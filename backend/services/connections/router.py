# backend/services/connections/router.py
"""
Endpoints REST para gestión de conexiones entre atracciones
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session

from shared.database.base import get_db
from shared.schemas.connection import (
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionRead,
    ConnectionWithAttractions
)
from shared.schemas.base import MessageResponse
from .service import ConnectionService

router = APIRouter(
    prefix="/connections",
    tags=["Connections"]
)


@router.post(
    "/",
    response_model=ConnectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una conexión entre atracciones",
    description="Crea una conexión unidireccional entre dos atracciones"
)
def create_connection(
    data: ConnectionCreate,
    db: Session = Depends(get_db)
):
    """
    Crear una conexión entre dos atracciones.
    
    Parámetros requeridos:
    - from_attraction_id: ID de la atracción origen
    - to_attraction_id: ID de la atracción destino
    - distance_meters: Distancia en metros
    - travel_time_minutes: Tiempo de viaje en minutos
    - transport_mode: Modo de transporte (caminando, carro, transporte_público, bici, taxi)
    
    Ejemplo:
    ```json
    {
        "from_attraction_id": 1,
        "to_attraction_id": 2,
        "distance_meters": 5200,
        "travel_time_minutes": 20,
        "transport_mode": "carro",
        "cost": 15.0,
        "traffic_factor": 1.2
    }
    ```
    """
    return ConnectionService.create(db, data)


@router.post(
    "/bidirectional",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Crear conexión bidireccional",
    description="Crea dos conexiones (A->B y B->A) simultáneamente"
)
def create_bidirectional_connection(
    from_id: int = Query(..., gt=0, description="ID atracción A"),
    to_id: int = Query(..., gt=0, description="ID atracción B"),
    distance_meters: float = Query(..., ge=0),
    travel_time_minutes: int = Query(..., gt=0),
    transport_mode: str = Query(...),
    cost: float = Query(0.0, ge=0),
    traffic_factor: float = Query(1.0, ge=0.5, le=3.0),
    db: Session = Depends(get_db)
):
    """
    Crear conexión bidireccional entre dos atracciones.
    
    Útil cuando el trayecto es simétrico (misma distancia y tiempo en ambas direcciones).
    
    """
    data = ConnectionCreate(
        from_attraction_id=from_id,
        to_attraction_id=to_id,
        distance_meters=distance_meters,
        travel_time_minutes=travel_time_minutes,
        transport_mode=transport_mode,
        cost=cost,
        traffic_factor=traffic_factor
    )
    
    conn_ab, conn_ba = ConnectionService.create_bidirectional(db, from_id, to_id, data)
    
    return {
        "message": "Conexión bidireccional creada exitosamente",
        "connection_ab": ConnectionRead.model_validate(conn_ab),
        "connection_ba": ConnectionRead.model_validate(conn_ba)
    }


@router.post(
    "/calculate",
    response_model=dict,
    summary="Calcular conexión automáticamente",
    description="Calcula distancia y tiempo usando PostGIS basándose en ubicaciones"
)
def calculate_connection(
    from_id: int = Query(..., gt=0),
    to_id: int = Query(..., gt=0),
    transport_mode: str = Query("walking", pattern="^(walking|car|public_transport|bicycle|taxi)$"),
    db: Session = Depends(get_db)
):
    """
    Calcular automáticamente los parámetros de una conexión.
    
    Usa PostGIS para calcular la distancia real y estima el tiempo y costo
    basándose en el modo de transporte.
    
    Modos de transporte:
    - caminando: 5 km/h, gratis
    - bici: 15 km/h, gratis
    - carro: 30 km/h, $2/km
    - transporte_público: 20 km/h, $2.50 fijo
    - taxi: 30 km/h, $5 mínimo o $3/km
    
    """
    return ConnectionService.calculate_connection_from_locations(
        db=db,
        from_id=from_id,
        to_id=to_id,
        transport_mode=transport_mode
    )


@router.get(
    "/",
    response_model=dict,
    summary="Listar conexiones",
    description="Obtiene una lista paginada de conexiones con filtros"
)
def list_connections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    from_attraction_id: Optional[int] = Query(None, description="Filtrar por atracción origen"),
    to_attraction_id: Optional[int] = Query(None, description="Filtrar por atracción destino"),
    transport_mode: Optional[str] = Query(None, description="Filtrar por modo de transporte"),
    db: Session = Depends(get_db)
):
    """
    Listar conexiones con paginación y filtros.
    """
    connections, total = ConnectionService.get_all(
        db=db,
        skip=skip,
        limit=limit,
        from_attraction_id=from_attraction_id,
        to_attraction_id=to_attraction_id,
        transport_mode=transport_mode
    )
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [ConnectionRead.model_validate(c) for c in connections]
    }


@router.get(
    "/from/{attraction_id}",
    response_model=List[ConnectionRead],
    summary="Obtener conexiones salientes",
    description="Obtiene todas las conexiones que salen de una atracción"
)
def get_connections_from(
    attraction_id: int = Path(..., gt=0),
    transport_mode: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Obtener conexiones salientes de una atracción.
    
    Útil para construir grafos y algoritmos de búsqueda (BFS, A*).
    """
    connections = ConnectionService.get_connections_from(
        db=db,
        attraction_id=attraction_id,
        transport_mode=transport_mode
    )
    return [ConnectionRead.model_validate(c) for c in connections]


