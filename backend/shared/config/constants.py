"""
Constantes de la aplicación
Centraliza valores usados en múltiples servicios
"""
from typing import Dict, List

# ============================================================================
# MAPEO DE INTERESES A CATEGORÍAS DE ATRACCIONES
# ============================================================================

INTEREST_TO_CATEGORY_MAP: Dict[str, str] = {
    # Cultural
    'cultural': 'cultural',
    'cultura': 'cultural',
    'historia': 'historico',
    'historico': 'historico',
    'arte': 'cultural',
    'museos': 'cultural',
    'museo': 'cultural',
    'arqueologia': 'historico',
    'patrimonio': 'historico',
    
    # Gastronomía
    'gastronomia': 'gastronomia',
    'comida': 'gastronomia',
    'restaurantes': 'gastronomia',
    'cocina': 'gastronomia',
    'culinario': 'gastronomia',
    
    # Naturaleza
    'naturaleza': 'naturaleza',
    'natural': 'naturaleza',
    'paisajes': 'naturaleza',
    'ecologia': 'naturaleza',
    'parques': 'naturaleza',
    
    # Aventura
    'aventura': 'aventura',
    'deportes': 'deportivo',
    'deporte': 'deportivo',
    'extremo': 'aventura',
    'trekking': 'aventura',
    'hiking': 'aventura',
    
    # Entretenimiento
    'entretenimiento': 'entretenimiento',
    'diversion': 'entretenimiento',
    'nocturna': 'entretenimiento',
    'vida_nocturna': 'entretenimiento',
    
    # Compras
    'compras': 'compras',
    'shopping': 'compras',
    'mercados': 'compras',
    'artesania': 'compras',
    
    # Religioso
    'religioso': 'religioso',
    'espiritual': 'religioso',
    'iglesias': 'religioso',
    'templos': 'religioso',
    'santuarios': 'religioso'
}


# ============================================================================
# CATEGORÍAS VÁLIDAS DE ATRACCIONES
# ============================================================================

VALID_ATTRACTION_CATEGORIES: List[str] = [
    'cultural',
    'historico',
    'gastronomia',
    'naturaleza',
    'aventura',
    'deportivo',
    'entretenimiento',
    'compras',
    'religioso'
]


# ============================================================================
# NIVELES DE MOVILIDAD
# ============================================================================

MOBILITY_LEVELS: List[str] = ['low', 'medium', 'high']

MOBILITY_CONSTRAINTS: Dict[str, Dict[str, bool]] = {
    'low': {
        'requires_walking': False,
        'wheelchair_accessible': True,
        'elevator_available': True
    },
    'medium': {
        'requires_walking': True,
        'max_walking_distance_km': 2.0,
        'stairs_ok': False
    },
    'high': {
        'requires_walking': True,
        'stairs_ok': True,
        'no_constraints': True
    }
}


# ============================================================================
# RANGOS DE PRESUPUESTO
# ============================================================================

BUDGET_RANGES: Dict[str, Dict[str, float]] = {
    'low': {
        'min': 0.0,
        'max': 50.0,
        'daily_budget': 50.0
    },
    'medium': {
        'min': 50.0,
        'max': 150.0,
        'daily_budget': 150.0
    },
    'high': {
        'min': 150.0,
        'max': 500.0,
        'daily_budget': 500.0
    },
    'luxury': {
        'min': 500.0,
        'max': float('inf'),
        'daily_budget': 1000.0
    }
}


# ============================================================================
# COSTOS DE TRANSPORTE (por km)
# ============================================================================

TRANSPORT_COSTS_PER_KM: Dict[str, float] = {
    'walking': 0.0,
    'taxi': 1.5,
    'bus': 0.3,
    'private_car': 1.0,
    'uber': 1.2,
    'bike': 0.0,
    'metro': 0.5
}


# ============================================================================
# VELOCIDADES DE TRANSPORTE (km/h)
# ============================================================================

