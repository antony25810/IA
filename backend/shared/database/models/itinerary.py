# shared/database/models/itinerary.py
"""
Modelos para itinerarios multi-día (VERSIÓN MEJORADA)
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean,
    Numeric, ForeignKey, func, Index, Text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from shared.database.base import Base


class Itinerary(Base):
    """
    Tabla principal de itinerarios multi-día
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
    
    # Punto de partida/retorno (hotel o centro de ciudad)
    start_point_id = Column(
        Integer,
        ForeignKey("attractions.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID de atracción usada como punto de inicio/fin (hotel o centro)"
    )
    
    # Metadatos
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Configuración del viaje
    num_days = Column(Integer, nullable=False, default=1)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Calculado automáticamente
    
    # Parámetros usados para generar (para regenerar si es necesario)
    generation_params = Column(JSONB, nullable=True)
    # Ejemplo:
    # {
    #   "optimization_mode": "balanced",
    #   "max_radius_km": 10.0,
    #   "max_candidates": 50,
    #   "bfs_max_depth": 5,
    #   "transport_mode": null
    # }
    
    # Métricas globales (sumatoria de todos los días)
    total_duration_minutes = Column(Integer, nullable=True)
    total_cost = Column(Numeric(10, 2), nullable=True)
    total_distance_meters = Column(Numeric(12, 2), nullable=True)
    total_attractions = Column(Integer, nullable=True)
    
    # Score promedio de optimización
    average_optimization_score = Column(Numeric(5, 2), nullable=True)
    
    # Algoritmos utilizados (metadata técnica)
    algorithms_used = Column(JSONB, nullable=True)
    # {"search": "BFS", "routing": "A*", "clustering": "KMeans"}
    
    # Estado del itinerario
    status = Column(
        String(50), 
        default='draft',
        nullable=False,
        comment="draft, confirmed, in_progress, completed, cancelled"
    )
    
    # Indica si fue editado manualmente
    manually_edited = Column(Boolean, default=False)
    
    # Feedback del usuario
    user_rating = Column(Integer, nullable=True, comment="1-5 estrellas")
    user_feedback = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    user_profile = relationship("UserProfile", back_populates="itineraries")
    destination = relationship("Destination", back_populates="itineraries")
    start_point = relationship("Attraction", foreign_keys=[start_point_id])
    days = relationship(
        "ItineraryDay", 
        back_populates="itinerary", 
        cascade="all, delete-orphan",
        order_by="ItineraryDay.day_number"
    )
    attraction_visits = relationship(
        "ItineraryAttraction",
        back_populates="itinerary",
        cascade="all, delete-orphan"
    )

    # Índices
    __table_args__ = (
        Index('idx_itinerary_user_date', 'user_profile_id', 'start_date'),
        Index('idx_itinerary_status', 'status'),
        Index('idx_itinerary_destination', 'destination_id', 'start_date'),
    )

    def __repr__(self):
        return f"<Itinerary(id={self.id}, days={self.num_days}, destination={self.destination_id})>"


class ItineraryDay(Base):
    """
    Tabla para días individuales del itinerario
    Facilita consultas y edición por día
    """
    __tablename__ = "itinerary_days"

    id = Column(Integer, primary_key=True, index=True)
    
    itinerary_id = Column(
        Integer,
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    day_number = Column(Integer, nullable=False, comment="1, 2, 3...")
    date = Column(Date, nullable=False)
    
    # ID del cluster (si se usó clustering geográfico)
    cluster_id = Column(Integer, nullable=True)
    
    # Coordenadas del centroide del cluster (para visualización)
    cluster_centroid_lat = Column(Numeric(10, 7), nullable=True)
    cluster_centroid_lon = Column(Numeric(10, 7), nullable=True)
    
    # Datos estructurados del día (JSONB)
    day_data = Column(JSONB, nullable=False)
    # Estructura:
    # {
    #   "attractions": [
    #     {
    #       "attraction_id": 5,
    #       "order": 1,
    #       "arrival_time": "09:00",
    #       "departure_time": "10:30",
    #       "visit_duration_minutes": 90,
    #       "score": 85.5
    #     }
    #   ],
    #   "segments": [
    #     {
    #       "from_attraction_id": 55,
    #       "to_attraction_id": 5,
    #       "distance_meters": 2300,
    #       "travel_time_minutes": 15,
    #       "transport_mode": "walking",
    #       "cost": 0
    #     }
    #   ]
    # }
    
    # Métricas del día
    total_distance_meters = Column(Numeric(10, 2), nullable=True)
    total_time_minutes = Column(Integer, nullable=True)
    total_cost = Column(Numeric(8, 2), nullable=True)
    attractions_count = Column(Integer, nullable=True)
    optimization_score = Column(Numeric(5, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    itinerary = relationship("Itinerary", back_populates="days")
    attractions = relationship(
        "ItineraryAttraction",
        back_populates="day",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_itinerary_day', 'itinerary_id', 'day_number', unique=True),
    )

    def __repr__(self):
        return f"<ItineraryDay(itinerary={self.itinerary_id}, day={self.day_number})>"


class ItineraryAttraction(Base):
    """
    Tabla de relación muchos-a-muchos
    Vincula atracciones con itinerarios y días específicos
    """
    __tablename__ = "itinerary_attractions"

    id = Column(Integer, primary_key=True, index=True)
    
    itinerary_id = Column(
        Integer,
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    day_id = Column(
        Integer,
        ForeignKey("itinerary_days.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    attraction_id = Column(
        Integer,
        ForeignKey("attractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Orden global en todo el itinerario
    visit_order = Column(Integer, nullable=False)
    
    # Orden dentro del día específico
    day_order = Column(Integer, nullable=True)
    
    # Score asignado por el algoritmo de scoring
    attraction_score = Column(Numeric(5, 2), nullable=True)
    
    # Tiempos planificados
    planned_arrival = Column(DateTime(timezone=True), nullable=True)
    planned_departure = Column(DateTime(timezone=True), nullable=True)
    visit_duration_minutes = Column(Integer, nullable=True)
    
    # Tiempos reales (si el usuario completa el viaje)
    actual_arrival = Column(DateTime(timezone=True), nullable=True)
    actual_departure = Column(DateTime(timezone=True), nullable=True)
    
    # Indica si fue añadido manualmente después de la generación
    manually_added = Column(Boolean, default=False)
    
    # Rating y notas del usuario para esta visita específica
    visit_rating = Column(Integer, nullable=True, comment="1-5 estrellas")
    visit_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    itinerary = relationship("Itinerary", back_populates="attraction_visits")
    day = relationship("ItineraryDay", back_populates="attractions")
    attraction = relationship("Attraction")

    __table_args__ = (
        Index('idx_itinerary_day_attr', 'itinerary_id', 'day_id', 'attraction_id'),
        Index('idx_visit_order', 'itinerary_id', 'visit_order'),
    )

    def __repr__(self):
        return (
            f"<ItineraryAttraction("
            f"itinerary={self.itinerary_id}, "
            f"day={self. day_id}, "
            f"attraction={self.attraction_id})>"
        )