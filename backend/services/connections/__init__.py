# backend/services/connections/__init__.py
"""
Módulo de servicios para gestión de conexiones entre atracciones
"""
from .service import ConnectionService
from .router import router as connection_router

__all__ = ["ConnectionService", "connection_router"]