# backend/services/router_optimizer/router.py
"""
Endpoints REST para optimización de rutas con A*
"""
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, Query, Body, status
from sqlalchemy.orm import Session
from typing import Union

from shared.database.base import get_db
from .service import RouterOptimizerService

router = APIRouter(
    prefix="/router",
    tags=["Route Optimization (A*)"]
)


@router.post(
    "/optimize",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Optimizar ruta entre dos atracciones",
    description="Usa A* para encontrar la ruta óptima según el modo de optimización"
)
def optimize_route(
    start_attraction_id: int = Query(..., gt=0, description="ID de atracción de inicio"),
    end_attraction_id: int = Query(..., gt=0, description="ID de atracción destino"),
    optimization_mode: str = Query(
        "balanced",
        pattern="^(distance|time|cost|balanced|score)$",
        description="Modo de optimización"
    ),
    heuristic_type: str = Query(
        "euclidean",
        pattern="^(euclidean|manhattan|zero)$",
        description="Tipo de heurística"
    ),
    attraction_scores: Optional[Dict[Union[int, str], float]] = Body(
        None,
        description="Scores de idoneidad por atracción (opcional)"
    ),
    max_iterations: int = Query(10000, ge=100, le=100000),
    db: Session = Depends(get_db)
):
    """
    Optimizar ruta usando algoritmo A*.
    
    Modos de Optimización:
    - distance: Minimiza distancia en metros
    - time: Minimiza tiempo de viaje
    - cost: Minimiza costo monetario
    - balanced: Balance entre todos los factores (recomendado)
    - score: Maximiza scores de idoneidad (requiere scores)
    
    Tipos de Heurística:
    - euclidean: Distancia en línea recta (recomendado)
    - manhattan: Distancia Manhattan (ciudades en cuadrícula)
    - zero: Sin heurística (convierte A* en Dijkstra)
    
    Ejemplo de uso:
    ```
    POST /router/optimize?start_attraction_id=1&end_attraction_id=5&optimization_mode=balanced
    ```
    
    Con scores (opcional):
    ```json
    {
        "1": 95.5,
        "2": 87.3,
        "5": 92.0
    }
    ```
    
    Respuesta:
    - Lista ordenada de atracciones a visitar
    - Segmentos (conexiones) con distancia, tiempo y costo
    - Resumen de totales y score de optimización
    """
    return RouterOptimizerService.optimize_route(
        db=db,
        start_attraction_id=start_attraction_id,
        end_attraction_id=end_attraction_id,
        optimization_mode=optimization_mode,
        heuristic_type=heuristic_type,
        attraction_scores=attraction_scores,
        max_iterations=max_iterations
    )


@router.post(
    "/optimize-multi-stop",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Optimizar ruta con múltiples paradas",
    description="Encuentra la mejor ruta visitando múltiples atracciones"
)
def optimize_multi_stop_route(
    start_attraction_id: int = Query(..., gt=0),
    waypoints: List[int] = Body(..., min_length=1, description="IDs de atracciones a visitar"),
    end_attraction_id: Optional[int] = Query(None, description="ID destino final (opcional)"),
    optimization_mode: str = Query("balanced", pattern="^(distance|time|cost|balanced|score)$"),
    attraction_scores: Optional[Dict[int, float]] = Body(
        None,
        description="Scores de idoneidad por atracción",
        example={1: 95.5, 2: 87.3, 5: 92.0}
    ),
    db: Session = Depends(get_db)
):
    """
    Optimizar ruta con múltiples paradas.
    
    Algoritmo:
    - Usa estrategia greedy: visita la parada más óptima siguiente
    - Cada segmento se optimiza con A*
    - Si no se especifica destino final, vuelve al inicio
    
    Ejemplo:
    ```json
    {
        "waypoints": [2, 3, 5, 7],
        "attraction_scores": {
            "2": 90,
            "3": 85,
            "5": 95,
            "7": 88
        }
    }
    ```
    """
    return RouterOptimizerService.optimize_multi_stop(
        db=db,
        start_attraction_id=start_attraction_id,
        waypoints=waypoints,
        end_attraction_id=end_attraction_id,
        optimization_mode=optimization_mode,
        attraction_scores=attraction_scores
    )


@router.get(
    "/compare",
    response_model=dict,
    summary="Comparar diferentes modos de optimización",
    description="Compara rutas con todos los modos disponibles"
)
def compare_optimization_modes(
    start_attraction_id: int = Query(..., gt=0),
    end_attraction_id: int = Query(..., gt=0),
    attraction_scores: Optional[Dict[int, float]] = Body(
        None,
        description="Scores de idoneidad por atracción",
        example={1: 95.5, 2: 87.3, 5: 92.0}
    ),
    db: Session = Depends(get_db)
):
    """
    Comparar rutas con diferentes modos de optimización.
    
    Ejecuta A* con todos los modos disponibles:
    - distance
    - time
    - cost
    - balanced
    - score
    
    Respuesta:
    ```json
    {
        "comparisons": [
            {
                "mode": "distance",
                "total_distance_meters": 4200,
                "total_time_minutes": 50,
                "total_cost": 0,
                ...
            },
            {
                "mode": "time",
                "total_distance_meters": 6500,
                "total_time_minutes": 25,
                "total_cost": 15,
                ...
            },
            ...
        ]
    }
    ```
    """
    return RouterOptimizerService.compare_routes(
        db=db,
        start_attraction_id=start_attraction_id,
        end_attraction_id=end_attraction_id,
        attraction_scores=attraction_scores
    )