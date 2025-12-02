# backend/shared/schemas/attraction.py
"""
Schemas para atracciones turísticas
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from datetime import datetime
from .base import Location, ResponseBase, TimestampMixin
from geoalchemy2.elements import WKBElement # type: ignore
from geoalchemy2.shape import to_shape # type: ignore

if TYPE_CHECKING:
    from .destination import DestinationRead

class AttractionBase(BaseModel):
    """Schema base de atracción"""
    name: str = Field(..., min_length=1, max_length=255, description="Nombre de la atracción")
    description: Optional[str] = Field(None, description="Descripción detallada")
    category: str = Field(..., max_length=100, description="Categoría principal")
    subcategory: Optional[str] = Field(None, max_length=100, description="Subcategoría")
    address: Optional[str] = Field(None, max_length=500, description="Dirección física")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validar que la categoría sea válida"""
        valid_categories = [
            'cultural', 'aventura', 'gastronomia', 'naturaleza',
            'entretenimiento', 'compras', 'religioso', 'historico', 'deportivo'
        ]
        if v.lower() not in valid_categories:
            raise ValueError(f'Categoría debe ser una de: {", ".join(valid_categories)}')
        return v.lower()
    
    


class AttractionCreate(AttractionBase):
    """Schema para crear una atracción"""
    destination_id: int = Field(..., gt=0, description="ID del destino")
    location: Any = Field(..., description="Coordenadas (Lat/Lon dict o WKT string)")
    # Formato: {"lat": -12.0464, "lon": -77.0428}
    
    tags: Optional[List[str]] = Field(None, description="Etiquetas descriptivas")
    average_visit_duration: Optional[int] = Field(None, gt=0, description="Duración promedio de visita en minutos")
    price_range: Optional[str] = Field(None, pattern="^(gratis|bajo|medio|alto)$")
    price_min: Optional[float] = Field(None, ge=0, description="Precio mínimo")
    price_max: Optional[float] = Field(None, ge=0, description="Precio máximo")
    opening_hours: Optional[Dict[str, Dict[str, str]]] = Field(None, description="Horarios de apertura")
    accessibility: Optional[Dict[str, bool]] = Field(None, description="Características de accesibilidad")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Datos adicionales")
    images: Optional[List[Dict[str, str]]] = Field(None, description="URLs de imágenes")

    
    @field_validator('price_max')
    @classmethod
    def validate_price_range(cls, v: Optional[float], info) -> Optional[float]:
        """Validar que price_max >= price_min"""
        if v is not None and 'price_min' in info.data:
            price_min = info.data.get('price_min')
            if price_min is not None and v < price_min:
                raise ValueError('price_max debe ser mayor o igual a price_min')
        return v
    
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "destination_id": 1,
                "name": "Museo Larco",
                "description": "Museo de arte precolombino en una mansión del siglo XVIII",
                "category": "cultural",
                "subcategory": "museo",
                "tags": ["museo", "arte", "precolombino", "ceramica"],
                "location": {"lat": -12.0699, "lon": -77.0691},
                "address": "Av. Bolívar 1515, Pueblo Libre",
                "average_visit_duration": 120,
                "price_range": "medio",
                "price_min": 30.0,
                "price_max": 35.0,
                "opening_hours": {
                    "lunes": {"open": "09:00", "close": "22:00"},
                    "martes": {"open": "09:00", "close": "22:00"}
                },
                "accessibility": {
                    "wheelchair": True,
                    "parking": True,
                    "wifi": True
                },
                "extra_data": {
                    "website": "https://www.museolarco.org",
                    "phone": "+51 1 461 1312"
                }
            }
        }
    )


class AttractionUpdate(BaseModel):
    """Schema para actualizar una atracción"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    address: Optional[str] = None
    tags: Optional[List[str]] = None
    average_visit_duration: Optional[int] = Field(None, gt=0)
    price_range: Optional[str] = None
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    verified: Optional[bool] = None
    accessibility: Optional[Dict[str, bool]] = None
    extra_data: Optional[Dict[str, Any]] = None
    images: Optional[List[Dict[str, str]]] = None


class AttractionRead(AttractionBase, ResponseBase, TimestampMixin):
    """Schema para leer una atracción"""
    id: int
    destination_id: int
    location: Any = Field(..., description="Coordenadas (Lat/Lon dict o WKT string)")
    tags: Optional[List[str]] = None
    average_visit_duration: Optional[int] = None
    price_range: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    opening_hours: Optional[Dict[str, Dict[str, str]]] = None
    rating: Optional[float] = None
    total_reviews: int
    popularity_score: Optional[float] = None
    verified: bool
    data_source: Optional[str] = None
    accessibility: Optional[Dict[str, bool]] = None
    extra_data: Optional[Dict[str, Any]] = None
    images: Optional[List[Dict[str, str]]] = None
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @field_serializer('location')
    def serialize_location(self, value, _info):
        try:
            # 1. Si es un objeto de Base de Datos (WKBElement)
            if hasattr(value, 'desc') or isinstance(value, WKBElement):
                # Convertimos el binario a objeto Python (Shapely)
                point = to_shape(value)
                # Retornamos formato texto: "POINT(-99.13 19.43)"
                return f"POINT({point.x} {point.y})"
            
            # 2. Si ya es un string hexadecimal (el caso que te está pasando)
            if isinstance(value, str) and value.startswith('01010000'):
                # Es un hex WKB crudo. Como es difícil parsear aquí sin librerías extra,
                # devolvemos None para que el frontend use el fallback o intentamos pasarlo.
                # (Normalmente to_shape ya lo maneja antes de que sea string).
                return value 

            # 3. Si ya es texto o dict, lo dejamos pasar
            return value
            
        except Exception as e:
            # Si falla la conversión, retornamos string para debug
            return str(value)


class AttractionWithDestination(AttractionRead):
    """Atracción con información del destino"""
    destination: 'DestinationRead'  # ← Forward reference como string


class AttractionWithDistance(AttractionRead):
    """Atracción con distancia calculada"""
    distance_meters: float = Field(..., description="Distancia en metros desde un punto de referencia")
    travel_time_minutes: Optional[int] = Field(None, description="Tiempo estimado de viaje en minutos")

class AttractionSearchParams(BaseModel):
    """Parámetros de búsqueda de atracciones (sin geolocalización)"""
    category: Optional[str] = None
    subcategory: Optional[str] = None
    min_rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    price_range: Optional[str] = None
    verified_only: bool = False
    tags: Optional[List[str]] = None


class AttractionNearbyParams(BaseModel):
    """Parámetros para búsqueda geoespacial"""
    lat: float = Field(..., ge=-90, le=90, description="Latitud")
    lon: float = Field(..., ge=-180, le=180, description="Longitud")
    radius_km: float = Field(5.0, gt=0, le=100, description="Radio en kilómetros")
    category: Optional[str] = None


class AttractionListResponse(BaseModel):
    """Respuesta de lista de atracciones"""
    total: int
    skip: int
    limit: int
    items: List[AttractionRead]