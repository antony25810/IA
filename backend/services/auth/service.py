# backend/services/auth/service.py
from datetime import datetime, timedelta
from typing import Optional, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext
from jose import jwt, JWTError

from shared.database.models import User, UserProfile
from shared.schemas. user import UserCreate
from shared. utils.logger import setup_logger
from shared.config.settings import get_settings

logger = setup_logger(__name__)
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hashear contraseña"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verificar contraseña"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> User:
        """
        Crear nuevo usuario Y su perfil asociado
        
        **Proceso:**
        1. Valida que el email no exista
        2. Crea registro en tabla `users`
        3. Crea registro en tabla `user_profiles` (relación 1:1)
        4.  Retorna el usuario con perfil vinculado
        """
        # 1. Validación de existencia
        existing_user = db. query(User).filter(User. email == user_in.email). first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado."
            )

        try:
            # 2. Hash del password
            hashed_pwd = UserService.get_password_hash(user_in.password)
            
            # 3.  Crear usuario
            db_user = User(
                email=user_in.email,
                hashed_password=hashed_pwd,
                full_name=user_in.full_name, 
                is_active=True
            )
            
            db.add(db_user)
            db.flush()  # Asigna ID al usuario SIN hacer commit
            
            # 4. Crear perfil de usuario automáticamente
            db_profile = UserProfile(
                user_id=db_user.id,
                budget_range="medium",  # Valor por defecto
                preferences={
                    "interests": [],
                    "tourism_type": "cultural",
                    "pace": "moderate"
                },
                mobility_constraints={}
            )
            
            db.add(db_profile)
            db.commit()
            db.refresh(db_user)
            db.refresh(db_profile)
            
            logger.info(f"✅ Usuario creado: {db_user.email} (ID: {db_user.id}, Profile ID: {db_profile.id})")
            
            # Adjuntar profile_id al objeto user para acceso fácil
            db_user.profile_id = db_profile.id
            
            return db_user

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error creando usuario: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error interno al crear el usuario: {str(e)}"
            )

    @staticmethod
    def authenticate_user(
        db: Session, 
        email: str, 
        password: str
    ) -> Union[User, bool]:
        """Autenticar usuario"""
        user = db. query(User).filter(User. email == email).first()
        if not user:
            return False
        if not UserService.verify_password(password, user.hashed_password):
            return False
        return user

    @staticmethod
    def get_user_with_profile(db: Session, user_id: int) -> dict:
        """
        Obtener usuario con su perfil asociado
        
        **Uso:** Para retornar en login/register
        """
        user = db.query(User).filter(User.id == user_id). first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        profile = db.query(UserProfile). filter(UserProfile.user_id == user_id).first()
        
        return {
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "is_active": user.is_active,
            "profile_id": profile.id if profile else None
        }

    @staticmethod
    def create_access_token(
        data: dict, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Crear JWT token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        return encoded_jwt