# backend/services/attractions/__init__.py
"""
Módulo de servicios para gestión de atracciones turísticas
"""
from .service import AttractionService
from .router import router as attraction_router

__all__ = ["AttractionService", "attraction_router"]