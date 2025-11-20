# backend/services/destinations/router.py
"""
Endpoints REST para gestión de destinos turísticos
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from shared.database.base import get_db
from shared.schemas.destination import (
    DestinationCreate,
    DestinationUpdate,
    DestinationRead,
    DestinationWithStats
)
from shared.schemas.base import MessageResponse
from .service import DestinationService

router = APIRouter(
    prefix="/destinations",
    tags=["Destinations"]
)


@router.post(
    "/",
    response_model=DestinationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo destino",
    description="Crea un nuevo destino turístico con su ubicación geográfica"
)
def create_destination(
    data: DestinationCreate,
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo destino turístico.
    
    **Parámetros:**
    - **name**: Nombre del destino (requerido)
    - **country**: País (requerido)
    - **location**: Coordenadas geográficas (requerido)
        - **lat**: Latitud
        - **lon**: Longitud
    - **state**: Estado o región (opcional)
    - **timezone**: Zona horaria (opcional)
    - **description**: Descripción del destino (opcional)
    - **population**: Población aproximada (opcional)
    
    **Ejemplo:**
    ```json
    {
        "name": "Lima",
        "country": "Perú",
        "state": "Lima",
        "location": {"lat": -12.0464, "lon": -77.0428},
        "timezone": "America/Lima",
        "description": "Capital del Perú",
        "population": 10000000
    }
    ```
    """
    return DestinationService.create(db, data)


@router.get(
    "/",
    response_model=dict,
    summary="Listar destinos",
    description="Obtiene una lista paginada de destinos con filtros opcionales"
)
def list_destinations(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    country: Optional[str] = Query(None, description="Filtrar por país"),
    search: Optional[str] = Query(None, description="Buscar en nombre o descripción"),
    db: Session = Depends(get_db)
):
    """
    Listar destinos con paginación y filtros.
    
    **Parámetros de consulta:**
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros (default: 100, max: 1000)
    - **country**: Filtrar por país (opcional)
    - **search**: Buscar texto en nombre o descripción (opcional)
    
    **Respuesta:**
    ```json
    {
        "total": 2,
        "skip": 0,
        "limit": 100,
        "items": [...]
    }
    ```
    """
    destinations, total = DestinationService.get_all(
        db=db,
        skip=skip,
        limit=limit,
        country=country,
        search=search
    )
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [DestinationRead.model_validate(d) for d in destinations]
    }


@router.get(
    "/{destination_id}",
    response_model=DestinationRead,
    summary="Obtener un destino",
    description="Obtiene la información de un destino específico por su ID"
)
def get_destination(
    destination_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener un destino por ID.
    
    **Parámetros:**
    - **destination_id**: ID del destino
    
    **Respuestas:**
    - **200**: Destino encontrado
    - **404**: Destino no encontrado
    """
    return DestinationService.get_or_404(db, destination_id)


@router.get(
    "/{destination_id}/stats",
    response_model=DestinationWithStats,
    summary="Obtener destino con estadísticas",
    description="Obtiene un destino con estadísticas de atracciones"
)
def get_destination_with_stats(
    destination_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener destino con estadísticas de atracciones.
    
    Incluye:
    - Número total de atracciones
    - Rating promedio de atracciones
    """
    return DestinationService.get_with_stats(db, destination_id)


@router.put(
    "/{destination_id}",
    response_model=DestinationRead,
    summary="Actualizar un destino",
    description="Actualiza la información de un destino existente"
)
def update_destination(
    destination_id: int,
    data: DestinationUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar un destino existente.
    
    **Parámetros:**
    - **destination_id**: ID del destino a actualizar
    - Solo se actualizarán los campos proporcionados (PATCH semántico)
    
    **Ejemplo:**
    ```json
    {
        "description": "Nueva descripción actualizada",
        "population": 10500000
    }
    ```
    """
    return DestinationService.update(db, destination_id, data)


@router.delete(
    "/{destination_id}",
    response_model=MessageResponse,
    summary="Eliminar un destino",
    description="Elimina un destino y todas sus atracciones asociadas"
)
def delete_destination(
    destination_id: int,
    db: Session = Depends(get_db)
):
    """
    Eliminar un destino.
    
    **⚠️ Advertencia:** Esta operación eliminará el destino y todas sus atracciones
    asociadas debido a la restricción CASCADE en la base de datos.
    
    **Parámetros:**
    - **destination_id**: ID del destino a eliminar
    
    **Respuestas:**
    - **200**: Destino eliminado exitosamente
    - **404**: Destino no encontrado
    """
    return DestinationService.delete(db, destination_id)


@router.get(
    "/country/{country}",
    response_model=List[DestinationRead],
    summary="Obtener destinos por país",
    description="Obtiene todos los destinos de un país específico"
)
def get_destinations_by_country(
    country: str,
    db: Session = Depends(get_db)
):
    """
    Obtener todos los destinos de un país.
    
    **Parámetros:**
    - **country**: Nombre del país
    
    **Ejemplo:**
    - `/destinations/country/Perú`
    - `/destinations/country/Colombia`
    """
    destinations = DestinationService.get_by_country(db, country)
    return [DestinationRead.model_validate(d) for d in destinations]