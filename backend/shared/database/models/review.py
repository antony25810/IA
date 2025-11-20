# shared/database/models/review.py
"""
Modelos para reseñas y ratings
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    Numeric, ForeignKey, func, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from shared.database.base import Base


class Review(Base):
    """
    Tabla de reseñas de atracciones
    Para análisis de sentimiento y validación de datos
    """
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    
    attraction_id = Column(
        Integer,
        ForeignKey("attractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Fuente de la reseña
    source = Column(String(100), nullable=False)
    # Valores: 'google_places', 'tripadvisor', 'yelp', 'internal'
    
    source_id = Column(String(255))  # ID externo de la reseña
    
    # Contenido
    text = Column(Text, nullable=False)
    rating = Column(Integer)  # Rating original (1-5 típicamente)
    
    # Análisis de sentimiento (calculado por ML)
    sentiment_score = Column(Numeric(3, 2))  # -1.00 a 1.00
    sentiment_label = Column(String(20))  # 'positive', 'negative', 'neutral'
    
    # Metadata
    language = Column(String(10), default='es')
    author = Column(String(255))
    
    # Fechas
    review_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    attraction = relationship("Attraction", backref="reviews")

    # Constraints
    __table_args__ = (
        CheckConstraint('sentiment_score >= -1.0 AND sentiment_score <= 1.0', name='check_sentiment_range'),
        Index('idx_review_attraction_source', 'attraction_id', 'source'),
        Index('idx_review_sentiment', 'sentiment_label'),
    )

    def __repr__(self):
        return f"<Review(id={self.id}, attraction={self.attraction_id}, source='{self.source}')>"

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "attraction_id": self.attraction_id,
            "source": self.source,
            "text": self.text,
            "rating": self.rating,
            "sentiment_score": float(self.sentiment_score) if self.sentiment_score else None,
            "sentiment_label": self.sentiment_label,
            "language": self.language,
            "author": self.author,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AttractionRating(Base):
    """
    Tabla de ratings directos de usuarios
    Para entrenar el modelo de ML
    """
    __tablename__ = "attraction_ratings"

    id = Column(Integer, primary_key=True, index=True)
    
    user_profile_id = Column(
        Integer,
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    attraction_id = Column(
        Integer,
        ForeignKey("attractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Rating del usuario
    rating = Column(Integer, nullable=False)  # 1-5
    
    # Fecha de visita
    visit_date = Column(DateTime(timezone=True))
    
    # Feedback textual (opcional)
    feedback = Column(Text)
    
    # Contexto de la visita
    visit_context = Column(String(50))
    # Valores: 'solo', 'pareja', 'familia', 'amigos', 'trabajo'
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    user_profile = relationship("UserProfile", backref="ratings")
    attraction = relationship("Attraction", backref="user_ratings")

    # Constraints
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
        Index('idx_rating_user_attraction', 'user_profile_id', 'attraction_id'),
        Index('idx_rating_attraction_date', 'attraction_id', 'visit_date'),
    )

    def __repr__(self):
        return (
            f"<AttractionRating("
            f"user={self.user_profile_id}, "
            f"attraction={self.attraction_id}, "
            f"rating={self.rating})>"
        )

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            "id": self.id,
            "user_profile_id": self.user_profile_id,
            "attraction_id": self.attraction_id,
            "rating": self.rating,
            "visit_date": self.visit_date.isoformat() if self.visit_date else None,
            "feedback": self.feedback,
            "visit_context": self.visit_context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }