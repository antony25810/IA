# backend/services/search_service/router.py
"""
Endpoints REST para búsqueda y exploración con BFS
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from shared.database.base import get_db
from .service import SearchService

router = APIRouter(
    prefix="/search",
    tags=["Search & Exploration (BFS)"]
)


@router.post(
    "/bfs/explore",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Explorar atracciones con BFS",
    description="Usa Breadth-First Search para encontrar atracciones alcanzables desde un punto inicial"
)
def bfs_explore(
    start_attraction_id: int = Query(..., gt=0, description="ID de la atracción de inicio"),
    user_profile_id: Optional[int] = Query(None, description="ID del perfil de usuario para filtros personalizados"),
    max_radius_km: float = Query(10.0, gt=0, le=50, description="Radio máximo de búsqueda en km"),
    max_time_minutes: int = Query(480, gt=0, le=1440, description="Tiempo máximo de viaje en minutos"),
    max_candidates: int = Query(50, ge=1, le=200, description="Número máximo de candidatos"),
    max_depth: int = Query(5, ge=1, le=10, description="Profundidad máxima del árbol BFS"),
    transport_mode: Optional[str] = Query(None, pattern="^(walking|car|public_transport|bicycle|taxi)$"),
    db: Session = Depends(get_db)
):
    """
    Explorar atracciones usando algoritmo BFS (Breadth-First Search).
    
    Algoritmo:
    - Empieza en `start_attraction_id`
    - Explora nivel por nivel (amplitud primero)
    - Filtra por preferencias del usuario si se provee `user_profile_id`
    - Respeta límites de distancia, tiempo y profundidad
    
    Filtros Automáticos (con user_profile_id):
    - Categorías según intereses del usuario
    - Rango de precios según presupuesto
    - Rating mínimo según ritmo de viaje
    
    Ejemplo de uso:
    ```
    POST /search/bfs/explore?start_attraction_id=1&user_profile_id=1&max_radius_km=5
    ```
    
    Respuesta incluye:
    - Lista de candidatos con distancia y tiempo desde el inicio
    - Metadata de la exploración
    - Estructura del grafo explorado
    """
    return SearchService.bfs_explore(
        db=db,
        start_attraction_id=start_attraction_id,
        user_profile_id=user_profile_id,
        max_radius_km=max_radius_km,
        max_time_minutes=max_time_minutes,
        max_candidates=max_candidates,
        max_depth=max_depth,
        transport_mode=transport_mode
    )


@router.get(
    "/bfs/path",
    response_model=dict,
    summary="Encontrar camino entre dos atracciones",
    description="Usa BFS para encontrar un camino entre dos atracciones"
)
def find_path(
    start_attraction_id: int = Query(..., gt=0),
    target_attraction_id: int = Query(..., gt=0),
    max_depth: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Encontrar un camino entre dos atracciones usando BFS.
    
    Útil para:
    - Verificar si dos atracciones están conectadas
    - Encontrar la ruta más corta en número de saltos
    - Explorar conectividad del grafo
    
    Ejemplo:
    ```
    GET /search/bfs/path?start_attraction_id=1&target_attraction_id=5
    ```
    """
    return SearchService.find_path(
        db=db,
        start_attraction_id=start_attraction_id,
        target_attraction_id=target_attraction_id,
        max_depth=max_depth
    )