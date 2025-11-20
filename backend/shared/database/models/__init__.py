# shared/database/models/__init__.py
"""
Modelos de base de datos para el sistema de turismo personalizado
"""
from .destination import Destination
from .attraction import Attraction
from .connection import AttractionConnection
from .user_profile import UserProfile
from .itinerary import Itinerary, ItineraryAttraction
from .review import Review, AttractionRating

__all__ = [
    "Destination",
    "Attraction",
    "AttractionConnection",
    "UserProfile",
    "Itinerary",
    "ItineraryAttraction",
    "Review",
    "AttractionRating"
]