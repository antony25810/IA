# backend/scripts/seed_data.py
"""
═══════════════════════════════════════════════════════════════════════════════
                    SEED AUTOMÁTICO CON APIs EXTERNAS
═══════════════════════════════════════════════════════════════════════════════

Este script puebla la base de datos automáticamente usando:
- Google Places API: Busca atracciones reales por ubicación
- Foursquare API: Enriquece con popularidad y tips
- Genera conexiones automáticas entre atracciones

Uso:
    python scripts/seed_data.py                    # Seed por defecto (CDMX)
    python scripts/seed_data.py "Lima, Perú"       # Seed de Lima
    python scripts/seed_data.py "Paris, France" 50 # Paris con 50 atracciones

═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import os
import httpx
from math import radians, cos, sin, asin, sqrt
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Agregar directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement
from shared.database.base import SessionLocal, engine, Base
from shared.database.models import Destination, Attraction, AttractionConnection, User, UserProfile
from shared.security import get_password_hash
from shared.config.settings import get_settings

settings = get_settings()

# ═══════════════════════════════════════════════════════════════════════════════
#                           CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

# Mapeo de tipos de Google Places a categorías del sistema
GOOGLE_TYPE_TO_CATEGORY = {
    # Cultural
    "museum": "cultural",
    "art_gallery": "cultural",
    "library": "cultural",
    
    # Histórico
    "church": "historico",
    "hindu_temple": "religioso",
    "mosque": "religioso",
    "synagogue": "religioso",
    "place_of_worship": "religioso",
    "city_hall": "historico",
    "landmark": "historico",
    "tourist_attraction": "historico",
    
    # Naturaleza
    "park": "naturaleza",
    "zoo": "naturaleza",
    "aquarium": "naturaleza",
    "botanical_garden": "naturaleza",
    "campground": "naturaleza",
    
    # Entretenimiento
    "amusement_park": "entretenimiento",
    "movie_theater": "entretenimiento",
    "night_club": "entretenimiento",
    "casino": "entretenimiento",
    "bowling_alley": "entretenimiento",
    "stadium": "deportivo",
    "gym": "deportivo",
    
    # Gastronomía
    "restaurant": "gastronomia",
    "cafe": "gastronomia",
    "bar": "gastronomia",
    "bakery": "gastronomia",
    "food": "gastronomia",
    
    # Compras
    "shopping_mall": "compras",
    "store": "compras",
    "market": "compras",
    
    # Aventura
    "rv_park": "aventura",
    "travel_agency": "aventura",
}

# Tipos de lugares a buscar en Google Places
PLACE_TYPES_TO_SEARCH = [
    "tourist_attraction",
    "museum",
    "park",
    "art_gallery",
    "church",
    "amusement_park",
    "zoo",
    "aquarium",
    "stadium",
    "landmark",
]


# ═══════════════════════════════════════════════════════════════════════════════
#                         CLIENTE DE GOOGLE PLACES (NEW API)
# ═══════════════════════════════════════════════════════════════════════════════

class GooglePlacesClient:
    """Cliente para Google Places API (New) - 2024+"""
    
    BASE_URL = "https://places.googleapis.com/v1"
    GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)
    
    def geocode_location(self, location_name: str) -> Optional[Tuple[float, float]]:
        """Convierte nombre de lugar a coordenadas usando Places API (New) - Text Search"""
        url = f"{self.BASE_URL}/places:searchText"
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.location,places.displayName"
        }
        
        body = {
            "textQuery": location_name,
            "maxResultCount": 1
        }
        
        try:
            response = self.client.post(url, json=body, headers=headers)
            data = response.json()
            
            if "places" in data and len(data["places"]) > 0:
                loc = data["places"][0].get("location", {})
                lat = loc.get("latitude")
                lng = loc.get("longitude")
                if lat and lng:
                    print(f"   ✅ Encontrado: {data['places'][0].get('displayName', {}).get('text', location_name)}")
                    return lat, lng
            
            print(f"   ⚠️ No se encontró ubicación para '{location_name}'")
            if "error" in data:
                print(f"   ❌ Error: {data['error'].get('message', 'Unknown')}")
                
        except Exception as e:
            print(f"   ❌ Error en geocoding: {e}")
        
        return None
    
    def search_nearby(
        self, 
        lat: float, 
        lng: float, 
        radius: int = 10000,
        place_type: str = "tourist_attraction"
    ) -> List[Dict]:
        """
        Busca lugares cercanos usando Places API (New) - searchNearby
        """
        url = f"{self.BASE_URL}/places:searchNearby"
        
        # Mapeo de tipos legacy a tipos de la nueva API
        type_mapping = {
            "tourist_attraction": "tourist_attraction",
            "museum": "museum",
            "park": "park",
            "art_gallery": "art_gallery",
            "church": "church",
            "amusement_park": "amusement_park",
            "zoo": "zoo",
            "aquarium": "aquarium",
            "stadium": "stadium",
            "landmark": "historical_landmark",
        }
        
        mapped_type = type_mapping.get(place_type, place_type)
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.priceLevel,places.types,places.regularOpeningHours,places.photos,places.websiteUri,places.primaryTypeDisplayName"
        }
        
        body = {
            "includedTypes": [mapped_type],
            "maxResultCount": 20,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": lat,
                        "longitude": lng
                    },
                    "radius": float(radius)
                }
            }
        }
        
        try:
            response = self.client.post(url, json=body, headers=headers)
            data = response.json()
            
            if "places" in data:
                # Convertir formato de nueva API a formato compatible con legacy
                return self._convert_to_legacy_format(data["places"])
            return []
        except Exception as e:
            print(f"      ⚠️ Error en búsqueda: {e}")
            return []
    
    def _convert_to_legacy_format(self, places: List[Dict]) -> List[Dict]:
        """Convierte respuesta de nueva API a formato legacy para compatibilidad"""
        converted = []
        for place in places:
            legacy_place = {
                "place_id": place.get("id", ""),
                "name": place.get("displayName", {}).get("text", "Sin nombre"),
                "formatted_address": place.get("formattedAddress", ""),
                "geometry": {
                    "location": {
                        "lat": place.get("location", {}).get("latitude", 0),
                        "lng": place.get("location", {}).get("longitude", 0)
                    }
                },
                "rating": place.get("rating", 0),
                "user_ratings_total": place.get("userRatingCount", 0),
                "price_level": self._convert_price_level(place.get("priceLevel")),
                "types": place.get("types", []),
                "photos": place.get("photos", []),
            }
            converted.append(legacy_place)
        return converted
    
    def _convert_price_level(self, price_level: Optional[str]) -> int:
        """Convierte precio de nueva API a formato numérico"""
        if not price_level:
            return 2  # Moderado por defecto
        mapping = {
            "PRICE_LEVEL_FREE": 0,
            "PRICE_LEVEL_INEXPENSIVE": 1,
            "PRICE_LEVEL_MODERATE": 2,
            "PRICE_LEVEL_EXPENSIVE": 3,
            "PRICE_LEVEL_VERY_EXPENSIVE": 4,
        }
        return mapping.get(price_level, 2)
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """Obtiene detalles completos usando Places API (New)"""
        url = f"{self.BASE_URL}/places/{place_id}"
        
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "id,displayName,formattedAddress,location,rating,userRatingCount,priceLevel,types,regularOpeningHours,photos,reviews,websiteUri,nationalPhoneNumber,primaryTypeDisplayName,editorialSummary"
        }
        
        try:
            response = self.client.get(url, headers=headers)
            data = response.json()
            
            if "id" in data:
                # Convertir a formato legacy
                return {
                    "place_id": data.get("id", ""),
                    "name": data.get("displayName", {}).get("text", ""),
                    "formatted_address": data.get("formattedAddress", ""),
                    "geometry": {
                        "location": {
                            "lat": data.get("location", {}).get("latitude", 0),
                            "lng": data.get("location", {}).get("longitude", 0)
                        }
                    },
                    "rating": data.get("rating", 0),
                    "user_ratings_total": data.get("userRatingCount", 0),
                    "price_level": self._convert_price_level(data.get("priceLevel")),
                    "types": data.get("types", []),
                    "opening_hours": self._convert_opening_hours(data.get("regularOpeningHours")),
                    "photos": data.get("photos", []),
                    "reviews": self._convert_reviews(data.get("reviews", [])),
                    "website": data.get("websiteUri", ""),
                    "formatted_phone_number": data.get("nationalPhoneNumber", ""),
                    "editorial_summary": data.get("editorialSummary", {}).get("text", ""),
                }
            return None
        except Exception as e:
            print(f"      ⚠️ Error obteniendo detalles: {e}")
            return None
    
    def _convert_opening_hours(self, hours: Optional[Dict]) -> Optional[Dict]:
        """Convierte horarios a formato legacy"""
        if not hours:
            return None
        return {
            "open_now": True,  # Nueva API no lo incluye directamente
            "weekday_text": hours.get("weekdayDescriptions", [])
        }
    
    def _convert_reviews(self, reviews: List[Dict]) -> List[Dict]:
        """Convierte reseñas a formato legacy"""
        converted = []
        for review in reviews[:5]:  # Max 5 reseñas
            converted.append({
                "author_name": review.get("authorAttribution", {}).get("displayName", "Anónimo"),
                "rating": review.get("rating", 0),
                "text": review.get("text", {}).get("text", ""),
                "time": 0,  # Nueva API usa formato diferente
            })
        return converted
    
    def close(self):
        self.client.close()


# ═══════════════════════════════════════════════════════════════════════════════
#                         CLIENTE DE FOURSQUARE
# ═══════════════════════════════════════════════════════════════════════════════

class FoursquareClient:
    """Cliente para Foursquare Places API v3"""
    
    BASE_URL = "https://api.foursquare.com/v3/places"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(
            timeout=30.0,
            headers={"Authorization": api_key}
        )
    
    def search_nearby(
        self,
        lat: float,
        lng: float,
        radius: int = 10000,
        categories: str = "16000"  # Landmarks and Outdoors
    ) -> List[Dict]:
        """Busca lugares cercanos"""
        url = f"{self.BASE_URL}/search"
        params = {
            "ll": f"{lat},{lng}",
            "radius": radius,
            "categories": categories,
            "limit": 50
        }
        
        try:
            response = self.client.get(url, params=params)
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            print(f"⚠️ Error Foursquare: {e}")
            return []
    
    def get_place_details(self, fsq_id: str) -> Optional[Dict]:
        """Obtiene detalles de un lugar"""
        url = f"{self.BASE_URL}/{fsq_id}"
        params = {
            "fields": "name,rating,popularity,stats,price,hours,tips"
        }
        
        try:
            response = self.client.get(url, params=params)
            return response.json()
        except:
            return None
    
    def close(self):
        self.client.close()


# ═══════════════════════════════════════════════════════════════════════════════
#                           FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calcula distancia en metros entre dos puntos"""
    R = 6371000
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c


