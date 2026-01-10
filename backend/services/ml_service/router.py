"""
═══════════════════════════════════════════════════════════════════════════════
                        ML SERVICE ROUTER
═══════════════════════════════════════════════════════════════════════════════

Endpoints para el servicio de Machine Learning:
- Entrenamiento de la red neuronal
- Predicción de scores para atracciones
- Actualización masiva de scores en BD
- Métricas y estado del modelo

═══════════════════════════════════════════════════════════════════════════════
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from shared.database import get_db
from shared.database.models import Attraction, Destination
from shared.utils.logger import setup_logger
from services.auth.dependencies import get_current_user, get_admin_user

from .models.neural_network import AttractionScorerTrainer
from .models.inference import (
    AttractionScorer, 
    ScoringService, 
    ScoreCache,
    get_attraction_scores
)
from .data.dataset_loader import DatasetLoader, SyntheticDataGenerator

logger = setup_logger(__name__)

router = APIRouter(
    prefix="/ml",
    tags=["Machine Learning"],
    responses={404: {"description": "Not found"}}
)

# ═══════════════════════════════════════════════════════════════════════════════
#                              SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class TrainingConfig(BaseModel):
    """Configuración para entrenamiento"""
    epochs: int = Field(default=100, ge=1, le=1000, description="Número de épocas")
    batch_size: int = Field(default=32, ge=8, le=256, description="Tamaño del batch")
    learning_rate: float = Field(default=0.001, ge=0.0001, le=0.1, description="Learning rate")
    use_synthetic: bool = Field(default=True, description="Usar datos sintéticos si hay pocos datos reales")
    min_samples: int = Field(default=100, description="Mínimo de muestras para entrenar")
    validation_split: float = Field(default=0.2, ge=0.1, le=0.3, description="Proporción de validación")


class PredictionRequest(BaseModel):
    """Request para predicción de scores"""
    attraction_ids: List[int] = Field(..., min_items=1, max_items=500, description="IDs de atracciones")
    use_cache: bool = Field(default=True, description="Usar cache si está disponible")


class PredictionResponse(BaseModel):
    """Response con predicciones"""
    scores: Dict[int, float] = Field(..., description="Diccionario ID -> Score")
    cached_count: int = Field(default=0, description="Cantidad obtenida de cache")
    predicted_count: int = Field(default=0, description="Cantidad predicha por el modelo")
    model_loaded: bool = Field(default=False, description="Si el modelo está cargado")


class UpdateScoresRequest(BaseModel):
    """Request para actualizar scores"""
    destination_id: Optional[int] = Field(None, description="ID del destino (null = todos)")
    force_update: bool = Field(default=False, description="Forzar actualización de todos los scores")


class UpdateScoresResponse(BaseModel):
    """Response de actualización"""
    updated_count: int
    failed_count: int
    duration_seconds: float
    errors: List[str] = []


class ModelStatusResponse(BaseModel):
    """Estado del modelo"""
    model_loaded: bool
    model_path: str
    cache_size: int
    cache_ttl_minutes: int
    last_training: Optional[datetime]
    training_metrics: Optional[Dict[str, float]]


class TrainingStatusResponse(BaseModel):
    """Estado del entrenamiento"""
    status: str  # "idle", "training", "completed", "failed"
    current_epoch: int = 0
    total_epochs: int = 0
    current_loss: float = 0.0
    best_val_loss: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
#                         ESTADO GLOBAL DE ENTRENAMIENTO
# ═══════════════════════════════════════════════════════════════════════════════

class TrainingState:
    """Singleton para tracking del estado de entrenamiento"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_state()
        return cls._instance
    
    def _init_state(self):
        self.status = "idle"
        self.current_epoch = 0
        self.total_epochs = 0
        self.current_loss = 0.0
        self.best_val_loss = float('inf')
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.final_metrics = None
    
    def start_training(self, total_epochs: int):
        self.status = "training"
        self.total_epochs = total_epochs
        self.current_epoch = 0
        self.current_loss = 0.0
        self.best_val_loss = float('inf')
        self.started_at = datetime.utcnow()
        self.completed_at = None
        self.error_message = None
    
    def update_progress(self, epoch: int, loss: float, val_loss: float):
        self.current_epoch = epoch
        self.current_loss = loss
        if val_loss < self.best_val_loss:
            self.best_val_loss = val_loss
    
    def complete(self, metrics: Dict[str, float]):
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.final_metrics = metrics
    
    def fail(self, error: str):
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error
    
    def reset(self):
        self._init_state()


training_state = TrainingState()


# ═══════════════════════════════════════════════════════════════════════════════
#                              ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status():
    """
    Obtener estado actual del modelo de ML
    
    Retorna información sobre:
    - Si el modelo está cargado
    - Ruta del modelo
    - Estadísticas del cache
    - Métricas del último entrenamiento
    """
    scorer = AttractionScorer()
    cache = ScoreCache()
    
    return ModelStatusResponse(
        model_loaded=scorer.model is not None,
        model_path=scorer.model_path,
        cache_size=len(cache._cache),
        cache_ttl_minutes=int(cache.ttl / 60),
        last_training=training_state.completed_at,
        training_metrics=training_state.final_metrics
    )


@router.get("/training-status", response_model=TrainingStatusResponse)
async def get_training_status():
    """
    Obtener estado del entrenamiento en curso
    
    Útil para polling durante entrenamiento largo
    """
    return TrainingStatusResponse(
        status=training_state.status,
        current_epoch=training_state.current_epoch,
        total_epochs=training_state.total_epochs,
        current_loss=training_state.current_loss,
        best_val_loss=training_state.best_val_loss if training_state.best_val_loss != float('inf') else 0.0,
        started_at=training_state.started_at,
        completed_at=training_state.completed_at,
        error_message=training_state.error_message
    )


@router.post("/train", response_model=Dict[str, Any])
async def train_model(
    config: TrainingConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)  # Solo admins pueden entrenar
):
    """
    Iniciar entrenamiento de la red neuronal
    
    ⚠️ **Solo administradores**
    
    El entrenamiento se ejecuta en background. Usar `/ml/training-status`
    para monitorear el progreso.
    
    Si no hay suficientes datos reales y `use_synthetic=true`, se generarán
    datos sintéticos para el entrenamiento inicial.
    """
    # Verificar que no hay entrenamiento en curso
    if training_state.status == "training":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay un entrenamiento en curso"
        )
    
    # Contar datos disponibles
    total_attractions = db.query(Attraction).count()
    
    if total_attractions < config.min_samples and not config.use_synthetic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo hay {total_attractions} atracciones. Mínimo requerido: {config.min_samples}. "
                   f"Habilita use_synthetic=true para generar datos de entrenamiento."
        )
    
    # Iniciar entrenamiento en background
    background_tasks.add_task(
        _train_model_task,
        config=config,
        total_attractions=total_attractions
    )
    
    training_state.start_training(config.epochs)
    
    return {
        "message": "Entrenamiento iniciado",
        "total_attractions": total_attractions,
        "config": config.dict(),
        "monitor_url": "/ml/training-status"
    }


async def _train_model_task(config: TrainingConfig, total_attractions: int):
    """
    Tarea de entrenamiento en background
    """
    from shared.database import SessionLocal
    
    db = SessionLocal()
    try:
        logger.info("🚀 Iniciando entrenamiento de red neuronal...")
        
        # Cargar datos
        loader = DatasetLoader(db)
        train_loader, val_loader = loader.get_data_loaders(
            batch_size=config.batch_size,
            val_split=config.validation_split,
            augment=True
        )
        
        # Verificar si necesitamos datos sintéticos
        train_size = len(train_loader.dataset) if train_loader else 0
        
        if train_size < config.min_samples and config.use_synthetic:
            logger.info(f"📊 Generando datos sintéticos (solo {train_size} muestras reales)")
            
            generator = SyntheticDataGenerator()
            synthetic_samples = config.min_samples * 2  # Generar el doble
            
            train_loader, val_loader = generator.generate_dataloaders(
                num_samples=synthetic_samples,
                batch_size=config.batch_size,
                val_split=config.validation_split
            )
        
        if not train_loader or len(train_loader.dataset) == 0:
            training_state.fail("No hay datos suficientes para entrenar")
            return
        
        # Crear trainer
        trainer = AttractionScorerTrainer(
            learning_rate=config.learning_rate
        )
        
        # Callback para actualizar estado
        def progress_callback(epoch: int, train_loss: float, val_loss: float):
            training_state.update_progress(epoch, train_loss, val_loss)
        
        # Entrenar
        history = trainer.train(
            train_loader=train_loader,
            val_loader=val_loader,
            epochs=config.epochs,
            progress_callback=progress_callback
        )
        
        # Guardar modelo
        trainer.save_model()
        
        # Recargar modelo en el scorer singleton
        scorer = AttractionScorer()
        scorer._load_model()
        
        # Limpiar cache
        cache = ScoreCache()
        cache.clear()
        
        # Métricas finales
        metrics = {
            "final_train_loss": history["train_loss"][-1] if history["train_loss"] else 0,
            "final_val_loss": history["val_loss"][-1] if history["val_loss"] else 0,
            "best_val_loss": min(history["val_loss"]) if history["val_loss"] else 0,
            "total_epochs": len(history["train_loss"]),
            "samples_trained": len(train_loader.dataset)
        }
        
        training_state.complete(metrics)
        logger.info(f"✅ Entrenamiento completado: {metrics}")
        
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento: {e}")
        training_state.fail(str(e))
    finally:
        db.close()


