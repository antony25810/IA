# backend/api_gateway/routes/health.py
from fastapi import Response as response
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from shared.database.base import get_db
from shared.config.settings import get_settings
import redis  # type: ignore

router = APIRouter()
settings = get_settings()

@router.get("/")
async def health_check():
    """Health check básico"""
    return {
        "status": "healthy",
        "service": "api_gateway",
        "version": settings.APP_VERSION
    }

@router.get("/db")
async def database_health(db: Session = Depends(get_db)):
    """Verificar conexión a PostgreSQL"""
    try:
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        
        # Verificar PostGIS
        postgis_version = db.execute(text("SELECT PostGIS_Version()")).fetchone()
        
        return {
            "status": "healthy",
            "database": "postgresql",
            "connection": "connected",
            "postgis_version": postgis_version[0] if postgis_version else "unknown"
        }
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE 
        return {
            "status": "unhealthy",
            "database": "postgresql",
            "connection": "disconnected",
            "error": str(e)
        }

@router.get("/redis")
async def redis_health():
    """Verificar conexión a Redis"""
    try:
        r = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2, 
            socket_timeout=2
        )
        r.ping()
        info = r.info()
        
        return {
            "status": "healthy",
            "cache": "redis",
            "connection": "connected",
            "version": info.get("redis_version", "unknown")
        }
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "cache": "redis",
            "connection": "disconnected",
            "error": str(e)
        }

@router.get("/full")
async def full_health_check(db: Session = Depends(get_db)):
    """Health check completo de todos los servicios"""
    
    services = {
        "api": {"status": "healthy"},
        "database": {},
        "cache": {}
    }
    
    # Verificar Database
    try:
        db.execute(text("SELECT 1"))
        services["database"] = {
            "status": "healthy",
            "connection": "connected"
        }
    except Exception as e:
        services["database"] = {
            "status": "unhealthy",
            "connection": "disconnected",
            "error": str(e)
        }
    
    # Verificar Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        services["cache"] = {
            "status": "healthy",
            "connection": "connected"
        }
    except Exception as e:
        services["cache"] = {
            "status": "unhealthy",
            "connection": "disconnected",
            "error": str(e)
        }
    
    # Determinar status general
    overall_status = "healthy"
    if any(s.get("status") == "unhealthy" for s in services.values()):
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "services": services,
        "version": settings.APP_VERSION
    }

    