# backend/shared/schemas/destination.py
"""
Schemas para destinos turísticos
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .base import ResponseBase, TimestampMixin


class DestinationBase(BaseModel):
    """Schema base de destino"""
    name: str = Field(..., min_length=1, max_length=255, description="Nombre del destino")
    country: str = Field(..., min_length=1, max_length=100, description="País")
    state: Optional[str] = Field(None, max_length=100, description="Estado o región")
    timezone: Optional[str] = Field(None, max_length=50, description="Zona horaria")
    description: Optional[str] = Field(None, max_length=1000, description="Descripción del destino")
    population: Optional[int] = Field(None, ge=0, description="Población aproximada")


class DestinationCreate(DestinationBase):
    """Schema para crear un destino"""
    location: dict = Field(..., description="Coordenadas geográficas")
    # Formato: {"lat": -12.0464, "lon": -77.0428}
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Lima",
                "country": "Perú",
                "state": "Lima",
                "location": {"lat": -12.0464, "lon": -77.0428},
                "timezone": "America/Lima",
                "description": "Capital del Perú, ciudad histórica con gran oferta gastronómica",
                "population": 10000000
            }
        }
    )


class DestinationUpdate(BaseModel):
    """Schema para actualizar un destino"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    population: Optional[int] = Field(None, ge=0)


class DestinationRead(DestinationBase, ResponseBase, TimestampMixin):
    """Schema para leer un destino"""
    id: int
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Lima",
                "country": "Perú",
                "state": "Lima",
                "timezone": "America/Lima",
                "description": "Capital del Perú",
                "population": 10000000,
                "created_at": "2025-01-19T22:30:00",
                "updated_at": None
            }
        }
    )


class DestinationWithStats(DestinationRead):
    """Destino con estadísticas"""
    total_attractions: int = Field(..., description="Número total de atracciones")
    avg_rating: Optional[float] = Field(None, description="Rating promedio de atracciones")