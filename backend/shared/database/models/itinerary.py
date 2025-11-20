# shared/database/models/itinerary.py
"""
Modelos para itinerarios generados
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, 
    Numeric, ForeignKey, func, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from shared.database.base import Base


class Itinerary(Base):
    """
    Tabla de itinerarios generados por el sistema
    """
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    
    # Referencias
    user_profile_id = Column(
        Integer,
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    destination_id = Column(
        Integer,
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Nombre del itinerario
    name = Column(String(255))
    description = Column(String(1000))
    
    # Datos de la ruta calculada
    route_data = Column(JSONB, nullable=False)
    # Ejemplo:
    # {
    #   "sequence": [
    #     {
    #       "order": 1,
    #       "attraction_id": 5,
    #       "arrival_time": "09:00",
    #       "departure_time": "10:30",
    #       "visit_duration": 90
    #     },
    #     ...
    #   ],
    #   "connections": [
    #     {
    #       "from": 5,
    #       "to": 8,
    #       "transport": "walking",
    #       "duration": 15
    #     },
    #     ...
    #   ]
    # }
    
    # Métricas del itinerario
    total_duration = Column(Integer)  # Minutos totales
    total_cost = Column(Numeric(10, 2))  # Costo total estimado
    total_distance = Column(Numeric(10, 2))  # Distancia total en metros
    
    # Puntuación de optimización (calculada por A*)
    optimization_score = Column(Numeric(5, 2))
    
    # Algoritmos utilizados
    algorithms_used = Column(JSONB)
    # Ejemplo: {"search": "BFS", "routing": "A*", "ml_model": "neural_network_v1"}
    
    # Estado
    status = Column(String(50), default='draft')
    # Valores: 'draft', 'confirmed', 'in_progress', 'completed', 'cancelled'
    
    # Feedback del usuario
    user_rating = Column(Integer)  # 1-5
    user_feedback = Column(String(1000))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Fecha de inicio planificada
    start_date = Column(DateTime(timezone=True))
    
    # Relaciones
    user_profile = relationship("UserProfile", backref="itineraries")
    destination = relationship("Destination", backref="itineraries")

    # Índices
    __table_args__ = (
        Index('idx_itinerary_user_date', 'user_profile_id', 'start_date'),
        Index('idx_itinerary_status', 'status'),
    )

    def __repr__(self):
        return f"<Itinerary(id={self.id}, user={self.user_profile_id}, destination={self.destination_id})>"

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "user_profile_id": self.user_profile_id,
            "destination_id": self.destination_id,
            "name": self.name,
            "description": self.description,
            "route_data": self.route_data,
            "total_duration": self.total_duration,
            "total_cost": float(self.total_cost) if self.total_cost else None,
            "total_distance": float(self.total_distance) if self.total_distance else None,
            "optimization_score": float(self.optimization_score) if self.optimization_score else None,
            "algorithms_used": self.algorithms_used,
            "status": self.status,
            "user_rating": self.user_rating,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ItineraryAttraction(Base):
    """
    Tabla de relación muchos-a-muchos entre itinerarios y atracciones
    (opcional, para consultas más eficientes)
    """
    __tablename__ = "itinerary_attractions"

    id = Column(Integer, primary_key=True, index=True)
    
    itinerary_id = Column(
        Integer,
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    attraction_id = Column(
        Integer,
        ForeignKey("attractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Orden en el itinerario
    visit_order = Column(Integer, nullable=False)
    
    # Tiempos planificados
    planned_arrival = Column(DateTime(timezone=True))
    planned_departure = Column(DateTime(timezone=True))
    
    # Tiempos reales (si el usuario lo completa)
    actual_arrival = Column(DateTime(timezone=True))
    actual_departure = Column(DateTime(timezone=True))
    
    # Rating específico de esta visita
    visit_rating = Column(Integer)  # 1-5
    visit_notes = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    itinerary = relationship("Itinerary", backref="attraction_visits")
    attraction = relationship("Attraction", backref="itinerary_visits")

    # Índices
    __table_args__ = (
        Index('idx_itinerary_attraction', 'itinerary_id', 'attraction_id', unique=True),
        Index('idx_visit_order', 'itinerary_id', 'visit_order'),
    )

    def __repr__(self):
        return (
            f"<ItineraryAttraction("
            f"itinerary={self.itinerary_id}, "
            f"attraction={self.attraction_id}, "
            f"order={self.visit_order})>"
        )