def map_google_type_to_category(types: List[str]) -> str:
    """Convierte tipos de Google a categoría del sistema"""
    for t in types:
        if t in GOOGLE_TYPE_TO_CATEGORY:
            return GOOGLE_TYPE_TO_CATEGORY[t]
    return "otro"


def map_price_level(price_level: Optional[int]) -> str:
    """Convierte price_level de Google a nuestro formato"""
    if price_level is None:
        return "medio"
    mapping = {0: "gratis", 1: "bajo", 2: "medio", 3: "alto", 4: "alto"}
    return mapping.get(price_level, "medio")


def estimate_visit_duration(types: List[str], category: str) -> int:
    """Estima duración de visita en minutos"""
    if "museum" in types:
        return 120
    if "amusement_park" in types:
        return 240
    if "zoo" in types or "aquarium" in types:
        return 180
    if "park" in types:
        return 60
    if "restaurant" in types or "cafe" in types:
        return 90
    if category == "historico":
        return 60
    if category == "cultural":
        return 90
    return 45


# ═══════════════════════════════════════════════════════════════════════════════
#                           FUNCIÓN PRINCIPAL DE SEED
# ═══════════════════════════════════════════════════════════════════════════════

def seed_with_apis(
    location_name: str = "Ciudad de México, México",
    max_attractions: int = 30,
    search_radius: int = 15000  # 15 km
):
    """
    Pobla la base de datos usando Google Places API
    
    Args:
        location_name: Nombre del destino (ej: "Lima, Perú")
        max_attractions: Máximo de atracciones a importar
        search_radius: Radio de búsqueda en metros
    """
    
    # Verificar API keys
    if not settings.GOOGLE_PLACES_API_KEY:
        print("❌ ERROR: GOOGLE_PLACES_API_KEY no configurada en .env")
        print("   Obténla en: https://console.cloud.google.com/apis/credentials")
        print("\n   Ejecutando seed manual como fallback...")
        seed_manual()
        return
    
    db = SessionLocal()
    google = GooglePlacesClient(settings.GOOGLE_PLACES_API_KEY)
    foursquare = None
    if settings.FOURSQUARE_API_KEY:
        foursquare = FoursquareClient(settings.FOURSQUARE_API_KEY)
    
    try:
        print("═" * 60)
        print(f"🌱 SEED AUTOMÁTICO: {location_name}")
        print("═" * 60)
        
        # ───────────────────────────────────────────────────────
        # 1. GEOCODIFICAR UBICACIÓN
        # ───────────────────────────────────────────────────────
        print(f"\n📍 Geocodificando '{location_name}'...")
        coords = google.geocode_location(location_name)
        
        if not coords:
            print(f"❌ No se pudo geocodificar '{location_name}'")
            return
        
        lat, lng = coords
        print(f"   ✅ Coordenadas: {lat}, {lng}")
        
        # ───────────────────────────────────────────────────────
        # 2. CREAR O ACTUALIZAR DESTINO
        # ───────────────────────────────────────────────────────
        # Extraer nombre limpio del destino
        dest_name = location_name.split(",")[0].strip()
        country = location_name.split(",")[-1].strip() if "," in location_name else ""
        
        destination = db.query(Destination).filter(
            Destination.name == dest_name
        ).first()
        
        if not destination:
            destination = Destination(
                name=dest_name,
                country=country,
                description=f"Destino turístico: {location_name}",
                location=WKTElement(f"POINT({lng} {lat})", srid=4326),
                timezone="UTC"
            )
            db.add(destination)
            db.commit()
            db.refresh(destination)
            print(f"\n✅ Destino creado: {dest_name} (ID: {destination.id})")
        else:
            print(f"\nℹ️ Destino existente: {dest_name} (ID: {destination.id})")
        
        # ───────────────────────────────────────────────────────
        # 3. BUSCAR ATRACCIONES EN GOOGLE PLACES
        # ───────────────────────────────────────────────────────
        print(f"\n🔍 Buscando atracciones en Google Places...")
        print(f"   Radio de búsqueda: {search_radius/1000} km")
        
        all_places = []
        seen_place_ids = set()
        
        for place_type in PLACE_TYPES_TO_SEARCH:
            print(f"   → Buscando tipo: {place_type}...")
            places = google.search_nearby(lat, lng, search_radius, place_type)
            
            for place in places:
                place_id = place.get("place_id")
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    all_places.append(place)
        
        print(f"   ✅ Encontrados: {len(all_places)} lugares únicos")
        
        # Ordenar por rating y limitar
        all_places.sort(
            key=lambda x: (x.get("rating", 0), x.get("user_ratings_total", 0)),
            reverse=True
        )
        all_places = all_places[:max_attractions]
        
        # ───────────────────────────────────────────────────────
        # 4. IMPORTAR ATRACCIONES A LA BD
        # ───────────────────────────────────────────────────────
        print(f"\n📥 Importando {len(all_places)} atracciones...")
        
        created_count = 0
        updated_count = 0
        
        for i, place in enumerate(all_places):
            name = place.get("name", "Sin nombre")
            place_id = place.get("place_id")
            
            # Verificar si ya existe
            existing = db.query(Attraction).filter(
                Attraction.google_place_id == place_id
            ).first()
            
            if existing:
                updated_count += 1
                continue
            
            # Obtener detalles completos
            details = google.get_place_details(place_id) if place_id else None
            
            # Extraer coordenadas
            geometry = place.get("geometry", {})
            location = geometry.get("location", {})
            place_lat = location.get("lat", lat)
            place_lng = location.get("lng", lng)
            
            # Mapear categoría
            types = place.get("types", [])
            category = map_google_type_to_category(types)
            
            # Crear atracción
            attraction = Attraction(
                destination_id=destination.id,
                name=name,
                category=category,
                subcategory=types[0] if types else None,
                location=WKTElement(f"POINT({place_lng} {place_lat})", srid=4326),
                description=details.get("formatted_address") if details else place.get("vicinity"),
                
                # Datos de Google
                google_place_id=place_id,
                google_rating=place.get("rating"),
                google_reviews_count=place.get("user_ratings_total"),
                
                # Rating principal (de Google por ahora)
                rating=place.get("rating", 0),
                total_reviews=place.get("user_ratings_total", 0),
                
                # Precio y duración
                price_range=map_price_level(place.get("price_level")),
                average_visit_duration=estimate_visit_duration(types, category),
                
                # Metadata
                verified=True,
                is_active=True,
                external_data_updated_at=datetime.utcnow()
            )
            
            # Si hay horarios
            if details and details.get("opening_hours"):
                hours = details["opening_hours"]
                if hours.get("weekday_text"):
                    attraction.opening_hours = {"weekday_text": hours["weekday_text"]}
            
            # Si hay foto, guardar referencia
            if place.get("photos"):
                photo_ref = place["photos"][0].get("photo_reference")
                if photo_ref:
                    attraction.image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}&key={settings.GOOGLE_PLACES_API_KEY}"
            
            db.add(attraction)
            created_count += 1
            
            # Mostrar progreso
            if (i + 1) % 10 == 0:
                print(f"   Procesadas: {i + 1}/{len(all_places)}")
                db.commit()  # Commit parcial
        
        db.commit()
        print(f"   ✅ Creadas: {created_count} | Ya existían: {updated_count}")
        
        # ───────────────────────────────────────────────────────
        # 5. ENRIQUECER CON FOURSQUARE (OPCIONAL)
        # ───────────────────────────────────────────────────────
        if foursquare:
            print(f"\n🔄 Enriqueciendo con Foursquare...")
            attractions = db.query(Attraction).filter(
                Attraction.destination_id == destination.id,
                Attraction.foursquare_id == None
            ).limit(50).all()  # Límite por API gratuita
            
            fsq_places = foursquare.search_nearby(lat, lng, search_radius)
            
            # Crear índice por nombre para matching
            fsq_by_name = {p.get("name", "").lower(): p for p in fsq_places}
            
            enriched = 0
            for attr in attractions:
                # Buscar match por nombre similar
                attr_name_lower = attr.name.lower()
                for fsq_name, fsq_data in fsq_by_name.items():
                    if attr_name_lower in fsq_name or fsq_name in attr_name_lower:
                        # Match encontrado
                        attr.foursquare_id = fsq_data.get("fsq_id")
                        if fsq_data.get("rating"):
                            attr.foursquare_rating = fsq_data["rating"]
                        if fsq_data.get("popularity"):
                            attr.foursquare_popularity = fsq_data["popularity"]
                        enriched += 1
                        break
            
            db.commit()
            print(f"   ✅ Enriquecidas: {enriched} atracciones")
        
        # ───────────────────────────────────────────────────────
        # 6. GENERAR CONEXIONES AUTOMÁTICAS
        # ───────────────────────────────────────────────────────
        print(f"\n🔗 Generando conexiones entre atracciones...")
        
        all_attrs = db.query(Attraction).filter(
            Attraction.destination_id == destination.id
        ).all()
        
        connections_count = 0
        
        for i, origin in enumerate(all_attrs):
            # Extraer coordenadas
            try:
                wkt_origin = db.scalar(origin.location.ST_AsText())
                coords_o = wkt_origin.replace("POINT(", "").replace(")", "").split(" ")
                lon1, lat1 = float(coords_o[0]), float(coords_o[1])
            except:
                continue
            
            for j, target in enumerate(all_attrs):
                if i >= j:  # Evitar duplicados y auto-conexiones
                    continue
                
                try:
                    wkt_target = db.scalar(target.location.ST_AsText())
                    coords_t = wkt_target.replace("POINT(", "").replace(")", "").split(" ")
                    lon2, lat2 = float(coords_t[0]), float(coords_t[1])
                except:
                    continue
                
                dist_meters = haversine_distance(lon1, lat1, lon2, lat2)
                
                # Solo conectar si están relativamente cerca
                if dist_meters > 20000:  # Más de 20km, ignorar
                    continue
                
                modes = []
                
                # Caminata (< 2km)
                if dist_meters <= 2000:
                    walking_time = int((dist_meters / 1000) / 4.5 * 60)
                    modes.append(("walking", walking_time, 0))
                
                # Taxi/Uber (500m - 20km)
                if dist_meters > 500:
                    car_time = int((dist_meters / 1000) / 25 * 60) + 5
                    cost = 30 + (dist_meters / 1000 * 8)
                    modes.append(("taxi", car_time, cost))
                
                # Transporte público (1km - 15km)
                if 1000 < dist_meters < 15000:
                    transit_time = int((dist_meters / 1000) / 18 * 60) + 10
                    modes.append(("public_transport", transit_time, 5))
                
                for mode, time_min, cost in modes:
                    # Verificar si existe (en ambas direcciones)
                    exists = db.query(AttractionConnection).filter(
                        ((AttractionConnection.from_attraction_id == origin.id) & 
                         (AttractionConnection.to_attraction_id == target.id)) |
                        ((AttractionConnection.from_attraction_id == target.id) & 
                         (AttractionConnection.to_attraction_id == origin.id)),
                        AttractionConnection.transport_mode == mode
                    ).first()
                    
                    if not exists:
                        # Crear conexión bidireccional
                        conn1 = AttractionConnection(
                            from_attraction_id=origin.id,
                            to_attraction_id=target.id,
                            distance_meters=dist_meters,
                            travel_time_minutes=time_min,
                            transport_mode=mode,
                            cost=cost,
                            traffic_factor=1.2 if mode == 'taxi' else 1.0
                        )
                        conn2 = AttractionConnection(
                            from_attraction_id=target.id,
                            to_attraction_id=origin.id,
                            distance_meters=dist_meters,
                            travel_time_minutes=time_min,
                            transport_mode=mode,
                            cost=cost,
                            traffic_factor=1.2 if mode == 'taxi' else 1.0
                        )
                        db.add(conn1)
                        db.add(conn2)
                        connections_count += 2
            
            # Commit periódico
            if (i + 1) % 20 == 0:
                db.commit()
        
        db.commit()
        print(f"   ✅ {connections_count} conexiones creadas")
        
        # ───────────────────────────────────────────────────────
        # 7. CREAR USUARIO DEMO
        # ───────────────────────────────────────────────────────
        create_demo_user(db)
        
        # ───────────────────────────────────────────────────────
        # RESUMEN FINAL
        # ───────────────────────────────────────────────────────
        total_attractions = db.query(Attraction).filter(
            Attraction.destination_id == destination.id
        ).count()
        
        total_connections = db.query(AttractionConnection).count()
        
        print("\n" + "═" * 60)
        print("🏁 SEED COMPLETADO")
        print("═" * 60)
        print(f"   📍 Destino: {destination.name}")
        print(f"   🏛️ Atracciones: {total_attractions}")
        print(f"   🔗 Conexiones: {total_connections}")
        print(f"   👤 Usuario demo: demo@tripwise.com / demo123")
        print("═" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        google.close()
        if foursquare:
            foursquare.close()
        db.close()


def create_demo_user(db: Session):
    """Crea usuario demo si no existe"""
    user_email = "demo@tripwise.com"
    existing = db.query(User).filter(User.email == user_email).first()
    
    if not existing:
        user = User(
            email=user_email,
            hashed_password=get_password_hash("demo123"),
            full_name="Viajero Demo",
            is_active=True
        )
        db.add(user)
        db.commit()
        print(f"\n👤 Usuario demo creado: {user_email} / demo123")
    else:
        print(f"\n👤 Usuario demo ya existe")


def seed_manual():
    """
    Seed manual como fallback (sin APIs)
    Datos de CDMX predefinidos
    """
    print("\n⚠️ Ejecutando seed manual (sin APIs)...")
    
    db = SessionLocal()
    
    # Crear destino
    cdmx = db.query(Destination).filter(Destination.name == "Ciudad de México").first()
    if not cdmx:
        cdmx = Destination(
            name="Ciudad de México",
            country="México",
            state="CDMX",
            description="Capital de México, una de las ciudades más grandes del mundo.",
            location=WKTElement("POINT(-99.1332 19.4326)", srid=4326),
            timezone="America/Mexico_City"
        )
        db.add(cdmx)
        db.commit()
        db.refresh(cdmx)
        print(f"✅ Destino creado: {cdmx.name}")
    
    # Datos manuales
    attractions_data = [
        {"n": "Zócalo Capitalino", "c": "historico", "lat": 19.4326, "lng": -99.1332, "r": 4.8},
        {"n": "Catedral Metropolitana", "c": "religioso", "lat": 19.4337, "lng": -99.1330, "r": 4.7},
        {"n": "Palacio de Bellas Artes", "c": "cultural", "lat": 19.4352, "lng": -99.1412, "r": 4.9},
        {"n": "Museo Nacional de Antropología", "c": "cultural", "lat": 19.4260, "lng": -99.1870, "r": 5.0},
        {"n": "Castillo de Chapultepec", "c": "historico", "lat": 19.4204, "lng": -99.1819, "r": 4.9},
        {"n": "Ángel de la Independencia", "c": "historico", "lat": 19.4270, "lng": -99.1677, "r": 4.8},
        {"n": "Museo Frida Kahlo", "c": "cultural", "lat": 19.3551, "lng": -99.1625, "r": 4.6},
        {"n": "Xochimilco", "c": "aventura", "lat": 19.2600, "lng": -99.1000, "r": 4.4},
        {"n": "Templo Mayor", "c": "historico", "lat": 19.4350, "lng": -99.1313, "r": 4.8},
        {"n": "Alameda Central", "c": "naturaleza", "lat": 19.4356, "lng": -99.1440, "r": 4.6},
    ]
    
    created = 0
    for item in attractions_data:
        exists = db.query(Attraction).filter(Attraction.name == item["n"]).first()
        if not exists:
            attr = Attraction(
                destination_id=cdmx.id,
                name=item["n"],
                category=item["c"],
                location=WKTElement(f"POINT({item['lng']} {item['lat']})", srid=4326),
                rating=item["r"],
                average_visit_duration=60,
                verified=True
            )
            db.add(attr)
            created += 1
    
    db.commit()
    print(f"✅ {created} atracciones creadas")
    
    # Generar conexiones básicas
    print("🔗 Generando conexiones...")
    all_attrs = db.query(Attraction).filter(Attraction.destination_id == cdmx.id).all()
    connections = 0
    
    for i, origin in enumerate(all_attrs):
        try:
            wkt_o = db.scalar(origin.location.ST_AsText())
            coords_o = wkt_o.replace("POINT(", "").replace(")", "").split(" ")
            lon1, lat1 = float(coords_o[0]), float(coords_o[1])
        except:
            continue
        
        for j, target in enumerate(all_attrs):
            if i >= j:
                continue
            try:
                wkt_t = db.scalar(target.location.ST_AsText())
                coords_t = wkt_t.replace("POINT(", "").replace(")", "").split(" ")
                lon2, lat2 = float(coords_t[0]), float(coords_t[1])
            except:
                continue
            
            dist = haversine_distance(lon1, lat1, lon2, lat2)
            if dist < 15000:
                time_min = int((dist / 1000) / 20 * 60) + 5
                conn1 = AttractionConnection(
                    from_attraction_id=origin.id,
                    to_attraction_id=target.id,
                    distance_meters=dist,
                    travel_time_minutes=time_min,
                    transport_mode="taxi",
                    cost=30 + dist/1000*8
                )
                conn2 = AttractionConnection(
                    from_attraction_id=target.id,
                    to_attraction_id=origin.id,
                    distance_meters=dist,
                    travel_time_minutes=time_min,
                    transport_mode="taxi",
                    cost=30 + dist/1000*8
                )
                db.add(conn1)
                db.add(conn2)
                connections += 2
    
    db.commit()
    print(f"✅ {connections} conexiones creadas")
    
    create_demo_user(db)
    db.close()
    print("🏁 Seed manual completado")


# ═══════════════════════════════════════════════════════════════════════════════
#                              MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Argumentos: python seed_data.py "Lima, Perú" 50
    location = sys.argv[1] if len(sys.argv) > 1 else "Ciudad de México, México"
    max_attr = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    seed_with_apis(location, max_attr)
