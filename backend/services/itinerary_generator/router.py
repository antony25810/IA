# backend/services/itinerary_generator/router. py
"""
Endpoints REST para generación de itinerarios (VERSIÓN MEJORADA)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from shared.database.base import get_db
from shared. schemas.itinerary import (
    ItineraryGenerationRequest,
    ItineraryGenerationResponse,
    ItineraryRead,
    ItineraryWithDays,
    ItineraryUpdate
)
from shared.database.models import Itinerary
from shared.utils.logger import setup_logger
from .service import ItineraryGeneratorService

logger = setup_logger(__name__)

router = APIRouter(
    prefix="/itinerary",
    tags=["Itinerary Generator"]
)


@router.post(
    "/generate",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Generar itinerario completo",
    description="Genera un itinerario multi-día y lo guarda en BD"
)
async def generate_itinerary(
    request: ItineraryGenerationRequest,
    db: Session = Depends(get_db)
):
    """
    Genera un itinerario optimizado multi-día
    
    Flujo:
    1. Enriquecimiento de perfil (Rules Engine)
    2.  Exploración BFS
    3.  Scoring de candidatos
    4. Clustering geográfico
    5. Optimización A* por día
    6. Guardado en BD
    """
    try:
        service = ItineraryGeneratorService(db)
        
        # Extraer destination_id del city_center
        from shared.database.models import Attraction
        center_attr = db.query(Attraction). filter(Attraction.id == request.city_center_id).first()
        if not center_attr:
            raise HTTPException(status_code=404, detail="Atracción de inicio no encontrada")
        
        hotel_point = request.hotel_id if request.hotel_id else request.city_center_id
        
        result = await run_in_threadpool(
            service.generate_itinerary, 
            user_profile_id=request.user_profile_id,
            destination_id=center_attr.destination_id,
            city_center_attraction_id=request.city_center_id,
            num_days=request.num_days,
            start_date=request.start_date,
            hotel_attraction_id=hotel_point,
            optimization_mode=request.optimization_mode,
            max_radius_km=request.max_radius_km,
            max_candidates=request.max_candidates
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
            
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando itinerario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.get(
    "/{itinerary_id}",
    response_model=ItineraryWithDays,
    summary="Obtener itinerario con días"
)
def get_itinerary(
    itinerary_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Obtener un itinerario completo con sus días
    """
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerario no encontrado")
    
    return itinerary


@router.put(
    "/{itinerary_id}",
    response_model=ItineraryRead,
    summary="Actualizar itinerario"
)
def update_itinerary(
    itinerary_id: int = Path(..., gt=0),
    data: ItineraryUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    Actualizar metadatos del itinerario
    """
    itinerary = db.query(Itinerary). filter(Itinerary.id == itinerary_id).first()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerario no encontrado")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(itinerary, key, value)
    
    db.commit()
    db.refresh(itinerary)
    
    return itinerary


@router.delete(
    "/{itinerary_id}",
    status_code=status. HTTP_204_NO_CONTENT,
    summary="Eliminar itinerario"
)
def delete_itinerary(
    itinerary_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Eliminar un itinerario y todos sus días
    """
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerario no encontrado")
    
    db.delete(itinerary)
    db.commit()
    
    return None