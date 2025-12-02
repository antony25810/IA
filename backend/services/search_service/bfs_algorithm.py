# backend/services/search_service/bfs_algorithm.py
from typing import List, Dict, Set, Optional
from collections import deque
from dataclasses import dataclass
from sqlalchemy.orm import Session

from shared.database.models import Attraction
from shared.utils.logger import setup_logger
from shared.graph_loader import GraphDataManager 

logger = setup_logger(__name__)

@dataclass
class BFSNode:
    attraction_id: int
    depth: int
    distance_from_start: float
    time_from_start: int
    parent_id: Optional[int] = None

@dataclass
class BFSResult:
    candidates: List[Dict]
    explored_count: int
    levels_explored: int
    graph_structure: Dict[int, List[int]]
    start_attraction_id: int

class BFSAlgorithm:
    
    def __init__(self, db: Session):
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
        
        logger.info(f"🚀 BFS: Iniciando desde ID {start_attraction_id}")
        
        # 1. Obtener nodo de inicio para saber el destino y cargar el grafo
        start_node_db = self.db.query(Attraction).filter(Attraction.id == start_attraction_id).first()
        if not start_node_db:
            raise ValueError(f"Atracción de inicio {start_attraction_id} no encontrada")
        
        # 2. CARGAR EL GRAFO EN MEMORIA (Optimización N+1)
        graph = GraphDataManager(self.db, start_node_db.destination_id)
        
        # Inicializar estructuras
        self.visited = set()
        self.graph_structure = {}
        candidates = []
        
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
        
        # 3. BUCLE PRINCIPAL
        while queue and len(candidates) < max_candidates:
            current_node = queue.popleft()
            
            if current_node.attraction_id in self.visited:
                continue
            
            if current_node.depth > max_depth:
                continue
            
            self.visited.add(current_node.attraction_id)
            explored_count += 1
            max_level_reached = max(max_level_reached, current_node.depth)
            

            node_data = graph.get_node(current_node.attraction_id)
            
            if not node_data:
                logger.warning(f"⚠️ Nodo {current_node.attraction_id} no encontrado en RAM")
                continue
            
            # Validar filtros (usando la función adaptada a diccionarios)
            # El nodo inicial (depth 0) no se agrega a candidatos, solo sus vecinos
            if current_node.depth > 0:
                if self._meets_criteria_dict(node_data, category_filter, min_rating, price_range_filter):
                    candidates.append({
                        'attraction': node_data, # Pasamos el dict, el servicio luego lo maneja
                        'depth': current_node.depth,
                        'distance_from_start': round(current_node.distance_from_start, 2),
                        'time_from_start': current_node.time_from_start,
                        'parent_id': current_node.parent_id
                    })
                    # logger.info(f"✅ Candidato aceptado: {node_data['name']}")
                else:
                    # Debug para ver por qué rechaza
                    # logger.debug(f"❌ {node_data['name']} rechazado por filtros")
                    pass

            # 4. OBTENER VECINOS (Desde RAM)
            neighbors = graph.get_neighbors(current_node.attraction_id)
            
            # Guardar estructura para debug
            self.graph_structure[current_node.attraction_id] = [n['to_attraction_id'] for n in neighbors]
            
            for neighbor in neighbors:
                neighbor_id = neighbor['to_attraction_id']
                
                # Filtrar por modo de transporte si se pide
                if transport_mode and neighbor['transport_mode'] != transport_mode:
                    continue

                if neighbor_id in self.visited:
                    continue
                
                new_distance = current_node.distance_from_start + neighbor['distance_meters']
                new_time = current_node.time_from_start + neighbor['travel_time_minutes']
                
                if new_distance > max_radius_meters:
                    continue
                
                if new_time > max_time_minutes:
                    continue
                
                queue.append(BFSNode(
                    attraction_id=neighbor_id,
                    depth=current_node.depth + 1,
                    distance_from_start=new_distance,
                    time_from_start=new_time,
                    parent_id=current_node.attraction_id
                ))
                
        logger.info(f"🏁 BFS Fin: {len(candidates)} candidatos, {explored_count} explorados")
        
        return BFSResult(
            candidates=candidates,
            explored_count=explored_count,
            levels_explored=max_level_reached,
            graph_structure=self.graph_structure,
            start_attraction_id=start_attraction_id
        )

    def _meets_criteria_dict(
        self,
        attr_data: Dict,
        category_filter: Optional[List[str]],
        min_rating: Optional[float],
        price_range_filter: Optional[List[str]]
    ) -> bool:
        """
        Verifica criterios usando el DICCIONARIO de memoria (no objeto SQLAlchemy)
        """
        # 1. Filtro Categoría
        if category_filter:
            # Normalizar a minúsculas para comparar
            cat = (attr_data.get('category') or '').lower()
            if cat not in [c.lower() for c in category_filter]:
                return False
        
        # 2. Filtro Rating
        if min_rating is not None:
            rating = attr_data.get('rating')
            if rating is None or rating < min_rating:
                return False
        
        # 3. Filtro Precio
        if price_range_filter:
            price = (attr_data.get('price_range') or '').lower()
            if price not in [p.lower() for p in price_range_filter]:
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