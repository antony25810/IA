# backend/shared/schemas/base.py
"""
Schemas base y utilidades reutilizables
"""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class TimestampMixin(BaseModel):
    """Mixin para timestamps comunes"""
    created_at: datetime
    updated_at: Optional[datetime] = None


class ResponseBase(BaseModel):
    """Base para respuestas de API"""
    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    """Parámetros de paginación"""
    skip: int = 0
    limit: int = 100
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "skip": 0,
                "limit": 100
            }
        }
    )


class PaginatedResponse(BaseModel):
    """Respuesta paginada genérica"""
    total: int
    skip: int
    limit: int
    items: list


class MessageResponse(BaseModel):
    """Respuesta simple con mensaje"""
    message: str
    detail: Optional[str] = None

class Location(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)