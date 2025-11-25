from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache

class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # Application
    APP_NAME: str = "Turismo Personalizado API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database - Se cargan desde .env (requeridos en runtime)
    DATABASE_URL: str = ""
    DATABASE_URL_ASYNC: str = ""
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Security - Se carga desde .env (requerido en runtime)
    SECRET_KEY: str = "ContraseñaSuperSecretaPeroAsiBienSecreta"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8000"

    # ML
    ML_MODEL_PATH: str = "/app/ml_models"
    ML_BATCH_SIZE: int = 32
    
    # Logging
    LOG_LEVEL: str = "INFO"

    MAPBOX_API_KEY: Optional[str] = None
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        """Inicializa y valida configuración"""
        super().__init__(**kwargs)
        
        # Validar que las variables críticas NO estén vacías
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL must be set in .env file")
        if not self.DATABASE_URL_ASYNC:
            raise ValueError("DATABASE_URL_ASYNC must be set in .env file")
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in .env file")
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convierte ALLOWED_ORIGINS de string a lista"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]
        return self.ALLOWED_ORIGINS

@lru_cache()
def get_settings() -> Settings:
    """Singleton de configuración"""
    return Settings()