# backend/services/attractions/router.py
"""
Endpoints REST para gestión de atracciones turísticas
Incluye búsquedas geoespaciales
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from shared.database.base import get_db
from shared.schemas.attraction import (
    AttractionCreate,
    AttractionUpdate,
    AttractionRead,
    AttractionSearchParams,
    AttractionWithDistance
)
from shared.schemas.base import MessageResponse
from .service import AttractionService

router = APIRouter(
    prefix="/attractions",
    tags=["Attractions"]
)


@router.post(
    "/",
    response_model=AttractionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva atracción",
    description="Crea una nueva atracción turística con su ubicación geográfica"
)
def create_attraction(
    data: AttractionCreate,
    db: Session = Depends(get_db)
):
    """
    Crear una nueva atracción turística.
    
    Campos requeridos:
    - destination_id: ID del destino al que pertenece
    - name: Nombre de la atracción
    - category: Categoría (cultural, aventura, gastronomia, naturaleza, entretenimiento, compras, religioso, historico, deportivo)
    - location: Coordenadas geográficas {lat, lon}
    
    Ejemplo:
    ```json
    {
        "destination_id": 1,
        "name": "Museo de Arte de Lima",
        "description": "Principal museo de arte del Perú",
        "category": "cultural",
        "subcategory": "museo",
        "location": {"lat": -12.0724, "lon": -77.0386},
        "address": "Paseo Colón 125, Lima",
        "average_visit_duration": 120,
        "price_range": "medio",
        "price_min": 30.0,
        "price_max": 30.0,
        "tags": ["arte", "museo", "cultura"]
    }
    ```
    """
    return AttractionService.create(db, data)


@router.get(
    "/",
    response_model=dict,
    summary="Listar atracciones",
    description="Obtiene una lista paginada de atracciones con filtros opcionales"
)
def list_attractions(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    destination_id: Optional[int] = Query(None, description="Filtrar por destino"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    search: Optional[str] = Query(None, description="Buscar por nombre"),
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0, description="Rating mínimo"),
    verified_only: bool = Query(False, description="Solo atracciones verificadas"),
    db: Session = Depends(get_db)
):
    """
    Listar atracciones con paginación y filtros.
    
    Parámetros de consulta:
    - skip: Paginación - registros a saltar
    - limit: Paginación - registros por página
    - destination_id: Filtrar por ID de destino
    - category: Filtrar por categoría
    - search: Buscar por nombre (búsqueda parcial)
    - min_rating: Rating mínimo (0-5)
    - verified_only: Solo mostrar atracciones verificadas
    """
    attractions, total = AttractionService.get_all(
        db=db,
        skip=skip,
        limit=limit,
        destination_id=destination_id,
        category=category,
        search=search,
        min_rating=min_rating,
        verified_only=verified_only
    )
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [AttractionRead.model_validate(a) for a in attractions]
    }


@router.get(
    "/search",
    response_model=dict,
    summary="Búsqueda avanzada de atracciones",
    description="Búsqueda con múltiples filtros incluyendo tags"
)
def search_attractions(
    category: Optional[str] = Query(None, description="Categoría"),
    subcategory: Optional[str] = Query(None, description="Subcategoría"),
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0),
    price_range: Optional[str] = Query(None, pattern="^(gratis|bajo|medio|alto)$"),
    verified_only: bool = Query(False),
    tags: Optional[List[str]] = Query(None, description="Tags a buscar"),
    db: Session = Depends(get_db)
):
    """
    Búsqueda avanzada con múltiples criterios.
    
    Ejemplo de uso:
    - `/attractions/search?category=cultural&min_rating=4.0&verified_only=true`
    - `/attractions/search?tags=museo&tags=arte`
    - `/attractions/search?price_range=gratis&category=historico`
    """
    params = AttractionSearchParams(
        category=category,
        subcategory=subcategory,
        min_rating=min_rating,
        price_range=price_range,
        verified_only=verified_only,
        tags=tags
    )
    
    attractions, total = AttractionService.search(db, params)
    
    return {
        "total": total,
        "items": [AttractionRead.model_validate(a) for a in attractions]
    }


@router.get(
    "/nearby",
    response_model=List[AttractionWithDistance],
    summary="Buscar atracciones cercanas",
    description="Búsqueda geoespacial de atracciones cercanas a un punto"
)
def search_nearby_attractions(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lon: float = Query(..., ge=-180, le=180, description="Longitud"),
    radius_km: float = Query(5.0, gt=0, le=50, description="Radio de búsqueda en km"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """
    Buscar atracciones cercanas a un punto geográfico.
    
    Usa PostGIS para calcular distancias reales en la superficie terrestre.
    
    **Parámetros:**
    - **lat**: Latitud del punto de referencia (-90 a 90)
    - **lon**: Longitud del punto de referencia (-180 a 180)
    - **radius_km**: Radio de búsqueda en kilómetros (máx: 50km)
    - **category**: Filtrar por categoría (opcional)
    - **limit**: Número máximo de resultados (máx: 100)
    
    **Ejemplo:**
    - Buscar museos a 3km del centro de Lima:
      `/attractions/nearby?lat=-12.0464&lon=-77.0428&radius_km=3&category=cultural`
    
    **Respuesta incluye:**
    - Distancia en metros desde el punto de referencia
    - Tiempo estimado de viaje caminando
    """
    attractions = AttractionService.search_nearby(
        db=db,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        category=category,
        limit=limit
    )
    
    return [AttractionWithDistance(**a) for a in attractions]


@router.get(
    "/category/{category}",
    response_model=List[AttractionRead],
    summary="Obtener atracciones por categoría",
    description="Lista atracciones de una categoría específica"
)
def get_attractions_by_category(
    category: str = Path(..., description="Categoría de atracciones"),
    destination_id: Optional[int] = Query(None, description="Filtrar por destino"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Obtener atracciones por categoría.
    
    **Categorías válidas:**
    - cultural
    - aventura
    - gastronomia
    - naturaleza
    - entretenimiento
    - compras
    - religioso
    - historico
    - deportivo
    """
    attractions = AttractionService.get_by_category(
        db=db,
        category=category,
        destination_id=destination_id,
        limit=limit
    )
    
    return [AttractionRead.model_validate(a) for a in attractions]


@router.get(
    "/{attraction_id}",
    response_model=AttractionRead,
    summary="Obtener una atracción",
    description="Obtiene la información detallada de una atracción"
)
def get_attraction(
    attraction_id: int = Path(..., gt=0, description="ID de la atracción"),
    db: Session = Depends(get_db)
):
    """
    Obtener una atracción por ID.
    """
    return AttractionService.get_or_404(db, attraction_id)


@router.get(
    "/{attraction_id}/statistics",
    response_model=dict,
    summary="Obtener estadísticas de una atracción",
    description="Estadísticas de reviews, ratings y popularidad"
)
def get_attraction_statistics(
    attraction_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas completas de una atracción.
    
    Incluye:
    - Total de reviews
    - Sentimiento promedio de reviews
    - Total de ratings de usuarios
    - Rating promedio
    - Score de popularidad
    """
    return AttractionService.get_statistics(db, attraction_id)


@router.put(
    "/{attraction_id}",
    response_model=AttractionRead,
    summary="Actualizar una atracción",
    description="Actualiza la información de una atracción existente"
)
def update_attraction(
    attraction_id: int = Path(..., gt=0),
    data: AttractionUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    Actualizar una atracción.
    
    Solo se actualizarán los campos proporcionados.
    """
    return AttractionService.update(db, attraction_id, data)


@router.delete(
    "/{attraction_id}",
    response_model=MessageResponse,
    summary="Eliminar una atracción",
    description="Elimina una atracción y sus relaciones"
)
def delete_attraction(
    attraction_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Eliminar una atracción.
    
    **⚠️ Advertencia:** Esta operación eliminará la atracción y todas sus
    relaciones (reviews, ratings, conexiones) debido a CASCADE.
    """
    return AttractionService.delete(db, attraction_id)