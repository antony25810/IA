# backend/services/auth/router.py
from datetime import timedelta
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from shared.database.models.user import User
from shared.database.base import get_db
from shared. database.models import UserProfile
from shared.schemas.user import UserCreate, UserRead
from shared.schemas.auth import Token, LoginRequest
from shared.config.settings import get_settings
from .service import UserService
from .dependencies import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication & Users"]
)

settings = get_settings()


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db)
):
    """
    Registrar un nuevo usuario
    
    **Proceso:**
    1. Crea usuario en tabla `users`
    2. Crea perfil en tabla `user_profiles` (automático)
    3. Genera token JWT
    4. Retorna datos completos para el frontend
    
    **Respuesta:**
    ```json
    {
      "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "token_type": "bearer",
      "user_id": 1,
      "name": "Juan Pérez",
      "email": "juan@example.com",
      "user_profile_id": 1
    }
    ```
    """
    # 1. Crear usuario (el service ya crea el perfil automáticamente)
    user = UserService.create_user(db=db, user_in=user_in)
    
    # 2. Obtener el perfil creado
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    
    # 3. Generar token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = UserService.create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    # 4. Retornar datos completos
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.full_name,
        "email": user.email,
        "user_profile_id": user_profile.id if user_profile else None
    }


@router.post("/login", response_model=dict)
def login_json(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login con JSON (email/password)
    
    **Retorna:**
    - access_token
    - token_type
    - user_id
    - name
    - email
    - user_profile_id
    """
    # 1. Autenticar
    user = UserService.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Obtener perfil
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    
    # 3. Generar token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = UserService.create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    # 4. Retornar datos completos
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.full_name,
        "email": user.email,
        "user_profile_id": user_profile.id if user_profile else None
    }


@router.post("/token", response_model=dict)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login con OAuth2 form (username/password)
    Usado por Swagger UI
    """
    user = UserService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = UserService.create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.full_name,
        "email": user.email,
        "user_profile_id": user_profile.id if user_profile else None
    }

@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Validar token y obtener usuario actual.
    Usado por el Frontend al recargar la página para verificar sesión.
    """
    return current_user