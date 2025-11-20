# backend/services/router_optimizer/astar.py
"""
Implementación del algoritmo A* (A-Star) core
"""
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
from heapq import heappush, heappop
from sqlalchemy.orm import Session

from shared.database.models import Attraction, AttractionConnection
from shared.utils.logger import setup_logger
from .heuristics import Heuristics, CostCalculator, get_optimization_weights
from .path_generator import PathGenerator, OptimizedRoute

logger = setup_logger(__name__)


@dataclass
class AStarNode:
    """Nodo en el algoritmo A*"""
    attraction_id: int
    g_cost: float  # Costo real desde el inicio
    h_cost: float  # Heurística (estimación al objetivo)
    f_cost: float = field(init=False)  # Costo total f = g + h
    parent_id: Optional[int] = None
    
    def __post_init__(self):
        """Calcular f_cost al crear el nodo"""
        self.f_cost = self.g_cost + self.h_cost
    
    def __lt__(self, other):
        """Comparación para heapq (min-heap por f_cost)"""
        return self.f_cost < other.f_cost


class AStar:
    """
    Implementación del algoritmo A* para optimización de rutas
    """
    
    def __init__(
        self,
        db: Session,
        optimization_mode: str = "balanced",
        heuristic_type: str = "euclidean"
    ):
        """
        Inicializar A*
        
        Args:
            db: Sesión de base de datos
            optimization_mode: Modo de optimización (distance, time, cost, balanced, score)
            heuristic_type: Tipo de heurística (euclidean, manhattan, zero)
        """
        self.db = db
        self.optimization_mode = optimization_mode
        self.heuristic_type = heuristic_type
        self.nodes_explored = 0
        
        # Obtener pesos según modo
        self.weights = get_optimization_weights(optimization_mode)
        
        # Inicializar calculadores
        self.cost_calculator = CostCalculator(self.weights)
        self.path_generator = PathGenerator(db)
        
        # Seleccionar función heurística
        self.heuristic_func = self._get_heuristic_function()
        
        logger.info(
            f"A* inicializado: modo={optimization_mode}, "
            f"heurística={heuristic_type}"
        )
    
    def _get_heuristic_function(self):
        """Obtener función heurística según el tipo"""
        heuristic_map = {
            'euclidean': Heuristics.euclidean_distance,
            'manhattan': Heuristics.manhattan_distance,
            'zero': Heuristics.zero_heuristic
        }
        
        return heuristic_map.get(
            self.heuristic_type,
            Heuristics.euclidean_distance
        )
    
    def find_path(
        self,
        start_attraction_id: int,
        end_attraction_id: int,
        attraction_scores: Optional[Dict[int, float]] = None,
        max_iterations: int = 10000
    ) -> OptimizedRoute:
        """
        Encontrar ruta óptima usando A*
        
        Args:
            start_attraction_id: ID de atracción de inicio
            end_attraction_id: ID de atracción destino
            attraction_scores: Scores de idoneidad (opcional)
            max_iterations: Máximo de iteraciones
            
        Returns:
            OptimizedRoute: Ruta optimizada o ruta vacía si no se encuentra
        """
        logger.info(
            f"Buscando ruta A*: {start_attraction_id} → {end_attraction_id}"
        )
        
        # Verificar que las atracciones existen
        start_attr = self.db.query(Attraction).filter(
            Attraction.id == start_attraction_id
        ).first()
        
        end_attr = self.db.query(Attraction).filter(
            Attraction.id == end_attraction_id
        ).first()
        
        if not start_attr:
            raise ValueError(f"Atracción de inicio {start_attraction_id} no encontrada")
        
        if not end_attr:
            raise ValueError(f"Atracción destino {end_attraction_id} no encontrada")
        
        # Inicializar estructuras de datos
        self.nodes_explored = 0
        open_set = []  # Min-heap
        closed_set: Set[int] = set()
        came_from: Dict[int, int] = {}
        g_scores: Dict[int, float] = {start_attraction_id: 0.0}
        
        # Nodo inicial
        h_initial = self.heuristic_func(self.db, start_attr, end_attr)
        initial_node = AStarNode(
            attraction_id=start_attraction_id,
            g_cost=0.0,
            h_cost=h_initial,
            parent_id=None
        )
        heappush(open_set, initial_node)
        
        # ALGORITMO A*
        while open_set and self.nodes_explored < max_iterations:
            # Obtener nodo con menor f_cost
            current_node = heappop(open_set)
            current_id = current_node.attraction_id
            
            self.nodes_explored += 1
            
            # ¿Llegamos al destino?
            if current_id == end_attraction_id:
                logger.info(f"✅ Ruta encontrada ({self.nodes_explored} nodos)")
                
                # Reconstruir camino
                path = self.path_generator.reconstruct_path(
                    came_from,
                    start_attraction_id,
                    end_attraction_id
                )
                
                # Construir ruta completa
                return self.path_generator.build_route(
                    path,
                    g_scores,
                    self.nodes_explored,
                    self.optimization_mode,
                    attraction_scores
                )
            
            # Marcar como explorado
            if current_id in closed_set:
                continue
            
            closed_set.add(current_id)
            
            # Explorar vecinos
            neighbors = self._get_neighbors(current_id)
            
            for neighbor in neighbors:
                neighbor_id = neighbor['to_attraction_id']
                
                # Saltar si ya fue explorado
                if neighbor_id in closed_set:
                    continue
                
                # Calcular g_cost del vecino
                edge_cost = self._calculate_edge_cost(neighbor, attraction_scores)
                tentative_g = current_node.g_cost + edge_cost
                
                # Si encontramos un mejor camino
                if neighbor_id not in g_scores or tentative_g < g_scores[neighbor_id]:
                    # Actualizar
                    g_scores[neighbor_id] = tentative_g
                    came_from[neighbor_id] = current_id
                    
                    # Obtener atracción vecina para heurística
                    neighbor_attr = self.db.query(Attraction).filter(
                        Attraction.id == neighbor_id
                    ).first()
                    
                    if neighbor_attr:
                        h_cost = self.heuristic_func(self.db, neighbor_attr, end_attr)
                        
                        neighbor_node = AStarNode(
                            attraction_id=neighbor_id,
                            g_cost=tentative_g,
                            h_cost=h_cost,
                            parent_id=current_id
                        )
                        
                        heappush(open_set, neighbor_node)
        
        # No se encontró ruta
        logger.warning(f"❌ No se encontró ruta ({self.nodes_explored} nodos explorados)")
        
        return self.path_generator.create_empty_route(
            self.nodes_explored,
            self.optimization_mode
        )
    
    def _get_neighbors(self, attraction_id: int) -> List[Dict]:
        """Obtener vecinos (conexiones salientes)"""
        connections = self.db.query(AttractionConnection).filter(
            AttractionConnection.from_attraction_id == attraction_id
        ).all()
        
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
    
    def _calculate_edge_cost(
        self,
        connection: Dict,
        attraction_scores: Optional[Dict[int, float]]
    ) -> float:
        """Calcular costo de una arista"""
        # Score de idoneidad
        score = 0.0
        if attraction_scores and connection['to_attraction_id'] in attraction_scores:
            score = attraction_scores[connection['to_attraction_id']]
        
        return self.cost_calculator.calculate_edge_cost(
            distance_meters=connection['distance_meters'],
            travel_time_minutes=connection['travel_time_minutes'],
            cost=connection['cost'],
            suitability_score=score
        )