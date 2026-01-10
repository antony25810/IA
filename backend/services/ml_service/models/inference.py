# backend/services/ml_service/models/inference.py
"""
Módulo de inferencia para la red neuronal de scoring

Este módulo proporciona funciones de alto nivel para:
1. Cargar el modelo entrenado
2. Predecir scores para atracciones
3. Actualizar scores en la base de datos
4. Cache de predicciones para rendimiento
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import update

from shared.database.models import Attraction
from shared.utils.logger import setup_logger
from shared.config.settings import get_settings
from .neural_network import AttractionScorerNetwork, AttractionScorerTrainer

logger = setup_logger(__name__)
settings = get_settings()


class AttractionScorer:
    """
    Clase principal para inferencia de scores de atracciones
    
    Singleton para evitar múltiples cargas del modelo
    """
    
    _instance: Optional['AttractionScorer'] = None
    _model: Optional[AttractionScorerNetwork] = None
    _is_loaded: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Solo inicializar una vez
        if not self._is_loaded:
            self._load_or_create_model()
    
    def _load_or_create_model(self) -> None:
        """
        Cargar modelo existente o crear uno nuevo
        """
        model_path = Path(settings.NN_MODEL_SAVE_PATH)
        
        try:
            if model_path.exists():
                trainer = AttractionScorerTrainer()
                trainer.load_model(str(model_path))
                self._model = trainer.model
                self._is_loaded = True
                logger.info("Modelo de scoring cargado exitosamente")
            else:
                # Crear modelo nuevo (sin entrenar)
                self._model = AttractionScorerNetwork(
                    hidden_size=settings.NN_HIDDEN_SIZE
                )
                self._is_loaded = True
                logger.warning(
                    "No se encontró modelo entrenado. "
                    "Usando modelo sin entrenar (scores por defecto)"
                )
        except Exception as e:
            logger.error(f"Error cargando modelo: {str(e)}")
            # Fallback a modelo nuevo
            self._model = AttractionScorerNetwork()
            self._is_loaded = True
    
    @property
    def model(self) -> AttractionScorerNetwork:
        """Obtener el modelo cargado"""
        if not self._model:
            self._load_or_create_model()
        return self._model
    
    def predict_score(self, features: Dict[str, float]) -> float:
        """
        Predecir score para una atracción
        
        Args:
            features: Diccionario de características
        
        Returns:
            Score entre 0 y 1
        """
        try:
            return self.model.predict_single(features)
        except Exception as e:
            logger.error(f"Error en predicción: {str(e)}")
            return 0.5  # Score neutro por defecto
    
    def predict_scores_batch(
        self,
        features_list: List[Dict[str, float]]
    ) -> List[float]:
        """
        Predecir scores para múltiples atracciones
        
        Args:
            features_list: Lista de diccionarios de características
        
        Returns:
            Lista de scores
        """
        if not features_list:
            return []
        
        try:
            return self.model.predict_batch(features_list)
        except Exception as e:
            logger.error(f"Error en predicción batch: {str(e)}")
            return [0.5] * len(features_list)
    
    def reload_model(self) -> bool:
        """
        Recargar el modelo desde disco
        
        Returns:
            True si se cargó exitosamente
        """
        try:
            self._is_loaded = False
            self._model = None
            self._load_or_create_model()
            return self._is_loaded
        except Exception as e:
            logger.error(f"Error recargando modelo: {str(e)}")
            return False


class ScoringService:
    """
    Servicio para actualizar scores en la base de datos
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.scorer = AttractionScorer()
    
    def score_attraction(self, attraction: Attraction) -> float:
        """
        Calcular score para una atracción
        
        Args:
            attraction: Objeto Attraction de la BD
        
        Returns:
            Score calculado (0-1)
        """
        features = attraction.get_features_for_nn()
        return self.scorer.predict_score(features)
    
    def update_attraction_score(
        self,
        attraction_id: int,
        commit: bool = True
    ) -> Optional[float]:
        """
        Calcular y actualizar score de una atracción en BD
        
        Args:
            attraction_id: ID de la atracción
            commit: Si hacer commit inmediato
        
        Returns:
            Score actualizado o None si falla
        """
        attraction = self.db.query(Attraction).filter(
            Attraction.id == attraction_id
        ).first()
        
        if not attraction:
            logger.warning(f"Atracción {attraction_id} no encontrada")
            return None
        
        score = self.score_attraction(attraction)
        
        # Actualizar en BD
        attraction.nn_score = score
        attraction.nn_score_updated_at = datetime.now()
        
        if commit:
            self.db.commit()
            logger.debug(f"Score actualizado: Attraction {attraction_id} -> {score:.4f}")
        
        return score
    
    def update_destination_scores(
        self,
        destination_id: int,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Actualizar scores de todas las atracciones de un destino
        
        Args:
            destination_id: ID del destino
            batch_size: Tamaño del batch para updates
        
        Returns:
            Diccionario con estadísticas
        """
        # Obtener todas las atracciones del destino
        attractions = self.db.query(Attraction).filter(
            Attraction.destination_id == destination_id
        ).all()
        
        if not attractions:
            return {"total": 0, "updated": 0, "errors": 0}
        
        updated = 0
        errors = 0
        
        # Procesar en batches
        for i in range(0, len(attractions), batch_size):
            batch = attractions[i:i + batch_size]
            
            # Obtener features de todo el batch
            features_list = [a.get_features_for_nn() for a in batch]
            
            # Predecir scores en batch
            scores = self.scorer.predict_scores_batch(features_list)
            
            # Actualizar en BD
            for attraction, score in zip(batch, scores):
                try:
                    attraction.nn_score = score
                    attraction.nn_score_updated_at = datetime.now()
                    updated += 1
                except Exception as e:
                    logger.error(f"Error actualizando {attraction.id}: {str(e)}")
                    errors += 1
            
            # Commit por batch
            try:
                self.db.commit()
            except Exception as e:
                logger.error(f"Error en commit: {str(e)}")
                self.db.rollback()
                errors += batch_size
        
        logger.info(
            f"Scores actualizados para destino {destination_id}: "
            f"{updated}/{len(attractions)} éxitos, {errors} errores"
        )
        
        return {
            "total": len(attractions),
            "updated": updated,
            "errors": errors
        }
    
    def update_all_scores(
        self,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Actualizar scores de TODAS las atracciones
        
        Args:
            batch_size: Tamaño del batch
        
        Returns:
            Estadísticas globales
        """
        total_count = self.db.query(Attraction).count()
        updated = 0
        errors = 0
        
        # Procesar en batches para no cargar toda la BD en memoria
        offset = 0
        
        while offset < total_count:
            attractions = self.db.query(Attraction).offset(offset).limit(batch_size).all()
            
            if not attractions:
                break
            
            features_list = [a.get_features_for_nn() for a in attractions]
            scores = self.scorer.predict_scores_batch(features_list)
            
            for attraction, score in zip(attractions, scores):
                try:
                    attraction.nn_score = score
                    attraction.nn_score_updated_at = datetime.now()
                    updated += 1
                except Exception as e:
                    errors += 1
            
            try:
                self.db.commit()
            except Exception as e:
                logger.error(f"Error en commit batch {offset}: {str(e)}")
                self.db.rollback()
            
            offset += batch_size
            
            # Log progreso cada 500
            if updated % 500 == 0:
                logger.info(f"Progreso: {updated}/{total_count}")
        
        logger.info(
            f"Actualización global completada: "
            f"{updated}/{total_count} éxitos, {errors} errores"
        )
        
        return {
            "total": total_count,
            "updated": updated,
            "errors": errors
        }
    
    def get_top_scored_attractions(
        self,
        destination_id: int,
        limit: int = 50,
        category: Optional[str] = None
    ) -> List[Tuple[Attraction, float]]:
        """
        Obtener atracciones con mejores scores
        
        Args:
            destination_id: ID del destino
            limit: Máximo de resultados
            category: Filtrar por categoría
        
        Returns:
            Lista de tuplas (atracción, score)
        """
        query = self.db.query(Attraction).filter(
            Attraction.destination_id == destination_id
        )
        
        if category:
            query = query.filter(Attraction.category == category)
        
        # Ordenar por nn_score descendente
        attractions = query.order_by(
            Attraction.nn_score.desc()
        ).limit(limit).all()
        
        return [(a, float(a.nn_score) if a.nn_score else 0.5) for a in attractions]
    
    def get_scores_dict(
        self,
        attraction_ids: List[int]
    ) -> Dict[int, float]:
        """
        Obtener diccionario de scores para lista de IDs
        
        Útil para los algoritmos BFS y A*
        
        Args:
            attraction_ids: Lista de IDs
        
        Returns:
            Diccionario {id: score}
        """
        if not attraction_ids:
            return {}
        
        attractions = self.db.query(
            Attraction.id, Attraction.nn_score
        ).filter(
            Attraction.id.in_(attraction_ids)
        ).all()
        
        return {
            a.id: float(a.nn_score) if a.nn_score else 0.5
            for a in attractions
        }


class ScoreCache:
    """
    Cache en memoria para scores de atracciones
    
    Evita consultas repetidas a la BD durante la optimización
    """
    
    def __init__(self, max_size: int = 10000):
        self._cache: Dict[int, Tuple[float, datetime]] = {}
        self._max_size = max_size
        self._ttl_seconds = 3600  # 1 hora
    
    def get(self, attraction_id: int) -> Optional[float]:
        """Obtener score del cache"""
        if attraction_id in self._cache:
            score, timestamp = self._cache[attraction_id]
            # Verificar TTL
            if (datetime.now() - timestamp).seconds < self._ttl_seconds:
                return score
            else:
                del self._cache[attraction_id]
        return None
    
    def set(self, attraction_id: int, score: float) -> None:
        """Guardar score en cache"""
        # Limpiar si excede tamaño máximo
        if len(self._cache) >= self._max_size:
            # Eliminar entradas más antiguas
            oldest = sorted(
                self._cache.items(),
                key=lambda x: x[1][1]
            )[:self._max_size // 4]
            for k, _ in oldest:
                del self._cache[k]
        
        self._cache[attraction_id] = (score, datetime.now())
    
    def get_many(self, attraction_ids: List[int]) -> Dict[int, float]:
        """Obtener múltiples scores del cache"""
        result = {}
        for aid in attraction_ids:
            score = self.get(aid)
            if score is not None:
                result[aid] = score
        return result
    
    def set_many(self, scores: Dict[int, float]) -> None:
        """Guardar múltiples scores"""
        for aid, score in scores.items():
            self.set(aid, score)
    
    def clear(self) -> None:
        """Limpiar cache"""
        self._cache.clear()
    
    @property
    def size(self) -> int:
        return len(self._cache)


# Instancia global del cache
_score_cache = ScoreCache()


def get_attraction_scores(
    db: Session,
    attraction_ids: List[int],
    use_cache: bool = True
) -> Dict[int, float]:
    """
    Función helper para obtener scores de atracciones
    
    Usa cache para optimizar rendimiento
    
    Args:
        db: Sesión de BD
        attraction_ids: Lista de IDs
        use_cache: Si usar cache
    
    Returns:
        Diccionario {id: score}
    """
    if not attraction_ids:
        return {}
    
    result = {}
    missing_ids = []
    
    # Primero buscar en cache
    if use_cache:
        cached = _score_cache.get_many(attraction_ids)
        result.update(cached)
        missing_ids = [aid for aid in attraction_ids if aid not in cached]
    else:
        missing_ids = attraction_ids
    
    # Obtener los faltantes de BD
    if missing_ids:
        service = ScoringService(db)
        db_scores = service.get_scores_dict(missing_ids)
        result.update(db_scores)
        
        # Guardar en cache
        if use_cache:
            _score_cache.set_many(db_scores)
    
    return result


def clear_score_cache() -> None:
    """Limpiar cache de scores"""
    _score_cache.clear()
    logger.info("Cache de scores limpiado")
