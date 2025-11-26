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
    
    # Popularidad y rating
    rating = Column(Numeric(3, 2))  # 0.00 a 5.00
    total_reviews = Column(Integer, default=0)
    popularity_score = Column(Numeric(5, 2), default=0.0)
    # Calculado por algoritmo: visitas, reviews, ratings, etc.
    
    # Validación de datos
    verified = Column(Boolean, default=False)
    data_source = Column(String(100))  # 'google_places', 'tripadvisor', 'manual'
    
    # Accesibilidad y servicios
    accessibility = Column(JSONB)
    # Ejemplo: {"wheelchair": true, "parking": true, "wifi": false}
    
    # Metadata adicional flexible
    extra_data = Column(JSONB)
    # Puede contener: contacto, website, redes sociales, restricciones, etc.
    
    # Imágenes
    images = Column(JSONB)
    # Ejemplo: [{"url": "...", "caption": "..."}, ...]
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    destination = relationship("Destination", backref="attractions")

    # Índices compuestos
    __table_args__ = (
        Index('idx_attraction_location', 'location', postgresql_using='gist'),
        Index('idx_attraction_category_rating', 'category', 'rating'),
    )

    def __repr__(self):
        return f"<Attraction(id={self.id}, name='{self.name}', category='{self.category}')>"

    def to_dict(self):
        """Convierte el modelo a diccionario"""
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
            "popularity_score": float(self.popularity_score) if self.popularity_score else None, # type: ignore
            "verified": self.verified,
            "accessibility": self.accessibility,
            "extra_data": self.extra_data,
            "images": self.images,
            "created_at": self.created_at.isoformat() if self.created_at else None, # type: ignore
            "updated_at": self.updated_at.isoformat() if self.updated_at else None, # type: ignore
        }