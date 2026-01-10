# shared/database/models/attraction.py
"""
Modelo para atracciones turísticas
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, 
    Boolean, Numeric, ForeignKey, func, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography # type: ignore
from shared.database.base import Base


class Attraction(Base):
    """
    Tabla de atracciones turísticas
    
    LÍMITES DE RENDIMIENTO:
    - Max 500 atracciones por destino
    - Max 50 reviews por atracción
    - Max 100 conexiones por atracción
    """
    __tablename__ = "attractions"

    id = Column(Integer, primary_key=True, index=True)
    destination_id = Column(
        Integer, 
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Información básica
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    
    # Categorización
    category = Column(String(100), nullable=False, index=True)
    # Categorías: 'cultural', 'aventura', 'gastronomia', 'naturaleza', 
    # 'entretenimiento', 'compras', 'religioso', 'historico', 'deportivo'
    
    subcategory = Column(String(100), index=True)
    tags = Column(JSONB)  # Array de tags: ['museo', 'arte', 'historia']
    
    # Ubicación
    location = Column(
        Geography(geometry_type='POINT', srid=4326),
        nullable=False
    )
    address = Column(String(500))
    
    # Tiempos y costos
    average_visit_duration = Column(Integer)  # Minutos
    price_range = Column(String(20))  # 'gratis', 'bajo', 'medio', 'alto'
    price_min = Column(Numeric(10, 2))  # Precio mínimo en moneda local
    price_max = Column(Numeric(10, 2))  # Precio máximo
    
    # Horarios (formato flexible para diferentes días)
    opening_hours = Column(JSONB)
    # Ejemplo: {"lunes": {"open": "09:00", "close": "18:00"}, ...}
    
    # ═══════════════════════════════════════════════════════════
    # RATINGS Y SCORES (Multi-fuente)
    # ═══════════════════════════════════════════════════════════
    
    # Rating principal (promedio de todas las fuentes)
    rating = Column(Numeric(3, 2))  # 0.00 a 5.00
    total_reviews = Column(Integer, default=0)
    
    # Ratings por fuente (para la red neuronal)
    google_rating = Column(Numeric(3, 2))  # Rating de Google Places
    google_reviews_count = Column(Integer, default=0)
    foursquare_rating = Column(Numeric(3, 2))  # Rating de Foursquare (escala 10)
    foursquare_popularity = Column(Numeric(5, 4))  # 0.0000 a 1.0000
    foursquare_checkins = Column(Integer, default=0)
    
    # Score calculado por la Red Neuronal (USADO POR LOS ALGORITMOS)
    nn_score = Column(Numeric(5, 4), default=0.5, index=True)
    # Score normalizado 0-1 calculado por el modelo de ML
    # Este es el valor que usan BFS y A* para priorizar
    
    nn_score_updated_at = Column(DateTime(timezone=True))
    # Cuándo se actualizó el score por última vez
    
    # Score de popularidad (calculado por fórmula o NN)
    popularity_score = Column(Numeric(5, 2), default=0.0)
    # Calculado por algoritmo: visitas, reviews, ratings, etc.
    
    # ═══════════════════════════════════════════════════════════
    # ANÁLISIS DE SENTIMIENTO (de reviews)
    # ═══════════════════════════════════════════════════════════
    
    sentiment_score = Column(Numeric(4, 3))  # -1.000 a 1.000
    # Promedio de sentiment de todas las reviews
    
    sentiment_positive_pct = Column(Numeric(5, 2))  # 0.00 a 100.00
    # Porcentaje de reviews positivas
    
    # ═══════════════════════════════════════════════════════════
    
    # Validación de datos
    verified = Column(Boolean, default=False)
    data_source = Column(String(100))  # 'google_places', 'foursquare', 'manual'
    
    # IDs de fuentes externas (para sincronización)
    google_place_id = Column(String(255), index=True)
    foursquare_id = Column(String(255), index=True)
    
    # Timestamp de última sincronización con APIs externas
    external_data_updated_at = Column(DateTime(timezone=True))
    
    # Accesibilidad y servicios
    accessibility = Column(JSONB)
    # Ejemplo: {"wheelchair": true, "parking": true, "wifi": false}
    
    # Metadata adicional flexible
    extra_data = Column(JSONB)
    # Puede contener: contacto, website, redes sociales, restricciones, etc.
    
    # Imágenes
    image_url = Column(String(500))  # URL de imagen principal
    images = Column(JSONB)
    # Ejemplo: [{"url": "...", "caption": "..."}, ...]
    
    # Estado
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    destination = relationship("Destination", backref="attractions")

    # Índices compuestos para rendimiento
    __table_args__ = (
        Index('idx_attraction_location', 'location', postgresql_using='gist'),
        Index('idx_attraction_category_rating', 'category', 'rating'),
        # Nuevo: índice para score de NN (usado en ORDER BY)
        Index('idx_attraction_nn_score', 'nn_score', postgresql_ops={'nn_score': 'DESC'}),
        # Nuevo: índice para búsquedas por destino + score
        Index('idx_attraction_dest_score', 'destination_id', 'nn_score'),
        # Nuevo: índice para búsquedas por categoría + score
        Index('idx_attraction_cat_score', 'category', 'nn_score'),
    )

    def __repr__(self):
        return f"<Attraction(id={self.id}, name='{self.name}', nn_score={self.nn_score})>"

    def to_dict(self):
        """Convierte el modelo a diccionario (incluye datos de Foursquare)"""
        return {
            "id": self.id,
            "destination_id": self.destination_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "tags": self.tags,
            "address": self.address,
            "average_visit_duration": self.average_visit_duration,
            "price_range": self.price_range,
            "price_min": float(self.price_min) if self.price_min else None, # type: ignore
            "price_max": float(self.price_max) if self.price_max else None, # type: ignore
            "opening_hours": self.opening_hours,
            "rating": float(self.rating) if self.rating else None, # type: ignore
            "total_reviews": self.total_reviews,
            "nn_score": float(self.nn_score) if self.nn_score else 0.5,  # type: ignore
            # Datos de Foursquare
            "foursquare_rating": float(self.foursquare_rating) if self.foursquare_rating else 0.0,  # type: ignore
            "foursquare_popularity": float(self.foursquare_popularity) if self.foursquare_popularity else 0.0,  # type: ignore
            "foursquare_checkins": self.foursquare_checkins or 0,
            "popularity_score": float(self.popularity_score) if self.popularity_score else None, # type: ignore
            "sentiment_score": float(self.sentiment_score) if self.sentiment_score else None,  # type: ignore
            "verified": self.verified,
            "accessibility": self.accessibility,
            "extra_data": self.extra_data,
            "images": self.images,
            "created_at": self.created_at.isoformat() if self.created_at else None, # type: ignore
            "updated_at": self.updated_at.isoformat() if self.updated_at else None, # type: ignore
        }
    
    def get_features_for_nn(self) -> dict:
        """
        Obtener características para la red neuronal
        Usado por el dataset_loader
        """
        return {
            "rating": float(self.rating) if self.rating else 0.0,
            "total_reviews": self.total_reviews or 0,
            "google_rating": float(self.google_rating) if self.google_rating else 0.0,
            "google_reviews": self.google_reviews_count or 0,
            "foursquare_rating": float(self.foursquare_rating) if self.foursquare_rating else 0.0,
            "foursquare_popularity": float(self.foursquare_popularity) if self.foursquare_popularity else 0.0,
            "foursquare_checkins": self.foursquare_checkins or 0,
            "sentiment_score": float(self.sentiment_score) if self.sentiment_score else 0.0,
            "sentiment_positive_pct": float(self.sentiment_positive_pct) if self.sentiment_positive_pct else 50.0,
            "price_level": self._price_to_numeric(),
            "has_accessibility": 1.0 if self.accessibility else 0.0,
            "is_verified": 1.0 if self.verified else 0.0,
            "category_encoded": self._category_to_numeric()
        }
    
    def _price_to_numeric(self) -> float:
        """Convertir rango de precio a numérico"""
        mapping = {"gratis": 0.0, "bajo": 0.25, "medio": 0.5, "alto": 0.75, "lujo": 1.0}
        return mapping.get(self.price_range, 0.5)
    
    def _category_to_numeric(self) -> float:
        """Convertir categoría a numérico (para embedding simple)"""
        categories = [
            'cultural', 'historico', 'gastronomia', 'naturaleza',
            'aventura', 'deportivo', 'entretenimiento', 'compras', 'religioso'
        ]
        if self.category in categories:
            return categories.index(self.category) / len(categories)
        return 0.5