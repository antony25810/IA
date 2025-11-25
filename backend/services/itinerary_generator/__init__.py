# backend/services/itinerary_generator/__init__.py
"""
Módulo Generador de Itinerarios (Orquestador)
Combina: Rules Engine + Search Service (BFS) + Route Optimizer (A*)
"""
from .service import ItineraryGeneratorService
from .router import router as itinerary_router
from .clustering import DayClustering

__all__ = [
    "ItineraryGeneratorService",
    "itinerary_router",
    "DayClustering"
]