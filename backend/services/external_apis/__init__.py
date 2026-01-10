# backend/services/external_apis/__init__.py
"""
Servicios de integración con APIs externas
"""
from .google_places import GooglePlacesService
from .foursquare import FoursquareService
from .weather import WeatherService
from .aggregator import DataAggregatorService

__all__ = [
    "GooglePlacesService",
    "FoursquareService", 
    "WeatherService",
    "DataAggregatorService"
]