@router.get(
    "/to/{attraction_id}",
    response_model=List[ConnectionRead],
    summary="Obtener conexiones entrantes",
    description="Obtiene todas las conexiones que llegan a una atracción"
)
def get_connections_to(
    attraction_id: int = Path(..., gt=0),
    transport_mode: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Obtener conexiones entrantes a una atracción.
    """
    connections = ConnectionService.get_connections_to(
        db=db,
        attraction_id=attraction_id,
        transport_mode=transport_mode
    )
    return [ConnectionRead.model_validate(c) for c in connections]


@router.get(
    "/between/{from_id}/{to_id}",
    response_model=ConnectionRead,
    summary="Obtener conexión específica",
    description="Obtiene la conexión entre dos atracciones específicas"
)
def get_connection_between(
    from_id: int = Path(..., gt=0),
    to_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Obtener conexión específica entre dos atracciones.
    
    Ejemplo:
    - `/connections/between/1/2` - Conexión de atracción 1 a atracción 2
    """
    connection = ConnectionService.get_connection_between(db, from_id, to_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe conexión entre {from_id} y {to_id}"
        )
    return connection


@router.get(
    "/graph",
    response_model=dict,
    summary="Construir grafo de conexiones",
    description="Construye el grafo completo para algoritmos de rutas"
)
def build_graph(
    destination_id: Optional[int] = Query(None, description="Filtrar por destino"),
    transport_mode: Optional[str] = Query(None, description="Filtrar por transporte"),
    db: Session = Depends(get_db)
):
    """
    Construir grafo de conexiones.
    
    Devuelve el grafo en formato:
    ```json
    {
        "1": [
            {"to": 2, "distance_meters": 500, "travel_time_minutes": 8, ...},
            {"to": 3, "distance_meters": 1200, "travel_time_minutes": 18, ...}
        ],
        "2": [...]
    }
    ```
    
    Este formato es ideal para algoritmos de búsqueda (BFS) y rutas (A*).
    """
    graph = ConnectionService.build_graph(
        db=db,
        destination_id=destination_id,
        transport_mode=transport_mode
    )
    return {"graph": graph, "nodes_count": len(graph)}


@router.get(
    "/{connection_id}",
    response_model=ConnectionRead,
    summary="Obtener una conexión",
    description="Obtiene los detalles de una conexión específica"
)
def get_connection(
    connection_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Obtener conexión por ID.
    """
    return ConnectionService.get_or_404(db, connection_id)


@router.get(
    "/{attraction_id}/statistics",
    response_model=dict,
    summary="Obtener estadísticas de conectividad",
    description="Estadísticas de conexiones de una atracción"
)
def get_connection_statistics(
    attraction_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas de conectividad.
    
    Incluye:
    - Conexiones salientes
    - Conexiones entrantes
    - Distancia promedio
    """
    return ConnectionService.get_statistics(db, attraction_id)


@router.put(
    "/{connection_id}",
    response_model=ConnectionRead,
    summary="Actualizar una conexión",
    description="Actualiza los parámetros de una conexión existente"
)
def update_connection(
    connection_id: int = Path(..., gt=0),
    data: ConnectionUpdate = ..., # type: ignore
    db: Session = Depends(get_db)
):
    """
    Actualizar una conexión.
    
    Solo se actualizarán los campos proporcionados.
    """
    return ConnectionService.update(db, connection_id, data)


@router.delete(
    "/{connection_id}",
    response_model=MessageResponse,
    summary="Eliminar una conexión",
    description="Elimina una conexión entre atracciones"
)
def delete_connection(
    connection_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Eliminar una conexión.
    """
    return ConnectionService.delete(db, connection_id)