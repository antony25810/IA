# backend/services/destinations/__init__.py
"""
Módulo de servicios para gestión de destinos turísticos
"""
from .service import DestinationService
from .router import router as destination_router

__all__ = ["DestinationService", "destination_router"]