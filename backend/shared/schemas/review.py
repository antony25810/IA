# backend/shared/schemas/review.py
"""
Schemas para reseñas y ratings
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
from .base import ResponseBase, TimestampMixin


class ReviewBase(BaseModel):
    """Schema base de reseña"""
    text: str = Field(..., min_length=10, max_length=5000, description="Texto de la reseña")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating de 1 a 5")


class ReviewCreate(ReviewBase):
    """Schema para crear una reseña"""
    attraction_id: int = Field(..., gt=0, description="ID de la atracción")
    source: str = Field(..., max_length=100, description="Fuente de la reseña")
    language: Optional[str] = Field("es", max_length=10, description="Idioma de la reseña")
    author: Optional[str] = Field(None, max_length=255, description="Autor de la reseña")
    review_date: Optional[datetime] = Field(None, description="Fecha de la reseña original")
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        valid_sources = ['google_places', 'tripadvisor', 'yelp', 'internal']
        if v.lower() not in valid_sources:
            raise ValueError(f'source debe ser uno de: {", ".join(valid_sources)}')
        return v.lower()
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "attraction_id": 1,
                "source": "google_places",
                "text": "Hermosa plaza histórica en el corazón de Lima. Muy bien conservada y rodeada de arquitectura colonial impresionante.",
                "rating": 5,
                "language": "es",
                "author": "Usuario123",
                "review_date": "2025-01-15T10:30:00"
            }
        }
    )


class ReviewRead(ReviewBase, ResponseBase, TimestampMixin):
    """Schema para leer una reseña"""
    id: int
    attraction_id: int
    source: str
    source_id: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    language: str
    author: Optional[str] = None
    review_date: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AttractionRatingBase(BaseModel):
    """Schema base de rating"""
    rating: int = Field(..., ge=1, le=5, description="Rating de 1 a 5")
    feedback: Optional[str] = Field(None, max_length=1000, description="Comentario opcional")
    visit_context: Optional[str] = Field(None, description="Contexto de la visita")
    
    @field_validator('visit_context')
    @classmethod
    def validate_visit_context(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_contexts = ['solo', 'pareja', 'familia', 'amigos', 'trabajo']
            if v.lower() not in valid_contexts:
                raise ValueError(f'visit_context debe ser uno de: {", ".join(valid_contexts)}')
            return v.lower()
        return v


class AttractionRatingCreate(AttractionRatingBase):
    """Schema para crear un rating"""
    user_profile_id: int = Field(..., gt=0, description="ID del perfil de usuario")
    attraction_id: int = Field(..., gt=0, description="ID de la atracción")
    visit_date: Optional[datetime] = Field(None, description="Fecha de visita")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_profile_id": 1,
                "attraction_id": 2,
                "rating": 5,
                "feedback": "Excelente museo, muy bien organizado",
                "visit_context": "familia",
                "visit_date": "2025-01-19T14:00:00"
            }
        }
    )


class AttractionRatingRead(AttractionRatingBase, ResponseBase):
    """Schema para leer un rating"""
    id: int
    user_profile_id: int
    attraction_id: int
    visit_date: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)