@router.post("/predict", response_model=PredictionResponse)
async def predict_scores(
    request: PredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Predecir scores para una lista de atracciones
    
    Retorna un diccionario con los scores predichos por la red neuronal.
    Los scores están en rango [0, 1] donde 1 es mejor.
    
    Si `use_cache=true`, primero busca en cache antes de predecir.
    """
    try:
        # Verificar que las atracciones existen
        existing_ids = db.query(Attraction.id).filter(
            Attraction.id.in_(request.attraction_ids)
        ).all()
        existing_ids = {row[0] for row in existing_ids}
        
        # Filtrar IDs válidos
        valid_ids = [aid for aid in request.attraction_ids if aid in existing_ids]
        
        if not valid_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ninguna de las atracciones especificadas existe"
            )
        
        # Obtener scores
        cache = ScoreCache()
        cached_count = 0
        predicted_count = 0
        
        if request.use_cache:
            # Intentar obtener de cache primero
            scores = {}
            to_predict = []
            
            for aid in valid_ids:
                cached = cache.get(aid)
                if cached is not None:
                    scores[aid] = cached
                    cached_count += 1
                else:
                    to_predict.append(aid)
            
            # Predecir los que no están en cache
            if to_predict:
                predicted = get_attraction_scores(db, to_predict, use_cache=False)
                scores.update(predicted)
                predicted_count = len(predicted)
        else:
            scores = get_attraction_scores(db, valid_ids, use_cache=False)
            predicted_count = len(scores)
        
        scorer = AttractionScorer()
        
        return PredictionResponse(
            scores=scores,
            cached_count=cached_count,
            predicted_count=predicted_count,
            model_loaded=scorer.model is not None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en predicción: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al predecir scores: {str(e)}"
        )


@router.post("/update-scores", response_model=UpdateScoresResponse)
async def update_scores(
    request: UpdateScoresRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    """
    Actualizar scores en la base de datos
    
    ⚠️ **Solo administradores**
    
    Ejecuta el modelo sobre las atracciones y guarda los scores
    en el campo `nn_score` de cada atracción.
    
    - Si `destination_id` se especifica, solo actualiza ese destino
    - Si `force_update=true`, actualiza incluso si ya tienen score reciente
    """
    import time
    start_time = time.time()
    
    try:
        service = ScoringService(db)
        
        # Filtrar atracciones a actualizar
        query = db.query(Attraction)
        
        if request.destination_id:
            query = query.filter(Attraction.destination_id == request.destination_id)
        
        if not request.force_update:
            # Solo las que no tienen score o tienen score antiguo (>24h)
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(hours=24)
            query = query.filter(
                (Attraction.nn_score == None) | 
                (Attraction.nn_score_updated_at < cutoff)
            )
        
        attractions = query.all()
        
        if not attractions:
            return UpdateScoresResponse(
                updated_count=0,
                failed_count=0,
                duration_seconds=time.time() - start_time,
                errors=["No hay atracciones para actualizar"]
            )
        
        updated = 0
        failed = 0
        errors = []
        
        # Actualizar en batches
        batch_size = 100
        for i in range(0, len(attractions), batch_size):
            batch = attractions[i:i + batch_size]
            
            for attraction in batch:
                try:
                    score = service.update_attraction_score(attraction)
                    if score is not None:
                        updated += 1
                    else:
                        failed += 1
                        errors.append(f"Atracción {attraction.id}: modelo no disponible")
                except Exception as e:
                    failed += 1
                    errors.append(f"Atracción {attraction.id}: {str(e)}")
            
            # Commit cada batch
            db.commit()
        
        # Limpiar cache después de actualizar BD
        cache = ScoreCache()
        cache.clear()
        
        return UpdateScoresResponse(
            updated_count=updated,
            failed_count=failed,
            duration_seconds=time.time() - start_time,
            errors=errors[:20]  # Limitar errores retornados
        )
        
    except Exception as e:
        logger.error(f"Error actualizando scores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar scores: {str(e)}"
        )


@router.get("/top-attractions/{destination_id}", response_model=List[Dict[str, Any]])
async def get_top_attractions(
    destination_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    category: Optional[str] = Query(default=None, description="Filtrar por categoría"),
    db: Session = Depends(get_db)
):
    """
    Obtener las mejores atracciones de un destino según el score de la NN
    
    Útil para mostrar recomendaciones destacadas.
    """
    # Verificar destino
    destination = db.query(Destination).filter(
        Destination.id == destination_id
    ).first()
    
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destino {destination_id} no encontrado"
        )
    
    service = ScoringService(db)
    
    top_attractions = service.get_top_scored_attractions(
        destination_id=destination_id,
        limit=limit,
        category=category
    )
    
    return [
        {
            "id": attr.id,
            "name": attr.name,
            "category": attr.category,
            "rating": float(attr.rating) if attr.rating else None,
            "nn_score": float(attr.nn_score) if attr.nn_score else None,
            "google_rating": float(attr.google_rating) if attr.google_rating else None,
            "total_reviews": attr.total_reviews,
            "image_url": attr.image_url
        }
        for attr in top_attractions
    ]


@router.post("/clear-cache")
async def clear_cache(
    current_user = Depends(get_admin_user)
):
    """
    Limpiar cache de scores
    
    ⚠️ **Solo administradores**
    
    Útil después de reentrenar el modelo o actualizar datos.
    """
    cache = ScoreCache()
    size_before = len(cache._cache)
    cache.clear()
    
    return {
        "message": "Cache limpiado",
        "entries_removed": size_before
    }


@router.get("/statistics")
async def get_statistics(
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas del sistema de scoring
    
    Incluye distribución de scores, cobertura, etc.
    """
    from sqlalchemy import func
    
    # Total de atracciones
    total = db.query(func.count(Attraction.id)).scalar()
    
    # Con score
    with_score = db.query(func.count(Attraction.id)).filter(
        Attraction.nn_score != None
    ).scalar()
    
    # Estadísticas de scores
    score_stats = db.query(
        func.min(Attraction.nn_score).label('min'),
        func.max(Attraction.nn_score).label('max'),
        func.avg(Attraction.nn_score).label('avg'),
        func.stddev(Attraction.nn_score).label('stddev')
    ).filter(Attraction.nn_score != None).first()
    
    # Distribución por rangos
    distribution = {}
    for label, low, high in [
        ("bajo (0-0.3)", 0, 0.3),
        ("medio (0.3-0.6)", 0.3, 0.6),
        ("alto (0.6-0.8)", 0.6, 0.8),
        ("excelente (0.8-1.0)", 0.8, 1.0)
    ]:
        count = db.query(func.count(Attraction.id)).filter(
            Attraction.nn_score >= low,
            Attraction.nn_score < high if high < 1.0 else Attraction.nn_score <= high
        ).scalar()
        distribution[label] = count
    
    # Cache stats
    cache = ScoreCache()
    
    return {
        "total_attractions": total,
        "with_nn_score": with_score,
        "coverage_percent": round((with_score / total * 100) if total > 0 else 0, 2),
        "score_statistics": {
            "min": float(score_stats.min) if score_stats.min else None,
            "max": float(score_stats.max) if score_stats.max else None,
            "avg": float(score_stats.avg) if score_stats.avg else None,
            "stddev": float(score_stats.stddev) if score_stats.stddev else None
        },
        "score_distribution": distribution,
        "cache": {
            "entries": len(cache._cache),
            "ttl_minutes": int(cache.ttl / 60)
        },
        "model_loaded": AttractionScorer().model is not None
    }


@router.post("/reload-model")
async def reload_model(
    current_user = Depends(get_admin_user)
):
    """
    Recargar modelo desde disco
    
    ⚠️ **Solo administradores**
    
    Útil si se actualizó el archivo del modelo externamente.
    """
    scorer = AttractionScorer()
    
    old_state = scorer.model is not None
    scorer._load_model()
    new_state = scorer.model is not None
    
    # Limpiar cache al recargar
    cache = ScoreCache()
    cache.clear()
    
    return {
        "message": "Modelo recargado" if new_state else "No se pudo cargar el modelo",
        "was_loaded": old_state,
        "is_loaded": new_state,
        "model_path": scorer.model_path
    }


# ═══════════════════════════════════════════════════════════════════════════════
#                         ENDPOINT DE DIAGNÓSTICO
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/diagnose/{attraction_id}")
async def diagnose_attraction(
    attraction_id: int,
    db: Session = Depends(get_db)
):
    """
    Diagnóstico detallado del scoring de una atracción
    
    Muestra todas las features utilizadas por la red neuronal
    y cómo se calculó el score.
    """
    attraction = db.query(Attraction).filter(
        Attraction.id == attraction_id
    ).first()
    
    if not attraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Atracción {attraction_id} no encontrada"
        )
    
    # Obtener features
    features = attraction.get_features_for_nn()
    
    # Obtener score actual
    scorer = AttractionScorer()
    predicted_score = None
    
    if scorer.model is not None:
        predicted_score = scorer.predict_score(features)
    
    return {
        "attraction": {
            "id": attraction.id,
            "name": attraction.name,
            "category": attraction.category,
            "destination_id": attraction.destination_id
        },
        "stored_nn_score": float(attraction.nn_score) if attraction.nn_score else None,
        "stored_score_updated_at": attraction.nn_score_updated_at,
        "predicted_score": predicted_score,
        "features": features,
        "feature_descriptions": {
            "rating": "Rating promedio de la plataforma (0-5)",
            "total_reviews": "Número total de reviews (normalizado)",
            "google_rating": "Rating de Google Places (0-5)",
            "foursquare_rating": "Rating de Foursquare (0-10)",
            "foursquare_popularity": "Popularidad en Foursquare (0-1)",
            "sentiment_score": "Score de sentimiento de reviews (-1 a 1)",
            "price_level": "Nivel de precio (1-5)",
            "visit_duration": "Duración de visita en horas",
            "is_accessible": "Si es accesible (0/1)",
            "has_parking": "Si tiene estacionamiento (0/1)",
            "has_public_transport": "Si tiene transporte público (0/1)",
            "category_encoded": "Categoría codificada (0-9)",
            "location_quality": "Calidad de ubicación (latitud normalizada)"
        },
        "model_loaded": scorer.model is not None
    }
