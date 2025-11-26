from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from shared.database.base import Base

class User(Base):
    """
    Tabla de credenciales de usuario (Login)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True) 
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relación 1-a-1 con el Perfil
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
            return f"<User(id={self.id}, email={self.email})>"