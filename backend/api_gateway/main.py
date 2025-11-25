# backend/api_gateway/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config.settings import get_settings
from shared.utils.logger import setup_logger
from api_gateway.routes import health

from services.destinations import destination_router
from services.attractions import attraction_router
from services.connections import connection_router
from services.user_profile import user_profile_router
from services.search_service import search_router
from services.route_optimizer import router_optimizer_router
from services.rules_engine import rules_engine_router
from services.itinerary_generator import itinerary_router
from services.auth.router import  router as auth_router

from shared.database.base import engine, Base
from shared.database.models import User, UserProfile, Attraction, Itinerary, Destination, AttractionConnection, Review

# 2. ESTA LÍNEA CREA LAS TABLAS SI NO EXISTEN
# Se ejecuta cada vez que reinicias el backend. Si la tabla ya existe, no hace nada.
Base.metadata.create_all(bind=engine)

# Configuración
settings = get_settings()
logger = setup_logger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(
    health.router,
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

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📝 Modo: {settings.ENVIRONMENT}")
    logger.info(f"🔍 Debug: {settings.DEBUG}")

@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre de la aplicación"""
    logger.info(f"👋 Cerrando {settings.APP_NAME}")

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": f"Bienvenido a {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "disabled"
    }