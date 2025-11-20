# backend/services/search_service/bfs_algorithm.py
"""
Implementación del algoritmo BFS (Breadth-First Search)
Para exploración de atracciones turísticas
"""
from typing import List, Dict, Set, Optional, Tuple
from collections import deque
from dataclasses import dataclass
from sqlalchemy.orm import Session

from shared.database.models import Attraction, AttractionConnection
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class BFSNode:
    """Nodo en el grafo BFS"""
    attraction_id: int
    depth: int  # Nivel en el árbol BFS
    distance_from_start: float  # Distancia acumulada en metros
    time_from_start: int  # Tiempo acumulado en minutos
    parent_id: Optional[int] = None  # Atracción padre en el camino


@dataclass
class BFSResult:
    """Resultado de la exploración BFS"""
    candidates: List[Dict]  # Atracciones encontradas
    explored_count: int  # Total de nodos explorados
    levels_explored: int  # Niveles de profundidad explorados
    graph_structure: Dict[int, List[int]]  # Estructura del grafo explorado
    start_attraction_id: int


class BFSAlgorithm:
    """
    Implementación del algoritmo Breadth-First Search
    para exploración de atracciones turísticas
    """
    
    def __init__(self, db: Session):
        """
        Inicializar BFS
        
        Args:
            db: Sesión de base de datos
        """
        self.db = db
        self.visited: Set[int] = set()
        self.graph_structure: Dict[int, List[int]] = {}
    
    def explore(
        self,
        start_attraction_id: int,
        max_radius_meters: float = 10000,
        max_time_minutes: int = 480,
        max_candidates: int = 50,
        max_depth: int = 5,
        category_filter: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        price_range_filter: Optional[List[str]] = None,
        transport_mode: Optional[str] = None
    ) -> BFSResult:
        """
        Explorar atracciones usando BFS desde un punto inicial
        
        Args:
            start_attraction_id: ID de la atracción de inicio
            max_radius_meters: Radio máximo de búsqueda en metros
            max_time_minutes: Tiempo máximo de viaje acumulado
            max_candidates: Número máximo de candidatos a retornar
            max_depth: Profundidad máxima del árbol BFS
            category_filter: Filtrar por categorías específicas
            min_rating: Rating mínimo requerido
            price_range_filter: Filtrar por rangos de precio
            transport_mode: Modo de transporte preferido
            
        Returns:
            BFSResult: Resultado de la exploración
        """
        logger.info(
            f"Iniciando BFS desde atracción {start_attraction_id} "
            f"(radio: {max_radius_meters}m, tiempo: {max_time_minutes}min)"
        )
        
        # Verificar que la atracción de inicio existe
        start_attraction = self.db.query(Attraction).filter(
            Attraction.id == start_attraction_id
        ).first()
        
        if not start_attraction:
            raise ValueError(f"Atracción de inicio {start_attraction_id} no encontrada")
        
        # Inicializar estructuras
        self.visited = set()
        self.graph_structure = {}
        candidates = []
        
        # Cola BFS: (nodo, distancia_acumulada, tiempo_acumulado)
        queue = deque([
            BFSNode(
                attraction_id=start_attraction_id,
                depth=0,
                distance_from_start=0.0,
                time_from_start=0,
                parent_id=None
            )
        ])
        
        explored_count = 0
        max_level_reached = 0
        
        # ALGORITMO BFS
        while queue and len(candidates) < max_candidates:
            current_node = queue.popleft()
            
            # Verificar si ya visitamos este nodo
            if current_node.attraction_id in self.visited:
                continue
            
            # Verificar profundidad máxima
            if current_node.depth > max_depth:
                continue
            
            # Marcar como visitado
            self.visited.add(current_node.attraction_id)
            explored_count += 1
            max_level_reached = max(max_level_reached, current_node.depth)
            
            # Obtener información de la atracción actual
            current_attraction = self.db.query(Attraction).filter(
                Attraction.id == current_node.attraction_id
            ).first()
            
            if not current_attraction:
                continue
            
            # Verificar restricciones
            if not self._meets_criteria(
                current_attraction,
                category_filter,
                min_rating,
                price_range_filter
            ):
                logger.debug(f"Atracción {current_attraction.name} no cumple criterios")
                continue
            
            # Agregar a candidatos (excepto el punto de inicio)
            if current_node.depth > 0:
                candidates.append({
                    'attraction': current_attraction,
                    'depth': current_node.depth,
                    'distance_from_start': round(current_node.distance_from_start, 2),
                    'time_from_start': current_node.time_from_start,
                    'parent_id': current_node.parent_id
                })
                
                logger.debug(
                    f"Candidato agregado: {current_attraction.name} "
                    f"(depth={current_node.depth}, distance={current_node.distance_from_start:.0f}m)"
                )
            
            # Obtener vecinos (conexiones salientes)
            neighbors = self._get_neighbors(
                current_node.attraction_id,
                transport_mode
            )
            
            # Agregar vecinos a la estructura del grafo
            self.graph_structure[current_node.attraction_id] = [
                n['to_attraction_id'] for n in neighbors
            ]
            
            # Agregar vecinos no visitados a la cola
            for neighbor in neighbors:
                neighbor_id = neighbor['to_attraction_id']
                
                # Saltar si ya fue visitado
                if neighbor_id in self.visited:
                    continue
                
                # Calcular distancia y tiempo acumulados
                new_distance = current_node.distance_from_start + neighbor['distance_meters']
                new_time = current_node.time_from_start + neighbor['travel_time_minutes']
                
                # Verificar límites de radio y tiempo
                if new_distance > max_radius_meters:
                    logger.debug(
                        f"Vecino {neighbor_id} excede radio máximo "
                        f"({new_distance:.0f}m > {max_radius_meters}m)"
                    )
                    continue
                
                if new_time > max_time_minutes:
                    logger.debug(
                        f"Vecino {neighbor_id} excede tiempo máximo "
                        f"({new_time}min > {max_time_minutes}min)"
                    )
                    continue
                
                # Agregar a la cola
                queue.append(
                    BFSNode(
                        attraction_id=neighbor_id,
                        depth=current_node.depth + 1,
                        distance_from_start=new_distance,
                        time_from_start=new_time,
                        parent_id=current_node.attraction_id
                    )
                )
        
        logger.info(
            f"BFS completado: {len(candidates)} candidatos encontrados, "
            f"{explored_count} nodos explorados, {max_level_reached} niveles"
        )
        
        return BFSResult(
            candidates=candidates,
            explored_count=explored_count,
            levels_explored=max_level_reached,
            graph_structure=self.graph_structure,
            start_attraction_id=start_attraction_id
        )
    
    def _get_neighbors(
        self,
        attraction_id: int,
        transport_mode: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtener vecinos (conexiones) de una atracción
        
        Args:
            attraction_id: ID de la atracción
            transport_mode: Filtrar por modo de transporte
            
        Returns:
            List[Dict]: Lista de vecinos con información de conexión
        """
        query = self.db.query(AttractionConnection).filter(
            AttractionConnection.from_attraction_id == attraction_id
        )
        
        if transport_mode:
            query = query.filter(
                AttractionConnection.transport_mode == transport_mode.lower()
            )
        
        connections = query.all()
        
        neighbors = []
        for conn in connections:
            neighbors.append({
                'to_attraction_id': conn.to_attraction_id,
                'distance_meters': float(conn.distance_meters),
                'travel_time_minutes': conn.travel_time_minutes,
                'transport_mode': conn.transport_mode,
                'cost': float(conn.cost) if conn.cost else 0.0
            })
        
        return neighbors
    
    def _meets_criteria(
        self,
        attraction: Attraction,
        category_filter: Optional[List[str]],
        min_rating: Optional[float],
        price_range_filter: Optional[List[str]]
    ) -> bool:
        """
        Verificar si una atracción cumple con los criterios de filtrado
        
        Args:
            attraction: Atracción a verificar
            category_filter: Categorías permitidas
            min_rating: Rating mínimo
            price_range_filter: Rangos de precio permitidos
            
        Returns:
            bool: True si cumple todos los criterios
        """
        # Filtro por categoría
        if category_filter:
            if attraction.category not in [c.lower() for c in category_filter]:
                return False
        
        # Filtro por rating
        if min_rating is not None:
            if attraction.rating is None or attraction.rating < min_rating:
                return False
        
        # Filtro por rango de precio
        if price_range_filter:
            if attraction.price_range not in [p.lower() for p in price_range_filter]:
                return False
        
        return True
    
    def reconstruct_path(
        self,
        target_attraction_id: int,
        candidates: List[Dict]
    ) -> List[int]:
        """
        Reconstruir el camino desde el inicio hasta una atracción específica
        
        Args:
            target_attraction_id: ID de la atracción objetivo
            candidates: Lista de candidatos de BFS
            
        Returns:
            List[int]: Lista de IDs de atracciones en el camino
        """
        # Crear mapa de parent_id
        parent_map = {}
        for candidate in candidates:
            attraction_id = candidate['attraction'].id
            parent_id = candidate['parent_id']
            parent_map[attraction_id] = parent_id
        
        # Reconstruir camino hacia atrás
        path = []
        current = target_attraction_id
        
        while current is not None:
            path.append(current)
            current = parent_map.get(current)
        
        # Invertir para obtener camino desde inicio
        path.reverse()
        
        return path