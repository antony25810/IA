# backend/shared/schemas/itinerary.py
"""
Schemas para itinerarios
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from .base import ResponseBase, TimestampMixin

if TYPE_CHECKING:
    from .user_profile import UserProfileRead
    from .destination import DestinationRead
    from .attraction import AttractionRead


class ItineraryBase(BaseModel):
    """Schema base de itinerario"""
    name: Optional[str] = Field(None, max_length=255, description="Nombre del itinerario")
    description: Optional[str] = Field(None, max_length=1000, description="Descripción")
    start_date: Optional[datetime] = Field(None, description="Fecha de inicio planificada")


class RouteDataSchema(BaseModel):
    """Schema para datos de ruta"""
    sequence: List[Dict[str, Any]] = Field(..., description="Secuencia de atracciones")
    connections: List[Dict[str, Any]] = Field(..., description="Conexiones entre atracciones")


class ItineraryCreate(ItineraryBase):
    """Schema para crear un itinerario"""
    user_profile_id: int = Field(..., gt=0, description="ID del perfil de usuario")
    destination_id: int = Field(..., gt=0, description="ID del destino")
    route_data: RouteDataSchema = Field(..., description="Datos de la ruta calculada")
    total_duration: Optional[int] = Field(None, gt=0, description="Duración total en minutos")
    total_cost: Optional[float] = Field(None, ge=0, description="Costo total estimado")
    total_distance: Optional[float] = Field(None, ge=0, description="Distancia total en metros")
    optimization_score: Optional[float] = Field(None, ge=0, le=100, description="Puntuación de optimización")
    algorithms_used: Optional[Dict[str, str]] = Field(None, description="Algoritmos utilizados")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_profile_id": 1,
                "destination_id": 1,
                "name": "Tour Cultural Lima",
                "description": "Recorrido por los principales museos y sitios históricos",
                "route_data": {
                    "sequence": [
                        {
                            "order": 1,
                            "attraction_id": 1,
                            "arrival_time": "09:00",
                            "departure_time": "10:30",
                            "visit_duration": 90
                        }
                    ],
                    "connections": [
                        {
                            "from": 1,
                            "to": 2,
                            "transport": "walking",
                            "duration": 15
                        }
                    ]
                },
                "total_duration": 480,
                "total_cost": 150.0,
                "total_distance": 8500,
                "optimization_score": 92.5,
                "algorithms_used": {
                    "search": "BFS",
                    "routing": "A*",
                    "ml_model": "neural_network_v1"
                },
                "start_date": "2025-02-15T09:00:00"
            }
        }
    )


class ItineraryUpdate(BaseModel):
    """Schema para actualizar un itinerario"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, pattern="^(draft|confirmed|in_progress|completed|cancelled)$")
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_feedback: Optional[str] = Field(None, max_length=1000)
    start_date: Optional[datetime] = None


class ItineraryRead(ItineraryBase, ResponseBase, TimestampMixin):
    """Schema para leer un itinerario"""
    id: int
    user_profile_id: int
    destination_id: int
    route_data: Dict[str, Any]
    total_duration: Optional[int] = None
    total_cost: Optional[float] = None
    total_distance: Optional[float] = None
    optimization_score: Optional[float] = None
    algorithms_used: Optional[Dict[str, str]] = None
    status: str
    user_rating: Optional[int] = None
    user_feedback: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ItineraryWithDetails(ItineraryRead):
    """Itinerario con detalles completos"""
    user_profile: 'UserProfileRead'  # ← Forward reference
    destination: 'DestinationRead'   # ← Forward reference
    attractions: List['AttractionRead']  # ← Forward reference


class ItinerarySearchParams(BaseModel):
    """Parámetros de búsqueda de itinerarios"""
    user_profile_id: Optional[int] = None
    destination_id: Optional[int] = None
    status: Optional[str] = None
    start_date_from: Optional[datetime] = None
    start_date_to: Optional[datetime] = None