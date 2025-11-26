# shared/database/models/destination.py
"""
Modelo para destinos turísticos (ciudades)
"""
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped
from geoalchemy2 import Geography # type: ignore
from typing import Optional
from datetime import datetime
from shared.database.base import Base
from sqlalchemy.orm import relationship


class Destination(Base):
    """
    Tabla de destinos turísticos (ciudades/regiones)
    """
    __tablename__ = "destinations"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(255), nullable=False, index=True)
    country: Mapped[str] = Column(String(100), nullable=False, index=True)
    state: Mapped[Optional[str]] = Column(String(100))
    
    # Ubicación geográfica (Point)
    location: Mapped[str] = Column(
        Geography(geometry_type='POINT', srid=4326),
        nullable=False
    )
    
    # Metadata
    timezone: Mapped[Optional[str]] = Column(String(50))
    description: Mapped[Optional[str]] = Column(String(1000))
    population: Mapped[Optional[int]] = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    itineraries = relationship(
        "Itinerary",
        back_populates="destination",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Destination(id={self.id}, name='{self.name}', country='{self.country}')>"

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "state": self.state,
            "timezone": self.timezone,
            "description": self.description,
            "population": self.population,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }