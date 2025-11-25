# backend/services/itinerary_generator/router.py
"""
Endpoints REST para la generación de itinerarios completos
"""
from typing import Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from shared.database.base import get_db
from shared.utils.logger import setup_logger
from .service import ItineraryGeneratorService

logger = setup_logger(__name__)

router = APIRouter(
    prefix="/itinerary",
    tags=["Itinerary Generator (Orchestrator)"]
)

# --- Esquemas de Solicitud (Request Models) ---

class ItineraryGenerationRequest(BaseModel):
    """Modelo de datos para solicitar un itinerario"""
    user_profile_id: int = Field(..., gt=0, description="ID del perfil del usuario")
    city_center_id: int = Field(..., gt=0, description="ID de una atracción céntrica o punto de partida general")
    hotel_id: Optional[int] = Field(None, gt=0, description="ID de la atracción/hotel donde se hospeda (inicio/fin de ruta)")
    num_days: int = Field(..., ge=1, le=14, description="Número de días del viaje")
    start_date: datetime = Field(..., description="Fecha y hora de inicio del viaje (ISO 8601)")

    class Config:
        json_schema_extra = {
            "example": {
                "user_profile_id": 1,
                "city_center_id": 10,     # Ej: Plaza Mayor
                "hotel_id": 55,           # Ej: Hotel XYZ
                "num_days": 3,
                "start_date": "2025-11-25T09:00:00"
            }
        }

# --- Endpoints ---

@router.post(
    "/generate",
    response_model=Dict,
    status_code=status.HTTP_201_CREATED,
    summary="Generar itinerario turístico completo",
    description="Orquesta todo el sistema IA (Reglas, BFS, Clustering, A*) para crear un plan de viaje personalizado."
)
def generate_itinerary(
    request: ItineraryGenerationRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Generar un itinerario multi-día optimizado.
    
    Flujo del proceso:
    1. **Enriquecimiento**: Usa el Motor de Reglas para determinar preferencias y restricciones (clima, presupuesto, gustos).
    2. **Exploración (BFS)**: Busca candidatos viables cerca del centro o hotel, filtrando por horario y reglas.
    3. **Puntuación**: Califica cada candidato (0-100) según qué tan bien encaja con el perfil enriquecido.
    4. **Selección**: Escoge los mejores candidatos (Top N).
    5. **Clustering**: Agrupa los candidatos geográficamente en 'N' días para minimizar traslados largos.
    6. **Ruteo (A*)**: Para cada día, calcula la ruta óptima paso a paso (hotel -> atracción A -> atracción B -> hotel).
    
    Retorna:
    - Objeto estructurado con el plan día por día, tiempos, costos y mapas.
    """
    try:
        service = ItineraryGeneratorService(db)
        
        # Si no se provee hotel, usamos el centro de la ciudad como punto de partida/retorno
        hotel_point = request.hotel_id if request.hotel_id else request.city_center_id
        
        result = service.generate_itinerary(
            user_profile_id=request.user_profile_id,
            city_center_attraction_id=request.city_center_id,
            num_days=request.num_days,
            start_date=request.start_date,
            hotel_attraction_id=hotel_point
        )
        
        # Manejo de errores lógicos del servicio
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=result["error"]
            )
            
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error crítico generando itinerario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno generando itinerario: {str(e)}"
        )