# backend/services/search_service/service.py
"""
Servicio para búsqueda y exploración de atracciones usando BFS
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from .bfs_algorithm import BFSAlgorithm, BFSResult
from shared.database.models import Attraction, UserProfile
from shared.schemas.attraction import AttractionRead
from shared.utils.logger import setup_logger
from shared.config.constants import(
    get_categories_from_interests,
    get_budget_limits,
    MOBILITY_CONSTRAINTS
)

logger = setup_logger(__name__)


class SearchService:
    """Servicio de búsqueda con algoritmos de exploración"""
    
    @staticmethod
    def bfs_explore(
        db: Session,
        start_attraction_id: int,
        user_profile_id: Optional[int] = None,
        max_radius_km: float = 10.0,
        max_time_minutes: int = 480,
        max_candidates: int = 50,
        max_depth: int = 5,
        transport_mode: Optional[str] = None,
        optimization_mode: str = "balanced"
    ) -> Dict:
        """
        Explorar atracciones usando BFS
        
        Args:
            db: Sesión de base de datos
            start_attraction_id: ID de atracción de inicio
            user_profile_id: ID del perfil de usuario (opcional, para filtros)
            max_radius_km: Radio máximo en kilómetros
            max_time_minutes: Tiempo máximo de viaje
            max_candidates: Máximo número de candidatos
            max_depth: Profundidad máxima del BFS
            transport_mode: Modo de transporte preferido
            
        Returns:
            Dict: Resultado de la exploración con candidatos
        """
        try:
            # Verificar que la atracción de inicio existe
            start_attraction = db.query(Attraction).filter(
                Attraction.id == start_attraction_id
            ).first()
            
            if not start_attraction:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Atracción de inicio {start_attraction_id} no encontrada"
                )
            
            # Obtener filtros del perfil de usuario si está disponible
            category_filter = None
            min_rating = None
            price_range_filter = None
            
            if user_profile_id:
                user_profile = db.query(UserProfile).filter(
                    UserProfile.id == user_profile_id
                ).first()
                
                if user_profile:
                    preferences = user_profile.preferences or {}
                    
                    # Extraer intereses para filtro de categorías
                    interests = preferences.get('interests', [])
                    if interests:
                        # Mapear intereses a categorías
                        category_map = {
                            'cultural': 'cultural',
                            'historia': 'historico',
                            'arte': 'cultural',
                            'museos': 'cultural',
                            'gastronomia': 'gastronomia',
                            'naturaleza': 'naturaleza',
                            'aventura': 'aventura',
                            'entretenimiento': 'entretenimiento',
                            'compras': 'compras',
                            'deportes': 'deportivo'
                        }
                        
                        category_filter = []
                        for interest in interests:
                            category = category_map.get(interest.lower())
                            if category and category not in category_filter:
                                category_filter.append(category)
                    
                    # Filtro de presupuesto
                    budget_range = user_profile.budget_range
                    if budget_range:
                        price_map = {
                            'bajo': ['gratis', 'bajo'],
                            'medio': ['gratis', 'bajo', 'medio'],
                            'alto': ['gratis', 'bajo', 'medio', 'alto'],
                            'lujo': ['gratis', 'bajo', 'medio', 'alto']
                        }
                        price_range_filter = price_map.get(budget_range.lower(), None)
                    
                    # Rating mínimo (preferencia de calidad)
                    pace = preferences.get('pace', 'moderate')
                    if pace == 'relaxed':
                        min_rating = 4.0  # Más exigente si es relajado
                    elif pace == 'intense':
                        min_rating = 3.0  # Menos exigente si es intenso
            
            adjusted_params = SearchService._adjust_params_for_mode(
                optimization_mode=optimization_mode,
                max_radius_km=max_radius_km,
                max_candidates=max_candidates,
                min_rating=min_rating,
                price_range_filter=price_range_filter
            )
                    
            max_radius_km = adjusted_params['max_radius_km']
            max_candidates = adjusted_params['max_candidates']
            min_rating = adjusted_params['min_rating']
            price_range_filter = adjusted_params['price_range_filter']
            sort_priority = adjusted_params['sort_priority']
                    
            logger.info(f"🎯 Modo optimización: {optimization_mode} → Radio: {max_radius_km}km, Rating mín: {min_rating}")
                    

            # Ejecutar BFS
            bfs = BFSAlgorithm(db)
            result = bfs.explore(
                start_attraction_id=start_attraction_id,
                max_radius_meters=max_radius_km * 1000,
                max_time_minutes=max_time_minutes,
                max_candidates=max_candidates,
                max_depth=max_depth,
                category_filter=category_filter,
                min_rating=min_rating,
                price_range_filter=price_range_filter,
                transport_mode=transport_mode
            )
            
            # Formatear resultados
            candidates_formatted = []
            for candidate in result.candidates:
                attraction = candidate['attraction']
                
                candidates_formatted.append({
                    'attraction': AttractionRead.model_validate(attraction).model_dump(),
                    'depth': candidate['depth'],
                    'distance_from_start_meters': candidate['distance_from_start'],
                    'time_from_start_minutes': candidate['time_from_start'],
                    'parent_id': candidate['parent_id']
                })

            candidates_formatted = SearchService._sort_candidates_by_mode(
                candidates_formatted, 
                sort_priority
            )
            
            logger.info(
                f"BFS completado: {len(candidates_formatted)} candidatos, "
                f"{result.explored_count} explorados"
            )
            
            return {
                'start_attraction': {
                    'id': start_attraction.id,
                    'name': start_attraction.name,
                    'category': start_attraction.category
                },
                'candidates': candidates_formatted,
                'metadata': {
                    'total_candidates': len(candidates_formatted),
                    'nodes_explored': result.explored_count,
                    'levels_explored': result.levels_explored,
                    'max_radius_km': max_radius_km,
                    'max_time_minutes': max_time_minutes,
                    'optimization_mode': optimization_mode,
                    'filters_applied': {
                        'categories': category_filter,
                        'min_rating': min_rating,
                        'price_ranges': price_range_filter,
                        'transport_mode': transport_mode
                    }
                },
                'graph_structure': result.graph_structure
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en BFS explore: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error en exploración BFS: {str(e)}"
            )

    @staticmethod
    def find_path(
        db: Session,
        start_attraction_id: int,
        target_attraction_id: int,
        max_depth: int = 10
    ) -> Dict:
        """
        Encontrar un camino entre dos atracciones usando BFS
        
        Args:
            db: Sesión de base de datos
            start_attraction_id: Atracción de inicio
            target_attraction_id: Atracción objetivo
            max_depth: Profundidad máxima de búsqueda
            
        Returns:
            Dict: Camino encontrado o error
        """
        bfs = BFSAlgorithm(db)
        result = bfs.explore(
            start_attraction_id=start_attraction_id,
            max_radius_meters=100000,  # Radio grande
            max_candidates=1000,
            max_depth=max_depth
        )
        
        # Buscar el objetivo en los candidatos
        target_found = None
        for candidate in result.candidates:
            if candidate['attraction'].id == target_attraction_id:
                target_found = candidate
                break
        
        if not target_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró camino entre {start_attraction_id} y {target_attraction_id}"
            )
        
        # Reconstruir el camino
        path = bfs.reconstruct_path(target_attraction_id, result.candidates)
        
        # Obtener detalles de las atracciones en el camino
        path_details = []
        for attraction_id in path:
            attraction = db.query(Attraction).filter(
                Attraction.id == attraction_id
            ).first()
            
            if attraction:
                path_details.append({
                    'id': attraction.id,
                    'name': attraction.name,
                    'category': attraction.category
                })
        
        return {
            'path': path,
            'path_details': path_details,
            'distance_total': target_found['distance_from_start'],
            'time_total': target_found['time_from_start'],
            'hops': len(path) - 1
        }
    
    @staticmethod
    def _adjust_params_for_mode(
        optimization_mode: str,
        max_radius_km: float,
        max_candidates: int,
        min_rating: Optional[float],
        price_range_filter: Optional[List[str]]
    ) -> Dict:
        """
        Ajustar parámetros de búsqueda según el modo de optimización
        
        Returns:
            Dict con parámetros ajustados
        """
        
        # Valores por defecto
        adjusted = {
            'max_radius_km': max_radius_km,
            'max_candidates': max_candidates,
            'min_rating': min_rating,
            'price_range_filter': price_range_filter,
            'sort_priority': 'balanced'
        }
        
        if optimization_mode == "distance":
            # Priorizar cercanía: radio más pequeño
            adjusted['max_radius_km'] = min(max_radius_km, 5.0)
            adjusted['sort_priority'] = 'distance'
            logger.info("📍 Modo DISTANCE: Reduciendo radio a 5km, priorizando cercanía")
            
        elif optimization_mode == "score":
            # Priorizar calidad: rating mínimo más alto
            adjusted['min_rating'] = max(min_rating or 0, 4.0)
            adjusted['max_radius_km'] = max_radius_km * 1.5  
            adjusted['sort_priority'] = 'rating'
            logger. info("⭐ Modo SCORE: Rating mínimo 4.0, expandiendo radio")
            
        elif optimization_mode == "cost":
            # Priorizar económico: solo gratis y bajo
            adjusted['price_range_filter'] = ['gratis', 'bajo']
            adjusted['sort_priority'] = 'price'
            logger. info("💰 Modo COST: Solo atracciones gratis y bajo costo")
            
        elif optimization_mode == "time":
            # Priorizar tiempo: radio pequeño + menos candidatos
            adjusted['max_radius_km'] = min(max_radius_km, 3.0)
            adjusted['max_candidates'] = min(max_candidates, 30)
            adjusted['sort_priority'] = 'distance'
            logger. info("⏱️ Modo TIME: Radio reducido a 3km")
            
        else:  # balanced
            adjusted['sort_priority'] = 'balanced'
            logger.info("⚖️ Modo BALANCED: Parámetros estándar")
        
        return adjusted

    @staticmethod
    def _sort_candidates_by_mode(
        candidates: List[Dict], 
        sort_priority: str
    ) -> List[Dict]:
        """
        Ordenar candidatos según la prioridad del modo
        """
        
        if sort_priority == 'distance':
            # Ordenar por distancia (más cercano primero)
            return sorted(candidates, key=lambda x: x. get('distance_from_start_meters', 999999))
        
        elif sort_priority == 'rating':
            # Ordenar por rating (mejor primero)
            return sorted(
                candidates, 
                key=lambda x: x.get('attraction', {}).get('rating', 0) or 0, 
                reverse=True
            )
        
        elif sort_priority == 'price':
            # Ordenar por precio (gratis primero)
            price_order = {'gratis': 0, 'bajo': 1, 'medio': 2, 'alto': 3}
            return sorted(
                candidates,
                key=lambda x: price_order.get(
                    (x.get('attraction', {}).get('price_range', '') or '').lower(), 
                    99
                )
            )
        
        else:  # balanced
            # Ordenar por una combinación
            def balanced_score(c):
                rating = c.get('attraction', {}).get('rating', 0) or 0
                distance = c.get('distance_from_start_meters', 10000)
                # Score alto = bueno (rating alto, distancia baja)
                return (rating * 1000) - (distance / 100)
            
            return sorted(candidates, key=balanced_score, reverse=True)