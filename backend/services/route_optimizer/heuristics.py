# backend/services/router_optimizer/heuristics.py
"""
Funciones heurísticas para el algoritmo A*
"""
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, cast
from geoalchemy2 import Geography # type: ignore

from shared.database.models import Attraction
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class Heuristics:
    """Colección de funciones heurísticas para A*"""
    
    @staticmethod
    def euclidean_distance(
        db: Session,
        from_attraction: Attraction,
        to_attraction: Attraction
    ) -> float:
        """
        Distancia euclidiana (línea recta) entre dos atracciones
        Usa PostGIS para cálculo geográfico real
        
        Args:
            db: Sesión de base de datos
            from_attraction: Atracción origen
            to_attraction: Atracción destino
            
        Returns:
            float: Distancia en metros
        """
        try:
            distance = db.query(
                func.ST_Distance(
                    cast(from_attraction.location, Geography),
                    cast(to_attraction.location, Geography)
                )
            ).scalar()
            
            return float(distance) if distance else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculando distancia euclidiana: {str(e)}")
            return 0.0
    
    @staticmethod
    def manhattan_distance(
        db: Session,
        from_attraction: Attraction,
        to_attraction: Attraction
    ) -> float:
        """
        Distancia Manhattan (taxi) - suma de diferencias en lat/lon
        Útil para ciudades con calles en cuadrícula
        
        Args:
            db: Sesión de base de datos
            from_attraction: Atracción origen
            to_attraction: Atracción destino
            
        Returns:
            float: Distancia estimada en metros
        """
        try:
            # Extraer coordenadas
            from_coords = db.query(
                func.ST_Y(cast(from_attraction.location, Geography)),
                func.ST_X(cast(from_attraction.location, Geography))
            ).first()
            
            to_coords = db.query(
                func.ST_Y(cast(to_attraction.location, Geography)),
                func.ST_X(cast(to_attraction.location, Geography))
            ).first()
            
            if from_coords and to_coords:
                lat_diff = abs(from_coords[0] - to_coords[0])
                lon_diff = abs(from_coords[1] - to_coords[1])
                
                # Aproximación: 1 grado ≈ 111km
                distance = (lat_diff + lon_diff) * 111000
                
                return float(distance)
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Error calculando distancia Manhattan: {str(e)}")
            return 0.0
    
    @staticmethod
    def zero_heuristic(
        db: Session,
        from_attraction: Attraction,
        to_attraction: Attraction
    ) -> float:
        """
        Heurística nula (siempre 0)
        Convierte A* en Dijkstra
        
        Returns:
            float: 0.0
        """
        return 0.0


class CostCalculator:
    """Calculador de costos de aristas (edges)"""
    
    def __init__(self, weights: Dict[str, float]):
        """
        Inicializar calculador
        
        Args:
            weights: Pesos para distance, time, cost, score
        """
        self.weights = weights
    
    def calculate_edge_cost(
        self,
        distance_meters: float,
        travel_time_minutes: int,
        cost: float,
        suitability_score: float = 0.0
    ) -> float:
        """
        Calcular costo de una arista (conexión)
        
        Args:
            distance_meters: Distancia en metros
            travel_time_minutes: Tiempo de viaje en minutos
            cost: Costo monetario
            suitability_score: Score de idoneidad (0-100)
            
        Returns:
            float: Costo calculado
        """
        # Normalizar valores a escala 0-1
        distance_normalized = min(1.0, distance_meters / 10000)  # Max 10km
        time_normalized = min(1.0, travel_time_minutes / 120)    # Max 2 horas
        cost_normalized = min(1.0, cost / 100)                   # Max $100
        
        # Score invertido (mayor score = menor costo)
        score_normalized = 1.0 - (suitability_score / 100) if suitability_score > 0 else 0.0
        
        # Calcular costo ponderado
        edge_cost = (
            self.weights.get('distance', 0.0) * distance_normalized +
            self.weights.get('time', 0.0) * time_normalized +
            self.weights.get('cost', 0.0) * cost_normalized +
            self.weights.get('score', 0.0) * score_normalized
        )
        
        return edge_cost


def get_optimization_weights(mode: str) -> Dict[str, float]:
    """
    Obtener pesos para diferentes modos de optimización
    
    Args:
        mode: Modo de optimización
            - "distance": Minimizar distancia
            - "time": Minimizar tiempo
            - "cost": Minimizar costo monetario
            - "balanced": Balance entre todos
            - "score": Maximizar score de idoneidad
    
    Returns:
        Dict: Pesos para cada factor
    """
    weights_map = {
        "distance": {
            "distance": 0.7,
            "time": 0.2,
            "cost": 0.1,
            "score": 0.0
        },
        "time": {
            "distance": 0.1,
            "time": 0.7,
            "cost": 0.1,
            "score": 0.1
        },
        "cost": {
            "distance": 0.2,
            "time": 0.2,
            "cost": 0.6,
            "score": 0.0
        },
        "balanced": {
            "distance": 0.3,
            "time": 0.3,
            "cost": 0.2,
            "score": 0.2
        },
        "score": {
            "distance": 0.1,
            "time": 0.2,
            "cost": 0.1,
            "score": 0.6
        }
    }
    
    return weights_map.get(mode, weights_map["balanced"])