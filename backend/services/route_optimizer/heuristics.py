# backend/services/router_optimizer/heuristics. py
"""
Funciones heurísticas para el algoritmo A*
"""
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, cast
from geoalchemy2 import Geography # type: ignore
from math import radians, cos, sin, asin, sqrt

from shared.database. models import Attraction
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class Heuristics:
    """Colección de funciones heurísticas para A*"""
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcula distancia en metros usando fórmula Haversine (Python puro). 
        Reemplaza a ST_Distance de PostGIS para velocidad en bucles.
        """
        if None in [lat1, lon1, lat2, lon2]:
            return 0.0

        # Radio de la tierra en metros
        R = 6371000 
        
        dLat = radians(lat2 - lat1)
        dLon = radians(lon2 - lon1)
        
        a = sin(dLat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon / 2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
    
    @staticmethod
    def manhattan_distance(
        db: Session,
        from_attraction: Attraction,
        to_attraction: Attraction
    ) -> float:
        """
        Distancia Manhattan (taxi) - suma de diferencias en lat/lon
        Útil para ciudades con calles en cuadrícula
        """
        try:
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
        self.is_cost_mode = weights.get('cost', 0) >= 2.0
    
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
        # ═══════════════════════════════════════════════════════════
        # NORMALIZACIÓN 
        # ═══════════════════════════════════════════════════════════
        
        # Distancia: escala logarítmica para no penalizar demasiado distancias largas
        distance_normalized = min(1.0, distance_meters / 5000)  # Max 5km para normalizar
        
        # Tiempo: escala lineal
        time_normalized = min(1.0, travel_time_minutes / 60)  # Max 1 hora
        
        # ═══════════════════════════════════════════════════════════
        # COSTO
        # ═══════════════════════════════════════════════════════════
        
        if self.is_cost_mode:
            # En modo costo, usar el valor REAL del costo, no normalizado
            # Esto hace que $50 sea 10x peor que $5
            if cost == 0:
                cost_factor = 0.0  # Gratis
            elif cost <= 5:
                cost_factor = 0.1  # Muy barato
            elif cost <= 15:
                cost_factor = 0.3  # Barato (metro, bus)
            elif cost <= 30:
                cost_factor = 0.6  # Medio
            else:
                cost_factor = 1.0 + (cost / 50)  # Caro (taxi) - penalización extra
        else:
            # Modo normal: normalización estándar
            cost_factor = min(1.0, cost / 100)
        
        # ═══════════════════════════════════════════════════════════
        
        # Score invertido (mayor score = menor costo)
        score_factor = 0.0
        if suitability_score > 0:
            score_factor = 1.0 - (suitability_score / 100)
        
        # Calcular costo ponderado
        edge_cost = (
            self.weights.get('distance', 0.0) * distance_normalized +
            self.weights.get('time', 0.0) * time_normalized +
            self.weights.get('cost', 0.0) * cost_factor +
            self.weights.get('score', 0.0) * score_factor
        )
        
        # Log para debug en modo cost
        if self.is_cost_mode and cost > 0:
            logger.debug(f"💰 Edge cost=${cost:.2f} → factor={cost_factor:.2f} → weighted={edge_cost:.3f}")
        
        return max(0.001, edge_cost)  # Mínimo para evitar ceros


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
            "distance": 3.0, 
            "time": 0.5,
            "cost": 0.3,
            "score": 0.2
        },
        "time": {
            "distance": 0.5,
            "time": 3.0,     
            "cost": 0.3,
            "score": 0.2
        },
        "cost": {
            "distance": 0.2,   # Casi ignorar distancia
            "time": 0.2,       # Casi ignorar tiempo
            "cost": 5.0,       # ← MUY ALTO - priorizar costo bajo
            "score": 0.1
        },
        "balanced": {
            "distance": 1.0,
            "time": 1.0,
            "cost": 1.0,
            "score": 1.0
        },
        "score": {
            "distance": 0.3,
            "time": 0.3,
            "cost": 0.2,
            "score": 3.0     
        }
    }
    
    selected = weights_map.get(mode, weights_map["balanced"])
    logger.info(f"🎯 Pesos para modo '{mode}': {selected}")
    
    return selected