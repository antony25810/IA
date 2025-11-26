# shared/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Turismo Personalizado API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str  # SIN valor por defecto
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # ML
    ML_MODEL_PATH: str = "/app/ml_models"
    ML_BATCH_SIZE: int = 32

    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Validar que SECRET_KEY exista y sea seguro
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set in .env file")
        
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        
        if self.SECRET_KEY in ["secret", "changeme"]:
            raise ValueError("SECRET_KEY must not be a default/example value")

@lru_cache()
def get_settings() -> Settings:
    return Settings()