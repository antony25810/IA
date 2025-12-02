# backend/services/router_optimizer/astar.py
"""
Implementación del algoritmo A* (A-Star) core
"""
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
from heapq import heappush, heappop
from sqlalchemy.orm import Session

from shared.database.models import Attraction
from shared.utils.logger import setup_logger
from shared.graph_loader import GraphDataManager
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
        optimization_mode: str,
        heuristic_type: str = "euclidean"
    ):
        self.db = db
        self.optimization_mode = optimization_mode
        self.heuristic_type = heuristic_type
        self.nodes_explored = 0
        
        # Obtener pesos según modo
        self.weights = get_optimization_weights(optimization_mode)
        
        # Inicializar calculadores
        self.cost_calculator = CostCalculator(self.weights)
        self.path_generator = PathGenerator(db)
        
        logger.info(f"A* inicializado: modo={optimization_mode}, heurística={heuristic_type}")
    
    def find_path(
        self,
        start_attraction_id: int,
        end_attraction_id: int,
        attraction_scores: Optional[Dict[int, float]] = None,
        max_iterations: int = 10000
    ) -> OptimizedRoute:
        """
        Encontrar ruta óptima usando A* con carga en memoria (GraphLoader)
        """
        logger.info(f"Buscando ruta A*: {start_attraction_id} → {end_attraction_id}")
        
        # 1. Obtener la atracción de inicio de la DB SOLO para saber el destination_id
        # y cargar el grafo correcto.
        start_attr_db = self.db.query(Attraction).filter(Attraction.id == start_attraction_id).first()
        if not start_attr_db:
            raise ValueError(f"Atracción de inicio {start_attraction_id} no encontrada")
            
        # 2. CARGAR EL GRAFO EN MEMORIA (Optimización N+1)
        graph = GraphDataManager(self.db, start_attr_db.destination_id)

        # Obtener nodos de inicio y fin desde la memoria RAM
        start_node_data = graph.get_node(start_attraction_id)
        end_node_data = graph.get_node(end_attraction_id)
        
        if not start_node_data:
            raise ValueError(f"Atracción de inicio {start_attraction_id} no encontrada en el grafo")
        
        if not end_node_data:
            raise ValueError(f"Atracción destino {end_attraction_id} no encontrada en el grafo")
        
        # Inicializar estructuras de datos
        self.nodes_explored = 0
        open_set = []  # Min-heap
        closed_set: Set[int] = set()
        came_from: Dict[int, int] = {}
        g_scores: Dict[int, float] = {start_attraction_id: 0.0}
        
        # Calcular heurística inicial (usando coordenadas del diccionario)
        h_initial = 0.0
        if self.heuristic_type == 'euclidean':
            h_initial = Heuristics.haversine_distance(
                start_node_data['lat'], start_node_data['lon'],
                end_node_data['lat'], end_node_data['lon']
            )

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
                
                path = self.path_generator.reconstruct_path(
                    came_from,
                    start_attraction_id,
                    end_attraction_id
                )
                
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
            
            # 3. OBTENER VECINOS DE MEMORIA (No SQL)
            neighbors = graph.get_neighbors(current_id)
            
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
                    g_scores[neighbor_id] = tentative_g
                    came_from[neighbor_id] = current_id
                    
                    # 4. CALCULAR HEURÍSTICA (Usando datos en memoria)
                    h_cost = 0.0
                    neighbor_data = graph.get_node(neighbor_id)
                    
                    if neighbor_data and self.heuristic_type == 'euclidean':
                        # Llamada correcta a la estática con 4 argumentos
                        h_cost = Heuristics.haversine_distance(
                            neighbor_data['lat'], neighbor_data['lon'],
                            end_node_data['lat'], end_node_data['lon']
                        )
                        
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