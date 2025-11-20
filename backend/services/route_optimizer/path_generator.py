# backend/services/router_optimizer/path_generator.py
"""
Generación y reconstrucción de rutas optimizadas
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from shared.database.models import Attraction, AttractionConnection
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class RouteSegment:
    """Segmento de una ruta (conexión entre dos atracciones)"""
    from_attraction_id: int
    to_attraction_id: int
    distance_meters: float
    travel_time_minutes: int
    transport_mode: str
    cost: float


@dataclass
class OptimizedRoute:
    """Ruta optimizada completa"""
    attractions: List[Dict]           # Atracciones en orden de visita
    segments: List[RouteSegment]      # Conexiones entre atracciones
    total_distance: float             # Distancia total en metros
    total_time: int                   # Tiempo total en minutos
    total_cost: float                 # Costo total
    optimization_score: float         # Score de optimización (0-100)
    path_found: bool                  # Si se encontró una ruta
    nodes_explored: int               # Nodos explorados por A*
    optimization_mode: str            # Modo usado


class PathGenerator:
    """Generador y reconstructor de rutas"""
    
    def __init__(self, db: Session):
        """
        Inicializar generador
        
        Args:
            db: Sesión de base de datos
        """
        self.db = db
    
    def reconstruct_path(
        self,
        came_from: Dict[int, int],
        start_id: int,
        end_id: int
    ) -> List[int]:
        """
        Reconstruir camino desde el final hasta el inicio
        
        Args:
            came_from: Mapa de padres (nodo -> padre)
            start_id: ID de inicio
            end_id: ID de destino
            
        Returns:
            List[int]: Lista de IDs de atracciones en orden
        """
        path = []
        current = end_id
        
        # Reconstruir hacia atrás
        while current is not None:
            path.append(current)
            current = came_from.get(current)
        
        # Invertir para obtener orden correcto
        path.reverse()
        
        logger.debug(f"Camino reconstruido: {len(path)} atracciones")
        return path
    
    def build_route(
        self,
        path: List[int],
        g_scores: Dict[int, float],
        nodes_explored: int,
        optimization_mode: str,
        attraction_scores: Optional[Dict[int, float]] = None
    ) -> OptimizedRoute:
        """
        Construir objeto OptimizedRoute completo desde un camino
        
        Args:
            path: Lista de IDs de atracciones
            g_scores: Scores g finales
            nodes_explored: Cantidad de nodos explorados
            optimization_mode: Modo de optimización usado
            attraction_scores: Scores de idoneidad (opcional)
            
        Returns:
            OptimizedRoute: Ruta completa con todos los detalles
        """
        if not path:
            return OptimizedRoute(
                attractions=[],
                segments=[],
                total_distance=0.0,
                total_time=0,
                total_cost=0.0,
                optimization_score=0.0,
                path_found=False,
                nodes_explored=nodes_explored,
                optimization_mode=optimization_mode
            )
        
        # Obtener detalles de atracciones
        attractions = self._get_attraction_details(path, attraction_scores)
        
        # Obtener segmentos (conexiones)
        segments, total_distance, total_time, total_cost = self._get_segments(path)
        
        # Calcular score de optimización
        end_id = path[-1]
        final_g = g_scores.get(end_id, 0.0)
        optimization_score = max(0, min(100, 100 - (final_g * 100)))
        
        logger.info(
            f"Ruta construida: {len(attractions)} atracciones, "
            f"{total_distance:.0f}m, {total_time}min, ${total_cost:.2f}"
        )
        
        return OptimizedRoute(
            attractions=attractions,
            segments=segments,
            total_distance=round(total_distance, 2),
            total_time=total_time,
            total_cost=round(total_cost, 2),
            optimization_score=round(optimization_score, 2),
            path_found=True,
            nodes_explored=nodes_explored,
            optimization_mode=optimization_mode
        )
    
    def _get_attraction_details(
        self,
        path: List[int],
        attraction_scores: Optional[Dict[int, float]]
    ) -> List[Dict]:
        """
        Obtener detalles de las atracciones en el camino
        
        Args:
            path: Lista de IDs
            attraction_scores: Scores de idoneidad
            
        Returns:
            List[Dict]: Lista de atracciones con detalles
        """
        attractions = []
        
        for attraction_id in path:
            attr = self.db.query(Attraction).filter(
                Attraction.id == attraction_id
            ).first()
            
            if attr:
                attr_dict = {
                    'id': attr.id,
                    'name': attr.name,
                    'category': attr.category,
                    'rating': float(attr.rating) if attr.rating else None,
                    'price_range': attr.price_range,
                    'address': attr.address
                }
                
                # Agregar score si está disponible
                if attraction_scores and attr.id in attraction_scores:
                    attr_dict['suitability_score'] = attraction_scores[attr.id]
                
                attractions.append(attr_dict)
        
        return attractions
    
    def _get_segments(
        self,
        path: List[int]
    ) -> tuple[List[RouteSegment], float, int, float]:
        """
        Obtener segmentos (conexiones) entre atracciones
        
        Args:
            path: Lista de IDs de atracciones
            
        Returns:
            tuple: (segmentos, distancia_total, tiempo_total, costo_total)
        """
        segments = []
        total_distance = 0.0
        total_time = 0
        total_cost = 0.0
        
        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i + 1]
            
            # Buscar la conexión
            conn = self.db.query(AttractionConnection).filter(
                AttractionConnection.from_attraction_id == from_id,
                AttractionConnection.to_attraction_id == to_id
            ).first()
            
            if conn:
                segment = RouteSegment(
                    from_attraction_id=from_id,
                    to_attraction_id=to_id,
                    distance_meters=float(conn.distance_meters),
                    travel_time_minutes=conn.travel_time_minutes,
                    transport_mode=conn.transport_mode,
                    cost=float(conn.cost) if conn.cost else 0.0
                )
                
                segments.append(segment)
                total_distance += segment.distance_meters
                total_time += segment.travel_time_minutes
                total_cost += segment.cost
        
        return segments, total_distance, total_time, total_cost
    
    def create_empty_route(
        self,
        nodes_explored: int,
        optimization_mode: str
    ) -> OptimizedRoute:
        """
        Crear ruta vacía (cuando no se encuentra camino)
        
        Args:
            nodes_explored: Nodos explorados
            optimization_mode: Modo usado
            
        Returns:
            OptimizedRoute: Ruta vacía
        """
        return OptimizedRoute(
            attractions=[],
            segments=[],
            total_distance=0.0,
            total_time=0,
            total_cost=0.0,
            optimization_score=0.0,
            path_found=False,
            nodes_explored=nodes_explored,
            optimization_mode=optimization_mode
        )