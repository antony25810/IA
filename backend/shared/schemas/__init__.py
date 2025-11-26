# backend/shared/schemas/__init__.py
"""
Schemas de Pydantic para validación y serialización de datos
"""
from .base import (
    TimestampMixin,
    ResponseBase,
    PaginationParams,
    PaginatedResponse,
    MessageResponse
)

from .destination import (
    DestinationBase,
    DestinationCreate,
    DestinationUpdate,
    DestinationRead,
    DestinationWithStats
)

from .attraction import (
    AttractionBase,
    AttractionCreate,
    AttractionUpdate,
    AttractionRead,
    AttractionWithDestination,
    AttractionWithDistance,
    AttractionSearchParams,
    AttractionNearbyParams,
    AttractionListResponse
)

from .connection import (
    ConnectionBase,
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionRead,
    ConnectionWithAttractions,
    ConnectionSearchParams
)

from .user_profile import (
    UserProfileBase,
    PreferencesSchema,
    MobilityConstraintsSchema,
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileRead,
    UserProfileWithStats
)

from .itinerary import (
    AttractionInDay,
    RouteSegment,
    DaySummary,
    DayData,
    ItineraryDayBase,
    ItineraryDayCreate,
    ItineraryDayRead,
    ItineraryDayUpdate,
    ItineraryBase,
    ItineraryCreate,
    ItineraryUpdate,
    ItineraryRead,
    ItineraryWithDays,
    ItineraryWithDetails,
    ItineraryGenerationRequest,
    ItineraryGenerationResponse,
)

from .review import (
    ReviewBase,
    ReviewCreate,
    ReviewRead,
    AttractionRatingBase,
    AttractionRatingCreate,
    AttractionRatingRead
)

# Resolver forward references (importante para Pydantic v2)
from pydantic import TypeAdapter

# Esto fuerza la resolución de las forward references
AttractionWithDestination.model_rebuild()
ConnectionWithAttractions.model_rebuild()
ItineraryWithDetails.model_rebuild()

__all__ = [
    # Base
    "TimestampMixin",
    "ResponseBase",
    "PaginationParams",
    "PaginatedResponse",
    "MessageResponse",
    
    # Destination
    "DestinationBase",
    "DestinationCreate",
    "DestinationUpdate",
    "DestinationRead",
    "DestinationWithStats",
    
    # Attraction
    "AttractionBase",
    "AttractionCreate",
    "AttractionUpdate",
    "AttractionRead",
    "AttractionWithDestination",
    "AttractionWithDistance",
    "AttractionSearchParams",
    "AttractionNearbyParams",
    "AttractionListResponse",
    
    # Connection
    "ConnectionBase",
    "ConnectionCreate",
    "ConnectionUpdate",
    "ConnectionRead",
    "ConnectionWithAttractions",
    "ConnectionSearchParams",
    
    # UserProfile
    "UserProfileBase",
    "PreferencesSchema",
    "MobilityConstraintsSchema",
    "UserProfileCreate",
    "UserProfileUpdate",
    "UserProfileRead",
    "UserProfileWithStats",
    
    # Itinerary
    "ItineraryBase",
    "ItineraryCreate",
    "ItineraryUpdate",
    "ItineraryRead",
    "ItineraryWithDetails",
    "ItineraryWithDays",
    "ItineraryDayBase",
    "ItineraryDayCreate",
    "ItineraryDayRead",
    "ItineraryDayUpdate",
    "AttractionInDay",
    "RouteSegment",
    "DaySummary",
    "DayData",
    "ItineraryGenerationRequest",
    "ItineraryGenerationResponse",
    
    # Review & Rating
    "ReviewBase",
    "ReviewCreate",
    "ReviewRead",
    "AttractionRatingBase",
    "AttractionRatingCreate",
    "AttractionRatingRead",
]