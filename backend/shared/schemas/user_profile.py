# backend/shared/schemas/user_profile.py
"""
Schemas para perfiles de usuario
"""
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import ResponseBase, TimestampMixin


class UserProfileBase(BaseModel):
    """Schema base de perfil de usuario"""
    name: Optional[str] = Field(None, max_length=255, description="Nombre del usuario")
    email: Optional[EmailStr] = Field(None, description="Email del usuario")


class PreferencesSchema(BaseModel):
    """Schema para preferencias del usuario"""
    interests: List[str] = Field(..., min_length=1, description="Intereses principales")
    tourism_type: str = Field(..., description="Tipo de turismo preferido")
    pace: str = Field(..., pattern="^(relaxed|moderate|intense)$", description="Ritmo de viaje")
    accessibility_needs: Optional[List[str]] = Field(default_factory=list)
    dietary_restrictions: Optional[List[str]] = Field(default_factory=list)
    
    @field_validator('tourism_type')
    @classmethod
    def validate_tourism_type(cls, v: str) -> str:
        valid_types = ['cultural', 'aventura', 'familiar', 'lujo', 'mochilero', 'negocios']
        if v.lower() not in valid_types:
            raise ValueError(f'tourism_type debe ser uno de: {", ".join(valid_types)}')
        return v.lower()


class MobilityConstraintsSchema(BaseModel):
    """Schema para restricciones de movilidad"""
    max_walking_distance: Optional[int] = Field(None, gt=0, description="Distancia máxima a caminar en metros")
    preferred_transport: Optional[List[str]] = Field(default_factory=list)
    avoid_transport: Optional[List[str]] = Field(default_factory=list)


class UserProfileCreate(UserProfileBase):
    """Schema para crear un perfil de usuario"""
    preferences: PreferencesSchema = Field(..., description="Preferencias del usuario")
    budget_range: Optional[str] = Field(None, pattern="^(bajo|medio|alto|lujo)$")
    budget_min: Optional[int] = Field(None, ge=0, description="Presupuesto mínimo por día")
    budget_max: Optional[int] = Field(None, ge=0, description="Presupuesto máximo por día")
    mobility_constraints: Optional[MobilityConstraintsSchema] = None
    
    @field_validator('budget_max')
    @classmethod
    def validate_budget_range(cls, v: Optional[int], info) -> Optional[int]:
        """Validar que budget_max >= budget_min"""
        if v is not None and 'budget_min' in info.data:
            budget_min = info.data.get('budget_min')
            if budget_min is not None and v < budget_min:
                raise ValueError('budget_max debe ser mayor o igual a budget_min')
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Juan Pérez",
                "email": "juan.perez@example.com",
                "preferences": {
                    "interests": ["cultural", "historia", "gastronomia"],
                    "tourism_type": "cultural",
                    "pace": "moderate",
                    "accessibility_needs": [],
                    "dietary_restrictions": []
                },
                "budget_range": "medio",
                "budget_min": 100,
                "budget_max": 300,
                "mobility_constraints": {
                    "max_walking_distance": 3000,
                    "preferred_transport": ["walking", "car"],
                    "avoid_transport": []
                }
            }
        }
    )


class UserProfileUpdate(BaseModel):
    """Schema para actualizar un perfil de usuario"""
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    preferences: Optional[Dict[str, Any]] = None
    budget_range: Optional[str] = None
    budget_min: Optional[int] = Field(None, ge=0)
    budget_max: Optional[int] = Field(None, ge=0)
    mobility_constraints: Optional[Dict[str, Any]] = None


class UserProfileRead(UserProfileBase, ResponseBase, TimestampMixin):
    """Schema para leer un perfil de usuario"""
    id: int
    user_id: int  # <-- CAMBIO: UUID a int
    preferences: Dict[str, Any]
    budget_range: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    mobility_constraints: Optional[Dict[str, Any]] = None
    computed_profile: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


class UserProfileWithStats(UserProfileRead):
    """Perfil de usuario con estadísticas"""
    total_itineraries: int = Field(..., description="Número total de itinerarios creados")
    total_ratings: int = Field(..., description="Número total de ratings dados")
    avg_rating_given: Optional[float] = Field(None, description="Rating promedio dado")