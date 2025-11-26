# shared/database/models/user_profile.py
"""
Modelo para perfiles de usuario
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, func, Index, ForeignKey
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from shared.database.base import Base


class UserProfile(Base):
    """
    Tabla de perfiles de usuario
    Almacena preferencias y restricciones para la personalización
    """
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        unique=True, 
        nullable=False, 
        index=True
    )
    
    # Información básica (opcional)
    name = Column(String(255))
    email = Column(String(255)) # Ya no es unique aquí estricto, depende del User, pero sirve de contacto
    
    # Preferencias de turismo
    preferences = Column(JSONB, nullable=False, default={})
    
    # Restricciones presupuestarias
    budget_range = Column(String(20))  # 'bajo', 'medio', 'alto', 'lujo'
    budget_min = Column(Integer)  # Presupuesto mínimo por día
    budget_max = Column(Integer)  # Presupuesto máximo por día
    
    # Restricciones de movilidad
    mobility_constraints = Column(JSONB, default={})
    
    # Historial de ratings (para el modelo ML)
    historical_ratings = Column(JSONB, default=[])
    
    # Perfil calculado por el sistema de reglas
    computed_profile = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="profile")

    itineraries = relationship(
        "Itinerary",
        back_populates="user_profile",
        cascade="all, delete-orphan"
    )

    # Índices
    __table_args__ = (
        Index('idx_user_preferences', 'preferences', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "preferences": self.preferences,
            "budget_range": self.budget_range,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "mobility_constraints": self.mobility_constraints,
            "computed_profile": self.computed_profile,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }