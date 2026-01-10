# backend/services/external_apis/google_places.py
"""
Servicio de integración con Google Places API
"""
from typing import List, Dict, Optional, Any
from .base import BaseExternalAPI
from shared.utils.logger import setup_logger
from shared.config.settings import settings

logger = setup_logger(__name__)


class GooglePlacesService(BaseExternalAPI):
    """
    Cliente para Google Places API (New)
    Documentación: https://developers.google.com/maps/documentation/places/web-service
    
    Límites gratuitos (crédito $200/mes):
    - Place Search: ~$17/1000 requests
    - Place Details: ~$17/1000 requests
    - Photos: ~$7/1000 requests
    
    Estrategia: Usar caché agresivo (24h) para datos estáticos
    """
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            api_key=api_key or settings.GOOGLE_PLACES_API_KEY,
            base_url="https://maps.googleapis.com/maps/api/place",
            calls_per_minute=50,      # Conservador
            calls_per_day=500,        # ~$8.50/día máximo
            cache_ttl_seconds=86400,  # 24 horas (datos no cambian mucho)
            timeout_seconds=15
        )
    
    async def search_places(
        self, 
        query: str, 
        lat: float, 
        lon: float, 
        radius_meters: int = 5000,
        place_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Buscar lugares turísticos cerca de una ubicación
        
        Args:
            query: Término de búsqueda (ej: "museo", "restaurante")
            lat: Latitud del centro
            lon: Longitud del centro
            radius_meters: Radio de búsqueda en metros (max 50000)
            place_type: Tipo de lugar (tourist_attraction, museum, restaurant, etc.)
        
        Returns:
            Lista de lugares encontrados
        """
        params = {
            "query": query,
            "location": f"{lat},{lon}",
            "radius": min(radius_meters, 50000),
            "key": self.api_key,
            "language": "es"
        }
        
        if place_type:
            params["type"] = place_type
        
        try:
            data = await self._make_request(
                "GET", 
                "textsearch/json", 
                params,
                cache_ttl=86400  # 24 horas
            )
            
            results = data.get("results", [])
            logger.info(f"Google Places: {len(results)} resultados para '{query}'")
            
            return [self._parse_place(place) for place in results]
            
        except Exception as e:
            logger.error(f"Error en búsqueda Google Places: {str(e)}")
            return []
    
    async def search_nearby(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000,
        place_type: str = "tourist_attraction"
    ) -> List[Dict[str, Any]]:
        """
        Buscar lugares cercanos por tipo
        """
        params = {
            "location": f"{lat},{lon}",
            "radius": min(radius_meters, 50000),
            "type": place_type,
            "key": self.api_key,
            "language": "es"
        }
        
        try:
            data = await self._make_request(
                "GET",
                "nearbysearch/json",
                params,
                cache_ttl=86400
            )
            
            results = data.get("results", [])
            return [self._parse_place(place) for place in results]
            
        except Exception as e:
            logger.error(f"Error en nearby search: {str(e)}")
            return []
    
    async def get_place_details(
        self, 
        place_id: str,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Obtener detalles completos de un lugar
        
        Args:
            place_id: ID de Google Places
            fields: Campos específicos a solicitar (reduce costo)
        
        Returns:
            Diccionario con detalles del lugar
        """
        # Campos por defecto (balance costo/información)
        default_fields = [
            "name", "formatted_address", "geometry", "rating",
            "user_ratings_total", "price_level", "types",
            "opening_hours", "website", "formatted_phone_number",
            "reviews", "photos"
        ]
        
        params = {
            "place_id": place_id,
            "fields": ",".join(fields or default_fields),
            "key": self.api_key,
            "language": "es"
        }
        
        try:
            data = await self._make_request(
                "GET",
                "details/json",
                params,
                cache_ttl=604800  # 1 semana (detalles cambian poco)
            )
            
            result = data.get("result", {})
            return self._parse_place_details(result)
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles: {str(e)}")
            return {}
    
    async def get_place_reviews(self, place_id: str, max_reviews: int = 5) -> List[Dict]:
        """
        Obtener reviews de un lugar
        Google solo devuelve hasta 5 reviews por API
        """
        details = await self.get_place_details(place_id, fields=["reviews"])
        reviews = details.get("reviews", [])[:max_reviews]
        return reviews
    
    def _parse_place(self, place: Dict) -> Dict[str, Any]:
        """Convertir respuesta de Google Places a formato interno"""
        geometry = place.get("geometry", {})
        location = geometry.get("location", {})
        
        return {
            "source": "google_places",
            "source_id": place.get("place_id"),
            "name": place.get("name"),
            "address": place.get("formatted_address"),
            "lat": location.get("lat"),
            "lon": location.get("lng"),
            "rating": place.get("rating"),
            "total_reviews": place.get("user_ratings_total", 0),
            "price_level": place.get("price_level"),  # 0-4
            "types": place.get("types", []),
            "is_open": place.get("opening_hours", {}).get("open_now"),
            "photo_reference": self._get_photo_reference(place)
        }
    
    def _parse_place_details(self, place: Dict) -> Dict[str, Any]:
        """Convertir detalles de Google Places a formato interno"""
        parsed = self._parse_place(place)
        
        # Agregar campos adicionales de detalles
        parsed.update({
            "website": place.get("website"),
            "phone": place.get("formatted_phone_number"),
            "opening_hours": self._parse_opening_hours(place.get("opening_hours", {})),
            "reviews": self._parse_reviews(place.get("reviews", []))
        })
        
        return parsed
    
    def _parse_opening_hours(self, hours_data: Dict) -> Dict:
        """Parsear horarios de apertura"""
        if not hours_data:
            return {}
        
        weekday_text = hours_data.get("weekday_text", [])
        periods = hours_data.get("periods", [])
        
        # Mapear días en español
        day_map = {
            0: "domingo", 1: "lunes", 2: "martes", 3: "miercoles",
            4: "jueves", 5: "viernes", 6: "sabado"
        }
        
        parsed = {}
        for period in periods:
            open_info = period.get("open", {})
            close_info = period.get("close", {})
            day = open_info.get("day")
            
            if day is not None and day in day_map:
                day_name = day_map[day]
                parsed[day_name] = {
                    "open": open_info.get("time", "00:00"),
                    "close": close_info.get("time", "23:59") if close_info else "23:59"
                }
        
        return parsed
    
    def _parse_reviews(self, reviews: List[Dict]) -> List[Dict]:
        """Parsear reviews"""
        return [
            {
                "author": r.get("author_name"),
                "rating": r.get("rating"),
                "text": r.get("text"),
                "time": r.get("time"),
                "language": r.get("language", "es")
            }
            for r in reviews
        ]
    
    def _get_photo_reference(self, place: Dict) -> Optional[str]:
        """Obtener referencia de foto principal"""
        photos = place.get("photos", [])
        if photos:
            return photos[0].get("photo_reference")
        return None
    
    def get_photo_url(self, photo_reference: str, max_width: int = 400) -> str:
        """Generar URL de foto"""
        return (
            f"https://maps.googleapis.com/maps/api/place/photo"
            f"?maxwidth={max_width}"
            f"&photo_reference={photo_reference}"
            f"&key={self.api_key}"
        )
