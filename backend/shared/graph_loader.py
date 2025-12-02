# backend/services/shared/graph_loader.py
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape # type: ignore
from shared.database.models import Attraction, AttractionConnection

class GraphDataManager:
    def __init__(self, db: Session, destination_id: int):
        self.db = db
        self.destination_id = destination_id
        self.nodes: Dict[int, Dict] = {} 
        self.adjacency_list: Dict[int, List[Dict]] = {}
        
        # Debug
        print(f"🔧 GraphManager: Iniciando carga para Destination ID: {destination_id}")
        self._load_data()

    def _load_data(self):
        # 1. Cargar Nodos
        attractions = self.db.query(Attraction).filter(
            Attraction.destination_id == self.destination_id
        ).all()
        
        print(f"🔧 GraphManager: {len(attractions)} atracciones encontradas en DB.")

        for attr in attractions:
            lat, lon = None, None
            location_str = None
            if attr.location is not None:
                try:
                    point = to_shape(attr.location)
                    lat, lon = point.y, point.x
                    location_str = f"POINT({lon} {lat})"
                except Exception:
                    pass

            self.nodes[attr.id] = {
                'id': attr.id,
                'name': attr.name,
                'category': attr.category,
                'subcategory': attr.subcategory, # Útil para filtros
                'rating': attr.rating,
                'price_range': attr.price_range,
                'description': attr.description,
                'average_visit_duration': attr.average_visit_duration,
                'lat': lat,
                'lon': lon,
                'location': location_str,
                'destination_id': attr.destination_id,
                # --- CAMPOS OBLIGATORIOS PARA PYDANTIC (AttractionRead) ---
                'destination_id': attr.destination_id,
                'verified': attr.verified,
                'total_reviews': 0, # Valor por defecto si no lo cargas
                'created_at': attr.created_at,
                'updated_at': attr.updated_at,
                # Campos opcionales pero útiles para el frontend
                'opening_hours': attr.opening_hours,
                'images': attr.images,
                'address': attr.address
            }
            self.adjacency_list[attr.id] = []

        # 2. Cargar Conexiones
        attr_ids = list(self.nodes.keys())
        if not attr_ids:
            print("⚠️ GraphManager: No hay atracciones, saltando carga de conexiones.")
            return

        # Carga masiva de conexiones
        connections = self.db.query(AttractionConnection).filter(
            AttractionConnection.from_attraction_id.in_(attr_ids)
        ).all()

        print(f"🔧 GraphManager: {len(connections)} conexiones crudas encontradas en DB.")

        valid_connections = 0
        for conn in connections:
            # Verificar integridad: origen y destino deben estar en el mapa
            if conn.to_attraction_id in self.nodes:
                self.adjacency_list[conn.from_attraction_id].append({
                    'to_attraction_id': conn.to_attraction_id,
                    'distance_meters': float(conn.distance_meters),
                    'travel_time_minutes': conn.travel_time_minutes,
                    'transport_mode': conn.transport_mode,
                    'cost': float(conn.cost) if conn.cost else 0.0,
                    'traffic_factor': float(conn.traffic_factor) if conn.traffic_factor else 1.0
                })
                valid_connections += 1
        
        print(f"🔧 GraphManager: {valid_connections} conexiones válidas cargadas en RAM.")

    def get_neighbors(self, attraction_id: int) -> List[Dict]:
        neighbors = self.adjacency_list.get(attraction_id, [])
        # Debug extra si piden vecinos del nodo 1
        if attraction_id == 1:
            print(f"🔧 GraphManager: Solicitados vecinos para ID 1. Encontrados: {len(neighbors)}")
        return neighbors

    def get_node(self, attraction_id: int) -> Optional[Dict]:
        return self.nodes.get(attraction_id)