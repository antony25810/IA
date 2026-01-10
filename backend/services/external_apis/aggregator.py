# backend/services/external_apis/aggregator.py
"""
Servicio agregador de múltiples APIs externas
Combina datos de Google Places, Foursquare y Weather
"""
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement  # type: ignore

from shared.database.models import Attraction, Review, Destination
from shared.utils.logger import setup_logger
from shared.config.settings import settings

from .google_places import GooglePlacesService
from .foursquare import FoursquareService
from .weather import WeatherService

logger = setup_logger(__name__)


class DataAggregatorService:
    """
    Servicio que agrega datos de múltiples APIs
    
    Estrategia de fusión:
    1. Google Places: Datos base (nombre, ubicación, rating principal)
    2. Foursquare: Datos de popularidad y check-ins
    3. Weather: Contexto temporal
    
    Límites de BD recomendados:
    - Max 500 atracciones por destino (evitar lentitud)
    - Max 50 reviews por atracción (suficiente para ML)
    - Purgar datos > 1 año sin actualizar
    """
    
    # Límites para evitar base de datos lenta
    MAX_ATTRACTIONS_PER_DESTINATION = 500
    MAX_REVIEWS_PER_ATTRACTION = 50
    MAX_CONNECTIONS_PER_ATTRACTION = 100
    DATA_STALENESS_DAYS = 365  # Datos a purgar después de 1 año
    
    def __init__(self, db: Session):
        self.db = db
        
        # Inicializar servicios solo si hay API keys
        self.google_service = None
        self.foursquare_service = None
        self.weather_service = None
        
        if settings.GOOGLE_PLACES_API_KEY:
            self.google_service = GooglePlacesService()
        else:
            logger.warning("Google Places API key no configurada")
        
        if settings.FOURSQUARE_API_KEY:
            self.foursquare_service = FoursquareService()
        else:
            logger.warning("Foursquare API key no configurada")
        
        if settings.OPENWEATHER_API_KEY:
            self.weather_service = WeatherService()
        else:
            logger.warning("OpenWeather API key no configurada")
    
    async def enrich_destination(
        self,
        destination_id: int,
        search_radius_km: float = 10.0,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """
        Enriquecer un destino con datos de APIs externas
        
        Args:
            destination_id: ID del destino
            search_radius_km: Radio de búsqueda
            max_results: Máximo de atracciones a agregar
        
        Returns:
            Resumen de operaciones realizadas
        """
        # Obtener destino
        destination = self.db.query(Destination).filter(
            Destination.id == destination_id
        ).first()
        
        if not destination:
            raise ValueError(f"Destino {destination_id} no encontrado")
        
        # Obtener coordenadas del destino
        lat, lon = self._get_destination_coords(destination)
        
        logger.info(f"Enriqueciendo destino {destination.name} ({lat}, {lon})")
        
        # Verificar límites actuales
        current_count = self.db.query(Attraction).filter(
            Attraction.destination_id == destination_id
        ).count()
        
        if current_count >= self.MAX_ATTRACTIONS_PER_DESTINATION:
            logger.warning(f"Destino {destination_id} ya tiene {current_count} atracciones (máx: {self.MAX_ATTRACTIONS_PER_DESTINATION})")
            return {
                "status": "limit_reached",
                "current_attractions": current_count,
                "max_allowed": self.MAX_ATTRACTIONS_PER_DESTINATION
            }
        
        results = {
            "destination_id": destination_id,
            "destination_name": destination.name,
            "google_places": 0,
            "foursquare": 0,
            "new_attractions": 0,
            "updated_attractions": 0,
            "new_reviews": 0,
            "errors": []
        }
        
        # Búsqueda paralela en APIs
        tasks = []
        
        if self.google_service:
            tasks.append(self._fetch_google_places(lat, lon, search_radius_km * 1000))
        
        if self.foursquare_service:
            tasks.append(self._fetch_foursquare_places(lat, lon, search_radius_km * 1000))
        
        if tasks:
            api_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(api_results):
                if isinstance(result, Exception):
                    results["errors"].append(str(result))
                    continue
                
                if i == 0 and self.google_service:  # Google
                    results["google_places"] = len(result)
                    await self._process_places(
                        result, destination_id, "google_places", results
                    )
                elif self.foursquare_service:  # Foursquare
                    results["foursquare"] = len(result)
                    await self._process_places(
                        result, destination_id, "foursquare", results
                    )
        
        return results
    
    async def _fetch_google_places(
        self,
        lat: float,
        lon: float,
        radius_meters: float
    ) -> List[Dict]:
        """Obtener lugares de Google Places"""
        all_places = []
        
        # Buscar por categorías turísticas
        search_queries = [
            ("tourist_attraction", "atracciones turísticas"),
            ("museum", "museo"),
            ("park", "parque"),
            ("restaurant", "restaurante popular"),
            ("church", "iglesia histórica")
        ]
        
        for place_type, query in search_queries:
            try:
                places = await self.google_service.search_places(
                    query=query,
                    lat=lat,
                    lon=lon,
                    radius_meters=int(radius_meters),
                    place_type=place_type
                )
                all_places.extend(places)
            except Exception as e:
                logger.error(f"Error buscando '{query}': {str(e)}")
        
        # Eliminar duplicados por source_id
        unique_places = {p["source_id"]: p for p in all_places if p.get("source_id")}
        return list(unique_places.values())
    
    async def _fetch_foursquare_places(
        self,
        lat: float,
        lon: float,
        radius_meters: float
    ) -> List[Dict]:
        """Obtener lugares de Foursquare"""
        try:
            return await self.foursquare_service.search_places(
                query="attractions",
                lat=lat,
                lon=lon,
                radius_meters=int(radius_meters),
                limit=50
            )
        except Exception as e:
            logger.error(f"Error en Foursquare: {str(e)}")
            return []
    
    async def _process_places(
        self,
        places: List[Dict],
        destination_id: int,
        source: str,
        results: Dict
    ) -> None:
        """
        Procesar lugares y guardar/actualizar en BD
        """
        for place_data in places:
            try:
                # Verificar límite
                current_count = self.db.query(Attraction).filter(
                    Attraction.destination_id == destination_id
                ).count()
                
                if current_count >= self.MAX_ATTRACTIONS_PER_DESTINATION:
                    logger.info("Límite de atracciones alcanzado")
                    break
                
                # Buscar si ya existe (por nombre similar o source_id)
                existing = self._find_existing_attraction(
                    destination_id, 
                    place_data.get("name"),
                    source,
                    place_data.get("source_id")
                )
                
                if existing:
                    # Actualizar datos existentes
                    self._update_attraction(existing, place_data, source)
                    results["updated_attractions"] += 1
                else:
                    # Crear nueva atracción
                    self._create_attraction(destination_id, place_data, source)
                    results["new_attractions"] += 1
                
                self.db.commit()
                
            except Exception as e:
                logger.error(f"Error procesando lugar '{place_data.get('name')}': {str(e)}")
                self.db.rollback()
    
    def _find_existing_attraction(
        self,
        destination_id: int,
        name: str,
        source: str,
        source_id: str
    ) -> Optional[Attraction]:
        """Buscar atracción existente por nombre o source_id"""
        # Primero buscar por source_id exacto
        if source_id:
            existing = self.db.query(Attraction).filter(
                Attraction.destination_id == destination_id,
                Attraction.data_source == source,
                Attraction.extra_data["source_id"].astext == source_id
            ).first()
            
            if existing:
                return existing
        
        # Buscar por nombre similar
        if name:
            existing = self.db.query(Attraction).filter(
                Attraction.destination_id == destination_id,
                Attraction.name.ilike(f"%{name[:50]}%")
            ).first()
            
            if existing:
                return existing
        
        return None
    
    def _create_attraction(
        self,
        destination_id: int,
        place_data: Dict,
        source: str
    ) -> Attraction:
        """Crear nueva atracción desde datos de API"""
        lat = place_data.get("lat")
        lon = place_data.get("lon")
        
        if not lat or not lon:
            raise ValueError("Coordenadas inválidas")
        
        # Mapear categoría
        category = self._map_category(place_data)
        price_range = self._map_price_range(place_data)
        
        attraction = Attraction(
            destination_id=destination_id,
            name=place_data.get("name", "Sin nombre")[:255],
            description=place_data.get("description", "")[:1000] if place_data.get("description") else None,
            category=category,
            subcategory=place_data.get("subcategory"),
            location=WKTElement(f"POINT({lon} {lat})", srid=4326),
            address=place_data.get("address", "")[:500] if place_data.get("address") else None,
            rating=place_data.get("rating"),
            total_reviews=place_data.get("total_reviews", 0),
            price_range=price_range,
            opening_hours=place_data.get("opening_hours"),
            data_source=source,
            verified=False,
            extra_data={
                "source_id": place_data.get("source_id"),
                "types": place_data.get("types", []),
                "popularity": place_data.get("popularity"),
                "total_checkins": place_data.get("total_checkins"),
                "photos": place_data.get("photos", [])[:5],  # Máximo 5 fotos
                "last_api_update": datetime.now().isoformat()
            }
        )
        
        self.db.add(attraction)
        return attraction
    
    def _update_attraction(
        self,
        attraction: Attraction,
        place_data: Dict,
        source: str
    ) -> None:
        """Actualizar atracción existente con nuevos datos"""
        # Solo actualizar si hay datos nuevos/mejores
        if place_data.get("rating") and (not attraction.rating or place_data["rating"] > attraction.rating):
            attraction.rating = place_data["rating"]
        
        if place_data.get("total_reviews", 0) > (attraction.total_reviews or 0):
            attraction.total_reviews = place_data["total_reviews"]
        
        # Actualizar metadata
        extra_data = attraction.extra_data or {}
        extra_data[f"{source}_data"] = {
            "source_id": place_data.get("source_id"),
            "rating": place_data.get("rating"),
            "popularity": place_data.get("popularity"),
            "total_checkins": place_data.get("total_checkins"),
            "last_update": datetime.now().isoformat()
        }
        attraction.extra_data = extra_data
    
    def _map_category(self, place_data: Dict) -> str:
        """Mapear categoría de API a categoría interna"""
        types = place_data.get("types", [])
        category = place_data.get("category")
        
        if category:
            return category
        
        # Mapeo de tipos de Google Places
        type_map = {
            "museum": "cultural",
            "art_gallery": "cultural",
            "church": "religioso",
            "hindu_temple": "religioso",
            "mosque": "religioso",
            "synagogue": "religioso",
            "park": "naturaleza",
            "zoo": "naturaleza",
            "aquarium": "naturaleza",
            "restaurant": "gastronomia",
            "cafe": "gastronomia",
            "bar": "entretenimiento",
            "night_club": "entretenimiento",
            "amusement_park": "aventura",
            "stadium": "deportivo",
            "shopping_mall": "compras",
            "tourist_attraction": "cultural",
            "point_of_interest": "cultural"
        }
        
        for t in types:
            if t in type_map:
                return type_map[t]
        
        return "entretenimiento"  # Default
    
    def _map_price_range(self, place_data: Dict) -> str:
        """Mapear nivel de precio"""
        price_level = place_data.get("price_level") or place_data.get("price_tier")
        
        if price_level is None:
            return "medio"
        
        if price_level <= 1:
            return "bajo"
        elif price_level == 2:
            return "medio"
        elif price_level >= 3:
            return "alto"
        
        return "medio"
    
    def _get_destination_coords(self, destination: Destination) -> Tuple[float, float]:
        """Obtener coordenadas del destino"""
        from geoalchemy2.shape import to_shape
        
        if destination.location:
            point = to_shape(destination.location)
            return point.y, point.x  # lat, lon
        
        raise ValueError(f"Destino {destination.id} sin ubicación")
    
    async def get_weather_context(
        self,
        destination_id: int
    ) -> Dict[str, Any]:
        """
        Obtener contexto de clima para el motor de reglas
        """
        if not self.weather_service:
            return {"weather": {"condition": "sunny", "temperature": 25, "is_default": True}}
        
        destination = self.db.query(Destination).filter(
            Destination.id == destination_id
        ).first()
        
        if not destination:
            return {"weather": {"condition": "sunny", "temperature": 25, "is_default": True}}
        
        lat, lon = self._get_destination_coords(destination)
        return await self.weather_service.get_weather_context_for_rules(lat, lon)
    
    async def enrich_attraction_with_reviews(
        self,
        attraction_id: int
    ) -> Dict[str, Any]:

        attraction = self.db.query(Attraction).filter(
            Attraction.id == attraction_id
        ).first()
        
        if not attraction:
            raise ValueError(f"Atracción {attraction_id} no encontrada")
        
        results = {"new_reviews": 0, "sources": []}
        
        # Obtener source_id de Google si existe
        extra_data = attraction.extra_data or {}
        google_id = extra_data.get("source_id")
        
        if google_id and self.google_service:
            try:
                reviews = await self.google_service.get_place_reviews(google_id)
                for review in reviews:
                    self._save_review(attraction_id, review, "google_places")
                    results["new_reviews"] += 1
                results["sources"].append("google_places")
            except Exception as e:
                logger.error(f"Error obteniendo reviews de Google: {str(e)}")
        
        # Obtener source_id de Foursquare si existe
        fsq_id = extra_data.get("foursquare_data", {}).get("source_id")
        
        if fsq_id and self.foursquare_service:
            try:
                tips = await self.foursquare_service.get_place_tips(fsq_id)
                for tip in tips:
                    self._save_review(attraction_id, tip, "foursquare")
                    results["new_reviews"] += 1
                results["sources"].append("foursquare")
            except Exception as e:
                logger.error(f"Error obteniendo tips de Foursquare: {str(e)}")
        
        self.db.commit()
        return results
    
    def _save_review(
        self,
        attraction_id: int,
        review_data: Dict,
        source: str
    ) -> None:
        """Guardar review en BD (con límite)"""
        # Verificar límite de reviews
        current_count = self.db.query(Review).filter(
            Review.attraction_id == attraction_id
        ).count()
        
        if current_count >= self.MAX_REVIEWS_PER_ATTRACTION:
            return
        
        text = review_data.get("text", "")
        if not text:
            return
        
        review = Review(
            attraction_id=attraction_id,
            source=source,
            text=text[:2000],  # Limitar longitud
            rating=review_data.get("rating"),
            author=review_data.get("author", "Anónimo")[:255],
            language=review_data.get("language", "es")
        )
        
        self.db.add(review)
    
    async def close(self):
        """Cerrar conexiones de APIs"""
        tasks = []
        if self.google_service:
            tasks.append(self.google_service.close())
        if self.foursquare_service:
            tasks.append(self.foursquare_service.close())
        if self.weather_service:
            tasks.append(self.weather_service.close())
        
        if tasks:
            await asyncio.gather(*tasks)
