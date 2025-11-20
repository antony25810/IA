# backend/services/router_optimizer/__init__.py
"""
Módulo de optimización de rutas
Incluye algoritmos: A* (A-Star)
"""
from .service import RouterOptimizerService
from .router import router as router_optimizer_router
from .a_star import AStar
from .heuristics import Heuristics, CostCalculator, get_optimization_weights
from .path_generator import PathGenerator, OptimizedRoute, RouteSegment

__all__ = [
    "RouterOptimizerService",
    "router_optimizer_router",
    "AStar",
    "Heuristics",
    "CostCalculator",
    "get_optimization_weights",
    "PathGenerator",
    "OptimizedRoute",
    "RouteSegment"
]