# backend/api_gateway/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config.settings import get_settings
from shared.utils.logger import setup_logger
from shared.database.base import engine, Base

import shared.database.models

from api_gateway.routes.health import router as health_router

from services.destinations import destination_router
from services.attractions import attraction_router
from services.connections import connection_router
from services.user_profile import user_profile_router
from services.search_service import search_router
from services.route_optimizer import router_optimizer_router
from services.rules_engine import rules_engine_router
from services.itinerary_generator import itinerary_router
from services.auth.router import  router as auth_router


# Configuración
settings = get_settings()
logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Contexto de ciclo de vida de la aplicación. 
    Maneja startup y shutdown events.
    """
    # ========== STARTUP ==========
    logger.info("=" * 60)
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)
    
    # Crear tablas en la base de datos
    try:
        logger.info("📊 Verificando tablas de base de datos...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tablas de base de datos verificadas correctamente")
    except Exception as e:
        logger.error(f"❌ Error al crear tablas en la base de datos: {e}")
        raise
    
    # Información del entorno
    logger.info(f"📝 Entorno: {settings.ENVIRONMENT}")
    logger.info(f"🔍 Debug mode: {settings.DEBUG}")
    logger.info(f"🌐 CORS Origins: {settings.CORS_ORIGINS}")
    logger.info(f"📚 Docs URL: {'/docs' if settings.DEBUG else 'Deshabilitado (producción)'}")
    logger.info("=" * 60)
    
    yield
    
    # ========== SHUTDOWN ==========
    logger. info("=" * 60)
    logger.info(f"👋 Cerrando {settings.APP_NAME}")
    logger.info("🛑 Limpiando recursos...")
    
    # Cerrar conexiones de base de datos
    try:
        engine.dispose()
        logger.info("✅ Conexiones de base de datos cerradas correctamente")
    except Exception as e:
        logger.error(f"❌ Error al cerrar conexiones: {e}")
    
    logger.info("=" * 60)


# Crear instancia de FastAPI
app = FastAPI(
    title=settings. APP_NAME,
    version=settings.APP_VERSION,
    description="API Gateway para TripWise - Sistema de planificación de viajes inteligente",
    debug=settings.DEBUG,
    docs_url="/docs" if settings. DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)


# ========== CONFIGURACIÓN DE CORS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== REGISTRO DE ROUTERS ==========

# Health checks (siempre disponible)
app.include_router(
    health_router,
    prefix="/health",
    tags=["Health"]
)

app.include_router(
    health_router,
    prefix="/api/health",
    tags=["Health Check"]
)

app.include_router(
    destination_router,
    prefix="/api",
    tags=["Destinations"]
)

app.include_router(
    attraction_router,
    prefix="/api",
    tags=["Attractions"]
)

app.include_router(
    connection_router,
    prefix="/api",
    tags=["Connections"]
)

app.include_router(
    user_profile_router,
    prefix="/api",
    tags=["User Profiles"]
)

app.include_router(
    search_router,
    prefix="/api",
    tags=["Search & Exploration (BFS)"]
)

app.include_router(
    router_optimizer_router,
    prefix="/api",
    tags=["Route Optimization (A*)"]
)

app.include_router(
    rules_engine_router,
    prefix="/api",
    tags=["Rules Engine (Forward Chaining)"]
)

app.include_router(
    itinerary_router,
    prefix="/api",
    tags=["Itinerary Generator"]
)

app.include_router(
    auth_router,
    prefix="/api",
    tags=["Authentication & Users"]
)


@app.get("/", tags=["Root"])
async def root():
    """
    Endpoint raíz de la API. 
    Retorna información básica de la aplicación.
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings. ENVIRONMENT,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "Disabled",
        "health": "/health"
    }


# ========== MANEJO DE ERRORES GLOBAL ==========

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Manejador personalizado para errores HTTP"""
    logger.error(f"HTTP Error {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc. detail,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejador personalizado para errores de validación"""
    logger.error(f"Validation Error - Path: {request.url.path} - Errors: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "status_code": 422,
            "message": "Error de validación en los datos enviados",
            "details": exc.errors(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejador personalizado para errores generales"""
    logger. exception(f"Unhandled Exception - Path: {request.url.path}")
    
    # En producción, no mostrar detalles del error
    if settings.ENVIRONMENT == "production":
        message = "Ha ocurrido un error interno. Por favor, contacte al administrador."
    else:
        message = str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": 500,
            "message": message,
            "path": str(request.url.path)
        }
    )

# ========== RUTAS BÁSICAS ==========

@app.get("/info", tags=["Root"])
async def info():
    """
    Información detallada de la aplicación. 
    """
    return {
        "application": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "description": "Sistema de planificación de viajes inteligente",
        },
        "environment": {
            "mode": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
        },
        "endpoints": {
            "documentation": "/docs" if settings.DEBUG else None,
            "health_checks": "/health",
            "api": "/api/v1"
        },
        "features": [
            "Búsqueda inteligente de destinos",
            "Optimización de rutas",
            "Generación de itinerarios personalizados",
            "Motor de reglas de negocio",
            "Sistema de recomendaciones"
        ]
    }


# ========== PUNTO DE ENTRADA ==========

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )