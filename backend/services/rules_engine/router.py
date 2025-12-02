"""
Router para el motor de reglas (Forward Chaining)
Expone endpoints para enriquecimiento de perfiles y validación
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Path, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime, time
from pydantic import BaseModel, Field

from shared.database.base import get_db
from shared. database.models import UserProfile
from . service import RulesEngineService

router = APIRouter(prefix="/rules", tags=["Rules Engine"])


# ============================================================================
# MODELOS PYDANTIC PARA REQUESTS
# ============================================================================

class WeatherContext(BaseModel):
    """Información meteorológica"""
    condition: str = Field(..., description="Condición climática", example="sunny")
    temperature: Optional[float] = Field(None, description="Temperatura en °C", example=28.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "condition": "sunny",
                "temperature": 28
            }
        }


class LocationContext(BaseModel):
    """Información de ubicación"""
    city: Optional[str] = Field(None, example="Arequipa")
    country: Optional[str] = Field(None, example="Peru")
    
    class Config:
        json_schema_extra = {
            "example": {
                "city": "Arequipa",
                "country": "Peru"
            }
        }


class EnrichmentContext(BaseModel):
    """Contexto para enriquecimiento de perfil de usuario"""
    current_date: Optional[datetime] = Field(
        None, 
        description="Fecha y hora actual",
        example="2025-01-21T10:30:00"
    )
    current_time: Optional[time] = Field(
        None,
        description="Hora actual",
        example="10:30:00"
    )
    weather: Optional[Dict[str, Any]] = Field(
        None,
        description="Información del clima actual",
        example={"condition": "sunny", "temperature": 28}
    )
    location: Optional[Dict[str, Any]] = Field(
        None,
        description="Información de ubicación del usuario",
        example={"city": "Arequipa", "country": "Peru"}
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_date": "2025-01-21T10:30:00",
                "current_time": "10:30:00",
                "weather": {
                    "condition": "sunny",
                    "temperature": 28
                },
                "location": {
                    "city": "Arequipa",
                    "country": "Peru"
                }
            }
        }


class ItineraryValidationRequest(BaseModel):
    """Request para validación de itinerario"""
    itinerary: Dict[str, Any] = Field(
        ...,
        description="Itinerario a validar",
        example={
            "attractions": [
                {"id": 1, "name": "Plaza de Armas", "duration_minutes": 60},
                {"id": 2, "name": "Monasterio Santa Catalina", "duration_minutes": 120}
            ],
            "total_duration_minutes": 180,
            "estimated_cost": 50.0
        }
    )
    enable_trace: bool = Field(
        default=False,
        description="Incluir traza de ejecución"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "itinerary": {
                    "attractions": [
                        {"id": 1, "name": "Plaza de Armas", "duration_minutes": 60},
                        {"id": 2, "name": "Monasterio Santa Catalina", "duration_minutes": 120}
                    ],
                    "total_duration_minutes": 180,
                    "estimated_cost": 50.0
                },
                "enable_trace": False
            }
        }


# ============================================================================
# ENDPOINTS
# ============================================================================

@router. post("/enrich-profile/{user_profile_id}")
async def enrich_user_profile(
    user_profile_id: int = Path(..., description="ID del perfil de usuario", ge=1, example=1),
    context: Optional[EnrichmentContext] = Body(
        default=None,
        description="Contexto adicional para el enriquecimiento"
    ),
    enable_trace: bool = Query(
        default=False,
        description="Incluir traza de ejecución del motor de reglas"
    ),
    db: Session = Depends(get_db)
):
    """
    Enriquece el perfil de un usuario aplicando reglas de inferencia
    
    **Proceso:**
    1. Carga el perfil del usuario desde la BD
    2. Construye working memory con datos del perfil + contexto
    3. Aplica motor de Forward Chaining con reglas de perfil
    4. Retorna perfil enriquecido con nuevos insights
    
    **Reglas aplicadas:**
    - Categorización de edad
    - Inferencia de budget desde mobility
    - Ajustes por clima
    - Recomendaciones temporales
    - Validaciones de consistencia
    
    **Ejemplo de respuesta:**
    ```json
    {
      "user_profile_id": 1,
      "original_profile": {
        "name": "Juan Pérez",
        "preferences": {"interests": ["cultura", "historia"]},
        "budget_range": "medium"
      },
      "computed_profile": {
        "age_category": "adulto",
        "inferred_budget": "medium",
        "recommended_activities": ["museos", "tours guiados"],
        "weather_suitable": true
      },
      "warnings": [],
      "validation_errors": [],
      "applied_rules": ["rule_age_category", "rule_budget_from_mobility"],
      "metadata": {
        "rules_fired": 5,
        "iterations": 2
      },
      "execution_trace": null
    }
    ```
    """
    # Convertir contexto Pydantic → dict
    context_dict = None
    if context:
        context_dict = {}
        if context.current_date:
            context_dict['current_date'] = context.current_date
        if context.current_time:
            context_dict['current_time'] = context.current_time
        if context.weather:
            context_dict['weather'] = context.weather
        if context. location:
            context_dict['location'] = context.location
    
    # Llamar al servicio (método REAL: enrich_user_profile)
    result = RulesEngineService. enrich_user_profile(
        db=db,
        user_profile_id=user_profile_id,
        context=context_dict,
        enable_trace=enable_trace
    )
    
    return result


@router.post("/validate-itinerary/{user_profile_id}")
async def validate_itinerary(
    user_profile_id: int = Path(... , description="ID del perfil de usuario", ge=1, example=1),
    request: ItineraryValidationRequest = Body(
        ...,
        description="Itinerario a validar y opciones"
    ),
    db: Session = Depends(get_db)
):
    """
    Valida un itinerario aplicando reglas de negocio
    
    **Validaciones:**
    - Factibilidad temporal (horarios, duración)
    - Compatibilidad con presupuesto del usuario
    - Accesibilidad (movilidad del usuario vs. requisitos)
    - Coherencia de la ruta
    - Restricciones climáticas
    
    **Respuesta:**
    ```json
    {
      "is_valid": true,
      "warnings": ["El tiempo entre atracciones 2 y 3 es ajustado"],
      "validation_errors": [],
      "applied_rules": ["temporal_feasibility", "budget_check"],
      "metadata": {
        "rules_fired": 4,
        "iterations": 1
      },
      "execution_trace": null
    }
    ```
    """
    # Llamar al servicio
    result = RulesEngineService.validate_itinerary(
        db=db,
        itinerary=request.itinerary,
        user_profile_id=user_profile_id,
        enable_trace=request.enable_trace
    )
    
    return result


@router.get("/explain/{user_profile_id}")
async def explain_rules(
    user_profile_id: int = Path(..., description="ID del perfil de usuario", ge=1, example=1),
    db: Session = Depends(get_db)
):
    """
    Explica qué reglas se aplicarían a un perfil de usuario
    
    **Respuesta:**
    ```json
    {
      "user_profile_id": 1,
      "total_rules": 16,
      "applicable_rules": 8,
      "rules_by_category": {
        "profile": [
          {
            "id": "rule_age_category",
            "name": "Categorización por edad",
            "description": "Asigna categoría según edad del usuario",
            "priority": "HIGH",
            "category": "profile",
            "is_applicable": true,
            "reason": "user_age está definido"
          }
        ],
        "temporal": [... ],
        "weather": [...],
        "validation": [...]
      },
      "all_rules": [...]
    }
    ```
    """
    # Llamar al servicio 
    result = RulesEngineService.explain_rules(
        db=db,
        user_profile_id=user_profile_id,
        context=None  
    )
    
    return result


@router.post("/recommendations/{user_profile_id}")
async def get_recommendations(
    user_profile_id: int = Path(..., description="ID del perfil de usuario", ge=1, example=1),
    context: Optional[EnrichmentContext] = Body(
        default=None,
        description="Contexto para personalizar recomendaciones"
    ),
    db: Session = Depends(get_db)
):
    """
    Genera recomendaciones personalizadas usando el motor de reglas
    
    **Proceso:**
    1.  Enriquece el perfil del usuario
    2. Aplica reglas de recomendación
    3.  Retorna sugerencias priorizadas
    
    **Respuesta:**
    ```json
    {
      "user_profile_id": 1,
      "recommendations": [
        {
          "type": "activity",
          "suggestion": "Visitar museos por la mañana",
          "reason": "Alta compatibilidad con interés en historia y cultura",
          "priority": "high"
        },
        {
          "type": "timing",
          "suggestion": "Evitar actividades al aire libre entre 12:00-15:00",
          "reason": "Temperatura elevada (32°C)",
          "priority": "medium"
        }
      ],
      "context": {
        "date": "2025-01-21",
        "time": "10:30:00"
      }
    }
    ```
    """
    # Convertir contexto
    context_dict = None
    if context:
        context_dict = {}
        if context.current_date:
            context_dict['current_date'] = context. current_date
        if context. current_time:
            context_dict['current_time'] = context.current_time
        if context.weather:
            context_dict['weather'] = context.weather
        if context.location:
            context_dict['location'] = context.location
    
    # Llamar al servicio
    result = RulesEngineService.get_recommendations(
        db=db,
        user_profile_id=user_profile_id,
        context=context_dict
    )
    
    return result


@router.get("/rules")
async def list_all_rules():
    """
    Lista todas las reglas disponibles en el motor
    
    **Respuesta:**
    ```json
    {
      "total_rules": 16,
      "categories": ["profile", "temporal", "weather", "validation"],
      "rules_by_category": {
        "profile": [
          {
            "id": "rule_age_category",
            "name": "Categorización por edad",
            "description": "Asigna categoría según edad",
            "priority": "HIGH",
            "category": "profile"
          }
        ],
        "temporal": [...],
        "weather": [...],
        "validation": [...]
      },
      "all_rules": [...]
    }
    ```
    """
    # Llamar al servicio
    result = RulesEngineService.list_all_rules()
    
    return result