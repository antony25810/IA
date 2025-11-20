# backend/services/search_service/__init__.py
"""
Módulo de servicios de búsqueda y exploración
Incluye algoritmos: BFS
"""
from .service import SearchService
from .router import router as search_router
from .bfs_algorithm import BFSAlgorithm, BFSResult

__all__ = ["SearchService", "search_router", "BFSAlgorithm", "BFSResult"]