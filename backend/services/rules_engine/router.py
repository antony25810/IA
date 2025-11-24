# backend/services/rules_engine/router.py
"""
Endpoints REST para motor de reglas
"""
from typing import Optional, Dict
from fastapi import APIRouter, Depends, Query, Body, Path, status
from sqlalchemy.orm import Session

from shared.database.base import get_db
from .service import RulesEngineService

router = APIRouter(
    prefix="/rules",
    tags=["Rules Engine (Forward Chaining)"]
)


@router.post(
    "/enrich-profile/{user_profile_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Enriquecer perfil de usuario",
    description="Aplica reglas de negocio para enriquecer el perfil del usuario"
)
def enrich_user_profile(
    user_profile_id: int = Path(..., gt=0, description="ID del perfil de usuario"),
    context: Optional[Dict] = Body(
        None,
        description="Contexto adicional (fecha, hora, clima)",
        examples=[{
            "current_date": "2025-01-21",
            "current_time": "10:30:00",
            "weather": {
                "condition": "sunny",
                "temperature": 28
            }
        }]
    ),
    enable_trace: bool = Query(False, description="Guardar traza de ejecución"),
    db: Session = Depends(get_db)
):
    """
    Enriquecer perfil de usuario con reglas de negocio.
    
    El motor aplica reglas según:
    - Tipo de turismo (familiar, aventura, etc.)
    - Presupuesto (bajo, medio, alto, lujo)
    - Restricciones de movilidad
    - Ritmo de viaje (relaxed, moderate, intense)
    - Contexto temporal (mañana, tarde, noche)
    - Clima (lluvia, calor, etc.)
    
    Ejemplo de respuesta:
    ```json
    {
        "computed_profile": {
            "family_friendly": true,
            "max_daily_attractions": 3,
            "required_amenities": ["wheelchair", "stroller_friendly"],
            "priority_categories": ["entretenimiento", "naturaleza"]
        },
        "applied_rules": [
            "PROFILE_001: Preferencias familiares agregadas",
            "PROFILE_005: Ritmo relajado - máx 3 atracciones/día"
        ],
        "warnings": [],
        "metadata": {
            "rules_fired": 2,
            "iterations": 1
        }
    }
    ```
    
    Uso:
    - Llamar antes de generar itinerarios
    - El `computed_profile` se guarda en la BD
    - Usar las recomendaciones para filtrar atracciones
    """
    return RulesEngineService.enrich_user_profile(
        db=db,
        user_profile_id=user_profile_id,
        context=context,
        enable_trace=enable_trace
    )


@router.post(
    "/validate-itinerary",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Validar itinerario",
    description="Valida un itinerario contra reglas de negocio"
)
def validate_itinerary(
    user_profile_id: int = Query(..., gt=0),
    itinerary: Dict = Body(..., description="Itinerario a validar"),
    enable_trace: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Validar itinerario contra reglas de negocio.
    
    Verifica:
    - Horarios de atracciones
    - Tiempo de viaje realista
    - Presupuesto total dentro de límites
    - Número de atracciones por día
    - Fatiga del viajero
    
    Ejemplo de itinerario:
    ```json
    {
        "attractions": [
            {"id": 1, "name": "Plaza Mayor"},
            {"id": 2, "name": "Museo Larco"},
            {"id": 3, "name": "Parque de las Aguas"}
        ],
        "segments": [
            {"travel_time_minutes": 50},
            {"travel_time_minutes": 30}
        ],
        "total_cost": 150
    }
    ```
    
    Respuesta:
    ```json
    {
        "is_valid": true,
        "warnings": [
            {
                "type": "travel_time",
                "message": "Tiempo de viaje alto: 80 minutos",
                "recommendation": "Considere agrupar por zona"
            }
        ],
        "validation_errors": []
    }
    ```
    """
    return RulesEngineService.validate_itinerary(
        db=db,
        itinerary=itinerary,
        user_profile_id=user_profile_id,
        enable_trace=enable_trace
    )


@router.post(
    "/explain/{user_profile_id}",
    response_model=dict,
    summary="Explicar reglas aplicables",
    description="Explica qué reglas se aplicarían a un perfil"
)
def explain_rules(
    user_profile_id: int = Path(..., gt=0),
    context: Optional[Dict] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Explicar qué reglas se aplicarían a un perfil.
    
    Respuesta:
    - Todas las reglas definidas
    - Cuáles son aplicables al perfil
    - Cuáles ya fueron ejecutadas
    - Agrupadas por categoría
    
    Ejemplo:
    ```json
    {
        "total_rules": 16,
        "applicable_rules": 5,
        "rules_by_category": {
            "profile": [
                {
                    "rule_id": "PROFILE_001",
                    "name": "Turismo Familiar",
                    "is_applicable": true
                }
            ],
            "temporal": [...],
            "weather": [...],
            "validation": [...]
        }
    }
    ```
    """
    return RulesEngineService.explain_rules(
        db=db,
        user_profile_id=user_profile_id,
        context=context
    )


@router.post(
    "/recommendations/{user_profile_id}",
    response_model=dict,
    summary="Obtener recomendaciones",
    description="Genera recomendaciones basadas en reglas"
)
def get_recommendations(
    user_profile_id: int = Path(..., gt=0),
    context: Optional[Dict] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Obtener recomendaciones basadas en reglas aplicadas.
    
    Genera:
    - Categorías recomendadas
    - Categorías prioritarias (según hora del día)
    - Categorías a evitar (según clima)
    - Máximo de atracciones por día
    - Rangos de precio permitidos
    - Rating mínimo
    - Amenidades requeridas
    - Modos de transporte preferidos
    
    Ejemplo:
    ```json
    {
        "recommendations": {
            "recommended_categories": ["entretenimiento", "naturaleza"],
            "priority_categories": ["cultural", "museos"],
            "avoid_categories": ["naturaleza"],
            "max_daily_attractions": 3,
            "allowed_price_ranges": ["gratis", "bajo"],
            "min_rating": 4.0,
            "required_amenities": ["wheelchair"],
            "special_requirements": {
                "family_friendly": true,
                "require_accessibility": true,
                "prefer_indoor": false
            }
        }
    }
    ```
    
    Uso:
    - Integrar con BFS para filtrar candidatos
    - Usar en búsquedas de atracciones
    - Ajustar scores en A*
    """
    return RulesEngineService.get_recommendations(
        db=db,
        user_profile_id=user_profile_id,
        context=context
    )


@router.get(
    "/rules",
    response_model=dict,
    summary="Listar todas las reglas",
    description="Lista todas las reglas definidas en el sistema"
)
def list_all_rules():
    """
    Listar todas las reglas disponibles.
    
    Respuesta:
    - Total de reglas
    - Categorías disponibles
    - Reglas agrupadas por categoría
    - Lista completa con ID, nombre, descripción, prioridad
    
    Categorías:
    - profile: Reglas de perfil de usuario
    - temporal: Reglas de contexto temporal
    - weather: Reglas de clima
    - validation: Reglas de validación de itinerarios
    
    Útil para:
    - Documentación del sistema
    - Debugging
    - Entender qué reglas están activas
    """
    return RulesEngineService.list_all_rules()