# backend/services/user_profiles/__init__.py
"""
Módulo de servicios para gestión de perfiles de usuario
"""
from .service import UserProfileService
from .router import router as user_profile_router

__all__ = ["UserProfileService", "user_profile_router"]