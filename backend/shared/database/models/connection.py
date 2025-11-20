# shared/database/models/connection.py
"""
Modelo para conexiones entre atracciones (aristas del grafo)
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, 
    ForeignKey, DateTime, func, Index
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography # type: ignore
from shared.database.base import Base


class AttractionConnection(Base):
    """
    Tabla de conexiones entre atracciones (aristas del grafo)
    Representa las rutas posibles entre dos atracciones
    """
    __tablename__ = "attraction_connections"

    id = Column(Integer, primary_key=True, index=True)
    
    # Nodos origen y destino
    from_attraction_id = Column(
        Integer,
        ForeignKey("attractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    to_attraction_id = Column(
        Integer,
        ForeignKey("attractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Métricas de distancia y tiempo
    distance_meters = Column(Numeric(10, 2), nullable=False)
    travel_time_minutes = Column(Integer, nullable=False)
    
    # Modo de transporte
    transport_mode = Column(String(50), nullable=False)
    # Valores: 'walking', 'car', 'public_transport', 'bicycle', 'taxi'
    
    # Costo del desplazamiento (opcional)
    cost = Column(Numeric(10, 2), default=0.0)
    
    # Geometría de la ruta (línea)
    route_geometry = Column(
        Geography(geometry_type='LINESTRING', srid=4326)
    )
    
    # Información adicional
    traffic_factor = Column(Numeric(3, 2), default=1.0)
    # Factor de tráfico: 1.0 = normal, >1.0 = más lento
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    from_attraction = relationship(
        "Attraction",
        foreign_keys=[from_attraction_id],
        backref="outgoing_connections"
    )
    to_attraction = relationship(
        "Attraction",
        foreign_keys=[to_attraction_id],
        backref="incoming_connections"
    )

    # Índices
    __table_args__ = (
        Index('idx_connection_from_to', 'from_attraction_id', 'to_attraction_id'),
        Index('idx_connection_transport', 'transport_mode'),
    )

    def __repr__(self):
        return (
            f"<AttractionConnection("
            f"from={self.from_attraction_id}, "
            f"to={self.to_attraction_id}, "
            f"mode='{self.transport_mode}')>"
        )

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "from_attraction_id": self.from_attraction_id,
            "to_attraction_id": self.to_attraction_id,
            "distance_meters": float(self.distance_meters) if self.distance_meters else None, # type: ignore
            "travel_time_minutes": self.travel_time_minutes,
            "transport_mode": self.transport_mode,
            "cost": float(self.cost) if self.cost else None, # type: ignore
            "traffic_factor": float(self.traffic_factor) if self.traffic_factor else None, # type: ignore
            "created_at": self.created_at.isoformat() if self.created_at else None, # type: ignore
        }

    @property
    def weighted_time(self):
        """Tiempo ponderado considerando el factor de tráfico"""
        return self.travel_time_minutes * float(self.traffic_factor) # type: ignore