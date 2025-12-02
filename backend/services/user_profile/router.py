# backend/services/user_profiles/router.py
"""
Endpoints REST para gestión de perfiles de usuario
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from services.auth.dependencies import get_current_user
from shared.database.models import User

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
    description="Crea un nuevo perfil vinculado a un usuario existente"
)
def create_user_profile(
    data: UserProfileCreate,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo perfil de usuario.
    
    Requiere el ID del usuario registrado (user_id).
    """
    return UserProfileService.create(db, current_user.id, data)  


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
    "/user/{user_id}",
    response_model=UserProfileRead,
    summary="Obtener perfil por User ID",
    description="Obtiene el perfil asociado a un ID de usuario de login"
)
def get_profile_by_user_id(
    user_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Obtener el perfil vinculado a un usuario específico.
    """
    profile = UserProfileService.get_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró perfil para el usuario {user_id}"
        )
    return profile


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
    """
    stats = UserProfileService.get_with_statistics(db, profile_id)
    if isinstance(stats, dict) and '_sa_instance_state' in stats:
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
    """
    return UserProfileService.get_recommendations(
        db=db,
        profile_id=profile_id,
        destination_id=destination_id,
        limit=limit
    )


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