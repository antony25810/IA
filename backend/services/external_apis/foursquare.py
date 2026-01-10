# backend/services/external_apis/foursquare.py
"""
Servicio de integración con Foursquare Places API
"""
from typing import List, Dict, Optional, Any
from .base import BaseExternalAPI
from shared.utils.logger import setup_logger
from shared.config.settings import settings

logger = setup_logger(__name__)


class FoursquareService(BaseExternalAPI):
    """
    Cliente para Foursquare Places API v3
    Documentación: https://developer.foursquare.com/docs/places-api
    
    Uso principal: Datos de popularidad y check-ins
    """
    
    # Mapeo de categorías Foursquare a categorías internas
    CATEGORY_MAP = {
        "Arts and Entertainment": "entretenimiento",
        "Arts & Entertainment": "entretenimiento",
        "Museum": "cultural",
        "Landmark and Historical Building": "historico",
        "Park": "naturaleza",
        "Restaurant": "gastronomia",
        "Shopping": "compras",
        "Sports": "deportivo",
        "Nightlife": "entretenimiento",
        "Religious Site": "religioso",
        "Outdoors": "naturaleza",
        "Adventure": "aventura"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            api_key=api_key or settings.FOURSQUARE_API_KEY,
            base_url="https://api.foursquare.com/v3",
            calls_per_minute=30,
            calls_per_day=180,        # Conservador para plan gratuito
            cache_ttl_seconds=43200,  # 12 horas
            timeout_seconds=15
        )
        
        # Headers específicos de Foursquare
        self.client.headers.update({
            "Authorization": self.api_key,
            "Accept": "application/json"
        })
    
    async def search_places(
        self,
        query: str,
        lat: float,
        lon: float,
        radius_meters: int = 5000,
        categories: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Buscar lugares en Foursquare
        
        Args:
            query: Término de búsqueda
            lat: Latitud
            lon: Longitud
            radius_meters: Radio de búsqueda
            categories: IDs de categorías Foursquare
            limit: Máximo de resultados (max 50)
        """
        params = {
            "query": query,
            "ll": f"{lat},{lon}",
            "radius": min(radius_meters, 100000),
            "limit": min(limit, 50)
        }
        
        if categories:
            params["categories"] = ",".join(categories)
        
        try:
            data = await self._make_request(
                "GET",
                "places/search",
                params,
                cache_ttl=43200
            )
            
            results = data.get("results", [])
            logger.info(f"Foursquare: {len(results)} resultados para '{query}'")
            
            return [self._parse_place(place) for place in results]
            
        except Exception as e:
            logger.error(f"Error en búsqueda Foursquare: {str(e)}")
            return []
    
    async def get_place_details(self, fsq_id: str) -> Dict[str, Any]:
        """
        Obtener detalles de un lugar
        
        Args:
            fsq_id: ID de Foursquare
        """
        params = {
            "fields": "name,geocodes,location,categories,rating,stats,popularity,price,hours,photos,tips"
        }
        
        try:
            data = await self._make_request(
                "GET",
                f"places/{fsq_id}",
                params,
                cache_ttl=86400
            )
            
            return self._parse_place_details(data)
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles Foursquare: {str(e)}")
            return {}
    
    async def get_place_tips(self, fsq_id: str, limit: int = 10) -> List[Dict]:
        """
        Obtener tips (reviews cortas) de un lugar
        """
        params = {"limit": limit}
        
        try:
            data = await self._make_request(
                "GET",
                f"places/{fsq_id}/tips",
                params,
                cache_ttl=43200
            )
            
            return [
                {
                    "text": tip.get("text"),
                    "created_at": tip.get("created_at"),
                    "agree_count": tip.get("agree_count", 0)
                }
                for tip in data.get("results", [])
            ]
            
        except Exception as e:
            logger.error(f"Error obteniendo tips: {str(e)}")
            return []
    
    async def get_popularity_data(self, fsq_id: str) -> Dict[str, Any]:
        """
        Obtener datos de popularidad (muy útil para scoring)
        """
        details = await self.get_place_details(fsq_id)
        
        return {
            "popularity": details.get("popularity", 0),
            "total_checkins": details.get("stats", {}).get("total_checkins", 0),
            "total_visitors": details.get("stats", {}).get("total_visitors", 0),
            "rating": details.get("rating"),
            "price_tier": details.get("price_tier")
        }
    
    def _parse_place(self, place: Dict) -> Dict[str, Any]:
        """Convertir respuesta de Foursquare a formato interno"""
        geocodes = place.get("geocodes", {}).get("main", {})
        location = place.get("location", {})
        categories = place.get("categories", [])
        
        # Obtener categoría principal
        main_category = None
        if categories:
            cat_name = categories[0].get("name", "")
            main_category = self.CATEGORY_MAP.get(cat_name, "entretenimiento")
        
        return {
            "source": "foursquare",
            "source_id": place.get("fsq_id"),
            "name": place.get("name"),
            "address": location.get("formatted_address"),
            "lat": geocodes.get("latitude"),
            "lon": geocodes.get("longitude"),
            "category": main_category,
            "categories_raw": [c.get("name") for c in categories],
            "distance_meters": place.get("distance"),
            "chain_id": place.get("chains", [{}])[0].get("id") if place.get("chains") else None
        }
    
    def _parse_place_details(self, place: Dict) -> Dict[str, Any]:
        """Convertir detalles completos"""
        parsed = self._parse_place(place)
        
        stats = place.get("stats", {})
        
        parsed.update({
            "rating": place.get("rating"),
            "price_tier": place.get("price"),  # 1-4
            "popularity": place.get("popularity", 0),  # 0-1
            "total_checkins": stats.get("total_checkins", 0),
            "total_visitors": stats.get("total_visitors", 0),
            "total_photos": stats.get("total_photos", 0),
            "total_tips": stats.get("total_tips", 0),
            "hours": self._parse_hours(place.get("hours", {})),
            "photos": self._parse_photos(place.get("photos", []))
        })
        
        return parsed
    
    def _parse_hours(self, hours_data: Dict) -> Dict:
        """Parsear horarios"""
        if not hours_data:
            return {}
        
        day_map = {
            1: "lunes", 2: "martes", 3: "miercoles",
            4: "jueves", 5: "viernes", 6: "sabado", 7: "domingo"
        }
        
        parsed = {}
        for period in hours_data.get("regular", []):
            day = period.get("day")
            if day in day_map:
                parsed[day_map[day]] = {
                    "open": period.get("open"),
                    "close": period.get("close")
                }
        
        return parsed
    
    def _parse_photos(self, photos: List[Dict]) -> List[str]:
        """Obtener URLs de fotos"""
        urls = []
        for photo in photos[:5]:  # Máximo 5 fotos
            prefix = photo.get("prefix", "")
            suffix = photo.get("suffix", "")
            if prefix and suffix:
                urls.append(f"{prefix}original{suffix}")
        return urls