TRANSPORT_SPEEDS: Dict[str, float] = {
    'walking': 5.0,
    'taxi': 30.0,
    'bus': 20.0,
    'private_car': 40.0,
    'uber': 30.0,
    'bike': 15.0,
    'metro': 35.0
}


# ============================================================================
# TIEMPOS BASE DE TRANSPORTE (minutos)
# ============================================================================

TRANSPORT_BASE_TIMES: Dict[str, float] = {
    'walking': 0.0,
    'taxi': 5.0,      # Tiempo de espera promedio
    'bus': 10.0,      # Tiempo de espera + paradas
    'private_car': 2.0,
    'uber': 7.0,
    'bike': 0.0,
    'metro': 8.0
}

SCORING_WEIGHTS = {
    # Coincidencias de categoría
    'priority_category': 30.0,    # Categoría prioritaria (ej: Museo en perfil cultural)
    'recommended_category': 15.0, # Categoría recomendada
    'avoid_category': -50.0,      # Categoría a evitar
    
    # Restricciones
    'price_mismatch': -100.0,     # Precio fuera de rango
    'rating_below_min': -50.0,    # Rating muy bajo
    'missing_amenity': -40.0,     # Falta algo crítico (ej: rampa silla ruedas)
    
    # Base
    'rating_multiplier': 10.0,    # Rating 4.5 * 10 = 45 puntos
    
    # Penalización por distancia (BFS)
    'distance_penalty_per_km': 1.0 # -1 punto por cada km de distancia del centro
}

DEFAULT_VISIT_DURATION = 60


# ============================================================================
# CONFIGURACIÓN DE ALGORITMOS
# ============================================================================

# A* (route_optimizer)
ASTAR_CONFIG = {
    'max_iterations': 10000,
    'default_heuristic': 'euclidean',
    'cost_weights': {
        'distance': 0.4,
        'time': 0.3,
        'price': 0.3
    }
}

# BFS (search_service)
BFS_CONFIG = {
    'max_depth': 5,
    'max_results': 100,
    'distance_threshold_km': 50.0
}

# Forward Chaining (rules_engine)
FORWARD_CHAINING_CONFIG = {
    'max_iterations': 100,
    'conflict_resolution': 'priority',  # 'priority' | 'specificity' | 'recency'
    'enable_trace': False
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_category_from_interest(interest: str) -> str:
    """
    Mapea un interés del usuario a una categoría de atracción
    
    Args:
        interest: Interés del usuario (ej: 'historia', 'comida')
        
    Returns:
        str: Categoría de atracción (ej: 'historico', 'gastronomia')
        Si no hay mapeo, retorna el interés original en minúsculas
    """
    interest_lower = interest.lower(). strip()
    return INTEREST_TO_CATEGORY_MAP.get(interest_lower, interest_lower)


def get_categories_from_interests(interests: List[str]) -> List[str]:
    """
    Mapea múltiples intereses a categorías
    
    Args:
        interests: Lista de intereses del usuario
        
    Returns:
        List[str]: Lista de categorías únicas
    """
    categories = set()
    for interest in interests:
        category = get_category_from_interest(interest)
        categories.add(category)
    return list(categories)


def validate_budget_range(budget_range: str) -> bool:
    """
    Valida si un rango de presupuesto es válido
    
    Args:
        budget_range: Rango de presupuesto ('low', 'medium', 'high', 'luxury')
        
    Returns:
        bool: True si es válido
    """
    return budget_range. lower() in BUDGET_RANGES


def get_budget_limits(budget_range: str) -> Dict[str, float]:
    """
    Obtiene los límites de presupuesto para un rango
    
    Args:
        budget_range: Rango de presupuesto
        
    Returns:
        Dict con 'min', 'max', 'daily_budget'
    """
    return BUDGET_RANGES.get(budget_range.lower(), BUDGET_RANGES['medium'])


def validate_mobility_level(mobility_level: str) -> bool:
    """
    Valida si un nivel de movilidad es válido
    
    Args:
        mobility_level: Nivel de movilidad ('low', 'medium', 'high')
        
    Returns:
        bool: True si es válido
    """
    return mobility_level.lower() in MOBILITY_LEVELS