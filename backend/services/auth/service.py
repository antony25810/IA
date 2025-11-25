from datetime import datetime, timedelta
from typing import Optional, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext
from jose import jwt, JWTError

from shared.database.models import User
from shared.schemas.user import UserCreate
from shared.utils.logger import setup_logger
# IMPORTACIÓN DE SETTINGS
from shared.config import settings  

logger = setup_logger(__name__)
settings = settings.get_settings()

# Usamos settings para la configuración
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> User:
        # Validación de existencia
        existing_user = db.query(User).filter(User.email == user_in.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado."
            )

        try:
            # Creación del usuario
            # IMPORTANTE: Aquí nos aseguramos de pasar user_in.password (string)
            hashed_pwd = UserService.get_password_hash(user_in.password)
            
            db_user = User(
                email=user_in.email,
                hashed_password=hashed_pwd,
                full_name=user_in.full_name,
                is_active=user_in.is_active
            )
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            logger.info(f"Usuario creado exitosamente: {db_user.email} (ID: {db_user.id})")
            return db_user

        except Exception as e:
            db.rollback()
            logger.error(f"Error creando usuario: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al crear el usuario."
            )

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Union[User, bool]:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return False
        if not UserService.verify_password(password, user.hashed_password):
            return False
        return user

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        
        # Usamos settings.SECRET_KEY y settings.ALGORITHM
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt