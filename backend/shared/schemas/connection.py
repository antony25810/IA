# backend/shared/schemas/connection.py
"""
Schemas para conexiones entre atracciones
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from .base import ResponseBase, TimestampMixin

if TYPE_CHECKING:
    from .attraction import AttractionRead


class ConnectionBase(BaseModel):
    """Schema base de conexión"""
    distance_meters: float = Field(..., ge=0, description="Distancia en metros")
    travel_time_minutes: int = Field(..., gt=0, description="Tiempo de viaje en minutos")
    transport_mode: str = Field(..., description="Modo de transporte")
    cost: Optional[float] = Field(0.0, ge=0, description="Costo del desplazamiento")
    traffic_factor: Optional[float] = Field(1.0, ge=0.5, le=3.0, description="Factor de tráfico")
    
    @field_validator('transport_mode')
    @classmethod
    def validate_transport_mode(cls, v: str) -> str:
        """Validar modo de transporte"""
        valid_modes = ['walking', 'car', 'public_transport', 'bicycle', 'taxi']
        if v.lower() not in valid_modes:
            raise ValueError(f'transport_mode debe ser uno de: {", ".join(valid_modes)}')
        return v.lower()


class ConnectionCreate(ConnectionBase):
    """Schema para crear una conexión"""
    from_attraction_id: int = Field(..., gt=0, description="ID de atracción origen")
    to_attraction_id: int = Field(..., gt=0, description="ID de atracción destino")
    
    @field_validator('to_attraction_id')
    @classmethod
    def validate_different_attractions(cls, v: int, info) -> int:
        """Validar que origen y destino sean diferentes"""
        if 'from_attraction_id' in info.data and v == info.data['from_attraction_id']:
            raise ValueError('from_attraction_id y to_attraction_id deben ser diferentes')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "from_attraction_id": 1,
                "to_attraction_id": 2,
                "distance_meters": 5200,
                "travel_time_minutes": 20,
                "transport_mode": "car",
                "cost": 15.0,
                "traffic_factor": 1.2
            }
        }
    )


class ConnectionUpdate(BaseModel):
    """Schema para actualizar una conexión"""
    distance_meters: Optional[float] = Field(None, ge=0)
    travel_time_minutes: Optional[int] = Field(None, gt=0)
    transport_mode: Optional[str] = None
    cost: Optional[float] = Field(None, ge=0)
    traffic_factor: Optional[float] = Field(None, ge=0.5, le=3.0)


class ConnectionRead(ConnectionBase, ResponseBase, TimestampMixin):
    """Schema para leer una conexión"""
    id: int
    from_attraction_id: int
    to_attraction_id: int
    
    model_config = ConfigDict(from_attributes=True)


class ConnectionWithAttractions(ConnectionRead):
    """Conexión con información de atracciones"""
    from_attraction: 'AttractionRead'  # ← Forward reference
    to_attraction: 'AttractionRead'    # ← Forward reference


class ConnectionSearchParams(BaseModel):
    """Parámetros de búsqueda de conexiones"""
    from_attraction_id: Optional[int] = None
    to_attraction_id: Optional[int] = None
    transport_mode: Optional[str] = None
    max_distance_meters: Optional[float] = Field(None, gt=0)
    max_travel_time_minutes: Optional[int] = Field(None, gt=0)