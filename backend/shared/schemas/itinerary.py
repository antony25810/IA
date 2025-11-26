# shared/schemas/itinerary. py
"""
Schemas Pydantic para itinerarios (VERSIÓN MEJORADA)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal


# ============================================================
# SCHEMAS AUXILIARES
# ============================================================

class AttractionInDay(BaseModel):
    """Atracción dentro de un día del itinerario"""
    attraction_id: int
    order: int
    arrival_time: Optional[str] = None  # "09:00"
    departure_time: Optional[str] = None  # "10:30"
    visit_duration_minutes: int
    score: Optional[float] = None


class RouteSegment(BaseModel):
    """Segmento de ruta entre dos atracciones"""
    from_attraction_id: int
    to_attraction_id: int
    distance_meters: float
    travel_time_minutes: int
    transport_mode: str
    cost: float


class DaySummary(BaseModel):
    """Resumen de métricas de un día"""
    total_distance_meters: float
    total_time_minutes: int
    total_cost: float
    attractions_count: int
    optimization_score: Optional[float] = None


class DayData(BaseModel):
    """Estructura completa de datos de un día"""
    attractions: List[AttractionInDay]
    segments: List[RouteSegment]


# ============================================================
# ITINERARY DAY SCHEMAS
# ============================================================

class ItineraryDayBase(BaseModel):
    """Schema base para días de itinerario"""
    day_number: int = Field(... , ge=1, description="Número del día (1, 2, 3...)")
    date: date
    cluster_id: Optional[int] = None


class ItineraryDayCreate(ItineraryDayBase):
    """Schema para crear un día de itinerario"""
    itinerary_id: int
    day_data: DayData
    cluster_centroid_lat: Optional[float] = None
    cluster_centroid_lon: Optional[float] = None
    total_distance_meters: Optional[float] = None
    total_time_minutes: Optional[int] = None
    total_cost: Optional[float] = None
    attractions_count: Optional[int] = None
    optimization_score: Optional[float] = None


class ItineraryDayRead(ItineraryDayBase):
    """Schema para leer un día de itinerario"""
    id: int
    itinerary_id: int
    day_data: Dict[str, Any]
    cluster_centroid_lat: Optional[float] = None
    cluster_centroid_lon: Optional[float] = None
    total_distance_meters: Optional[float] = None
    total_time_minutes: Optional[int] = None
    total_cost: Optional[float] = None
    attractions_count: Optional[int] = None
    optimization_score: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ItineraryDayUpdate(BaseModel):
    """Schema para actualizar un día"""
    day_data: Optional[DayData] = None
    date: Optional[date] = None


# ============================================================
# ITINERARY SCHEMAS
# ============================================================

class ItineraryBase(BaseModel):
    """Schema base de itinerario"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    start_date: date


class ItineraryCreate(ItineraryBase):
    """Schema para crear un itinerario"""
    user_profile_id: int = Field(..., gt=0)
    destination_id: int = Field(..., gt=0)
    start_point_id: Optional[int] = None
    num_days: int = Field(..., ge=1, le=14)
    generation_params: Optional[Dict[str, Any]] = None
    algorithms_used: Optional[Dict[str, str]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_profile_id": 1,
                "destination_id": 1,
                "start_point_id": 55,
                "name": "Tour Lima 3 Días",
                "description": "Recorrido cultural por Lima",
                "num_days": 3,
                "start_date": "2025-11-25",
                "generation_params": {
                    "optimization_mode": "balanced",
                    "max_radius_km": 10.0,
                    "max_candidates": 50
                },
                "algorithms_used": {
                    "search": "BFS",
                    "routing": "A*",
                    "clustering": "KMeans"
                }
            }
        }
    )


class ItineraryUpdate(BaseModel):
    """Schema para actualizar un itinerario"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(
        None, 
        pattern="^(draft|confirmed|in_progress|completed|cancelled)$"
    )
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_feedback: Optional[str] = None
    manually_edited: Optional[bool] = None


class ItineraryRead(ItineraryBase):
    """Schema para leer un itinerario"""
    id: int
    user_profile_id: int
    destination_id: int
    start_point_id: Optional[int] = None
    num_days: int
    end_date: Optional[date] = None
    generation_params: Optional[Dict[str, Any]] = None
    total_duration_minutes: Optional[int] = None
    total_cost: Optional[float] = None
    total_distance_meters: Optional[float] = None
    total_attractions: Optional[int] = None
    average_optimization_score: Optional[float] = None
    algorithms_used: Optional[Dict[str, str]] = None
    status: str
    manually_edited: bool
    user_rating: Optional[int] = None
    user_feedback: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ItineraryWithDays(ItineraryRead):
    """Itinerario completo con días incluidos"""
    days: List[ItineraryDayRead]


class ItineraryWithDetails(ItineraryWithDays):
    """Itinerario con días y detalles de atracciones"""
    destination_name: Optional[str] = None
    start_point_name: Optional[str] = None


# ============================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================

class ItineraryGenerationRequest(BaseModel):
    """Request para generar itinerario"""
    user_profile_id: int = Field(..., gt=0)
    city_center_id: int = Field(..., gt=0, description="ID de atracción céntrica")
    hotel_id: Optional[int] = Field(None, gt=0, description="ID del hotel (opcional)")
    num_days: int = Field(..., ge=1, le=14)
    start_date: datetime = Field(..., description="Fecha y hora de inicio")
    
    # Parámetros opcionales de generación
    optimization_mode: str = Field(default="balanced", pattern="^(distance|time|cost|balanced|score)$")
    max_radius_km: float = Field(default=10.0, gt=0, le=50)
    max_candidates: int = Field(default=50, ge=10, le=200)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_profile_id": 1,
                "city_center_id": 10,
                "hotel_id": 55,
                "num_days": 3,
                "start_date": "2025-11-25T09:00:00",
                "optimization_mode": "balanced",
                "max_radius_km": 10.0,
                "max_candidates": 50
            }
        }
    )


class ItineraryGenerationResponse(BaseModel):
    """Respuesta de generación de itinerario"""
    itinerary_id: int
    message: str
    itinerary: ItineraryWithDays
    metadata: Dict[str, Any]


# ============================================================
# EDIT SCHEMAS
# ============================================================

class ReorderAttractionsRequest(BaseModel):
    """Request para reordenar atracciones de un día"""
    day_number: int = Field(..., ge=1)
    new_order: List[int] = Field(..., min_length=1, description="IDs de atracciones en nuevo orden")


class AddAttractionRequest(BaseModel):
    """Request para agregar atracción a un día"""
    day_number: int = Field(..., ge=1)
    attraction_id: int = Field(..., gt=0)
    position: int = Field(..., ge=1, description="Posición en el orden (1-indexed)")


class RemoveAttractionRequest(BaseModel):
    """Request para eliminar atracción de un día"""
    day_number: int = Field(..., ge=1)
    attraction_id: int = Field(..., gt=0)