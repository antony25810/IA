# shared/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional

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
    
    # ═══════════════════════════════════════════════════════════
    # EXTERNAL APIs
    # ═══════════════════════════════════════════════════════════
    
    # Google Places API
    # Obtener en: https://console.cloud.google.com/apis/credentials
    # Límites gratis: $200/mes crédito
    GOOGLE_PLACES_API_KEY: Optional[str] = None
    
    # Foursquare API
    # Obtener en: https://developer.foursquare.com/
    # Límites gratis: 200 requests/día
    FOURSQUARE_API_KEY: Optional[str] = None
    
    # OpenWeatherMap API
    # Obtener en: https://openweathermap.org/api
    # Límites gratis: 1000 requests/día
    OPENWEATHER_API_KEY: Optional[str] = None
    
    # ═══════════════════════════════════════════════════════════
    # DATABASE LIMITS (para rendimiento)
    # ═══════════════════════════════════════════════════════════
    MAX_ATTRACTIONS_PER_DESTINATION: int = 500
    MAX_REVIEWS_PER_ATTRACTION: int = 50
    MAX_CONNECTIONS_PER_ATTRACTION: int = 100
    
    # ═══════════════════════════════════════════════════════════
    # ML Neural Network Settings
    # ═══════════════════════════════════════════════════════════
    NN_LEARNING_RATE: float = 0.001
    NN_EPOCHS: int = 100
    NN_BATCH_SIZE: int = 32
    NN_HIDDEN_SIZE: int = 64
    NN_MODEL_SAVE_PATH: str = "./ml_models/attraction_scorer.pth"

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