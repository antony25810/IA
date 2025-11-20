# backend/services/user_profiles/router.py
"""
Endpoints REST para gestión de perfiles de usuario
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, HTTPException, Query, Path, status
from sqlalchemy.orm import Session

from shared.database.base import get_db
from shared.schemas.user_profile import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileRead,
    UserProfileWithStats
)
from shared.schemas.base import MessageResponse
from .service import UserProfileService

router = APIRouter(
    prefix="/user-profiles",
    tags=["User Profiles"]
)


@router.post(
    "/",
    response_model=UserProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un perfil de usuario",
    description="Crea un nuevo perfil con preferencias personalizadas"
)
def create_user_profile(
    data: UserProfileCreate,
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo perfil de usuario.
    
    Campos requeridos:
    - preferences: Objeto con preferencias del usuario
      - interests: Lista de intereses (ej: ["cultural", "historia", "gastronomia"])
      - tourism_type: Tipo de turismo (cultural, aventura, familiar, lujo, mochilero, negocios)
      - pace: Ritmo de viaje (relaxed, moderate, intense)
    
    Ejemplo:
    ```json
    {
        "name": "Juan Pérez",
        "email": "juan@example.com",
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
    ```
    """
    return UserProfileService.create(db, data)


@router.get(
    "/",
    response_model=dict,
    summary="Listar perfiles de usuario",
    description="Obtiene una lista paginada de perfiles"
)
def list_user_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    budget_range: Optional[str] = Query(None, description="Filtrar por rango de presupuesto"),
    db: Session = Depends(get_db)
):
    """
    Listar perfiles de usuario con paginación.
    """
    profiles, total = UserProfileService.get_all(
        db=db,
        skip=skip,
        limit=limit,
        budget_range=budget_range
    )
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [UserProfileRead.model_validate(p) for p in profiles]
    }


@router.get(
    "/{profile_id}",
    response_model=UserProfileRead,
    summary="Obtener un perfil",
    description="Obtiene los detalles de un perfil específico"
)
def get_user_profile(
    profile_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Obtener perfil por ID.
    """
    return UserProfileService.get_or_404(db, profile_id)


@router.get(
    "/{profile_id}/stats",
    response_model=UserProfileWithStats,
    summary="Obtener perfil con estadísticas",
    description="Perfil con estadísticas de actividad (itinerarios, ratings)"
)
def get_user_profile_with_stats(
    profile_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Obtener perfil con estadísticas completas.
    
    Incluye:
    - Total de itinerarios creados
    - Itinerarios completados
    - Total de ratings dados
    - Rating promedio dado
    """
    stats = UserProfileService.get_with_statistics(db, profile_id)
    stats.pop('_sa_instance_state', None)
    return stats


@router.get(
    "/{profile_id}/recommendations",
    response_model=List[dict],
    summary="Obtener recomendaciones personalizadas",
    description="Recomendaciones de atracciones basadas en preferencias del usuario"
)
def get_recommendations(
    profile_id: int = Path(..., gt=0),
    destination_id: Optional[int] = Query(None, description="Filtrar por destino"),
    limit: int = Query(10, ge=1, le=50, description="Número de recomendaciones"),
    db: Session = Depends(get_db)
):
    """
    Obtener recomendaciones personalizadas.
    
    El sistema analiza:
    - Intereses del usuario
    - Presupuesto disponible
    - Restricciones de movilidad
    - Ratings históricos
    
    Y devuelve atracciones con un **recommendation_score** y razones del match.
    """
    return UserProfileService.get_recommendations(
        db=db,
        profile_id=profile_id,
        destination_id=destination_id,
        limit=limit
    )


@router.get(
    "/email/{email}",
    response_model=UserProfileRead,
    summary="Buscar perfil por email",
    description="Busca un perfil por dirección de email"
)
def get_profile_by_email(
    email: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    Buscar perfil por email.
    """
    profile = UserProfileService.get_by_email(db, email)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Perfil con email {email} no encontrado"
        )
    return profile


@router.put(
    "/{profile_id}",
    response_model=UserProfileRead,
    summary="Actualizar un perfil",
    description="Actualiza las preferencias y datos del perfil"
)
def update_user_profile(
    profile_id: int = Path(..., gt=0),
    data: UserProfileUpdate = ..., # type: ignore
    db: Session = Depends(get_db)
):
    """
    Actualizar perfil de usuario.
    
    Solo se actualizarán los campos proporcionados.
    """
    return UserProfileService.update(db, profile_id, data)


@router.delete(
    "/{profile_id}",
    response_model=MessageResponse,
    summary="Eliminar un perfil",
    description="Elimina un perfil y todos sus datos asociados"
)
def delete_user_profile(
    profile_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Eliminar perfil de usuario.
    
    """
    return UserProfileService.delete(db, profile_id)