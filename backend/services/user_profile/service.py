# backend/services/user_profiles/service.py
"""
Servicio CRUD para gestión de perfiles de usuario
Incluye preferencias para personalización de recomendaciones
"""
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from uuid import UUID

from shared.database.models.attraction import Attraction
from shared.database.models import UserProfile, AttractionRating, Itinerary
from shared.schemas.user_profile import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileRead,
    PreferencesSchema
)
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class UserProfileService:
    """Servicio para operaciones CRUD de perfiles de usuario"""
    
    @staticmethod
    def create(db: Session, data: UserProfileCreate) -> UserProfile:
        """
        Crear un nuevo perfil de usuario
        
        Args:
            db: Sesión de base de datos
            data: Datos del perfil a crear
            
        Returns:
            UserProfile: Perfil creado
        """
        try:
            # Verificar si el email ya existe
            if data.email:
                existing = db.query(UserProfile).filter(
                    UserProfile.email == data.email
                ).first()
                
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Ya existe un perfil con el email {data.email}"
                    )
            
            # Convertir preferences a dict
            profile_data = data.model_dump()
            if isinstance(profile_data.get('preferences'), PreferencesSchema):
                profile_data['preferences'] = profile_data['preferences'].model_dump()
            
            # Crear el perfil
            profile = UserProfile(**profile_data)
            
            db.add(profile)
            db.commit()
            db.refresh(profile)
            
            logger.info(f"Perfil de usuario creado: {profile.name} (ID: {profile.id})")
            return profile
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error al crear perfil de usuario: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear perfil de usuario: {str(e)}"
            )
    
    @staticmethod
    def get(db: Session, profile_id: int) -> Optional[UserProfile]:
        """Obtener un perfil por ID"""
        return db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    
    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> Optional[UserProfile]:
        """Obtener un perfil por user_id (UUID)"""
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[UserProfile]:
        """Obtener un perfil por email"""
        return db.query(UserProfile).filter(UserProfile.email == email).first()
    
    @staticmethod
    def get_or_404(db: Session, profile_id: int) -> UserProfile:
        """Obtener un perfil por ID o lanzar 404"""
        profile = UserProfileService.get(db, profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Perfil de usuario con ID {profile_id} no encontrado"
            )
        return profile
    
    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        budget_range: Optional[str] = None
    ) -> Tuple[List[UserProfile], int]:
        """
        Obtener lista de perfiles con filtros y paginación
        
        Args:
            db: Sesión de base de datos
            skip: Registros a saltar
            limit: Número máximo de registros
            budget_range: Filtrar por rango de presupuesto
            
        Returns:
            Tuple: (lista de perfiles, total)
        """
        query = db.query(UserProfile)
        
        # Filtrar por budget_range
        if budget_range:
            query = query.filter(UserProfile.budget_range == budget_range.lower())
        
        # Contar total
        total = query.count()
        
        # Aplicar paginación
        profiles = query.order_by(
            UserProfile.created_at.desc()
        ).offset(skip).limit(limit).all()
        
        return profiles, total
    
    @staticmethod
    def update(
        db: Session,
        profile_id: int,
        data: UserProfileUpdate
    ) -> UserProfile:
        """
        Actualizar un perfil existente
        
        Args:
            db: Sesión de base de datos
            profile_id: ID del perfil
            data: Datos a actualizar
            
        Returns:
            UserProfile: Perfil actualizado
        """
        profile = UserProfileService.get_or_404(db, profile_id)
        
        try:
            update_data = data.model_dump(exclude_unset=True)
            
            # Verificar email único si se está actualizando
            if 'email' in update_data and update_data['email']:
                existing = db.query(UserProfile).filter(
                    UserProfile.email == update_data['email'],
                    UserProfile.id != profile_id
                ).first()
                
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"El email {update_data['email']} ya está en uso"
                    )
            
            for field, value in update_data.items():
                setattr(profile, field, value)
            
            db.commit()
            db.refresh(profile)
            
            logger.info(f"Perfil actualizado: {profile.name} (ID: {profile.id})")
            return profile
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error al actualizar perfil {profile_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar perfil: {str(e)}"
            )
    
    @staticmethod
    def delete(db: Session, profile_id: int) -> dict:
        """
        Eliminar un perfil
        
        Args:
            db: Sesión de base de datos
            profile_id: ID del perfil
            
        Returns:
            dict: Mensaje de confirmación
        """
        profile = UserProfileService.get_or_404(db, profile_id)
        
        try:
            profile_name = profile.name
            db.delete(profile)
            db.commit()
            
            logger.info(f"Perfil eliminado: {profile_name} (ID: {profile_id})")
            return {"message": f"Perfil '{profile_name}' eliminado exitosamente"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al eliminar perfil {profile_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar perfil: {str(e)}"
            )
    
    @staticmethod
    def get_with_statistics(db: Session, profile_id: int) -> Dict:
        """
        Obtener perfil con estadísticas de actividad
        
        Args:
            db: Sesión de base de datos
            profile_id: ID del perfil
            
        Returns:
            Dict: Perfil con estadísticas
        """
        profile = UserProfileService.get_or_404(db, profile_id)
        
        # Calcular estadísticas
        total_itineraries = db.query(Itinerary).filter(
            Itinerary.user_profile_id == profile_id
        ).count()
        
        total_ratings = db.query(AttractionRating).filter(
            AttractionRating.user_profile_id == profile_id
        ).count()
        
        avg_rating_given = db.query(
            func.avg(AttractionRating.rating)
        ).filter(
            AttractionRating.user_profile_id == profile_id
        ).scalar()
        
        # Itinerarios completados
        completed_itineraries = db.query(Itinerary).filter(
            Itinerary.user_profile_id == profile_id,
            Itinerary.status == 'completed'
        ).count()
        
        # Categorías más visitadas (basado en ratings)
        top_categories = db.query(
            func.count(AttractionRating.id).label('count')
        ).join(
            AttractionRating.attraction
        ).filter(
            AttractionRating.user_profile_id == profile_id
        ).group_by(
            'category'
        ).order_by(
            func.count(AttractionRating.id).desc()
        ).limit(5).all()
        
        return {
            **profile.__dict__,
            "total_itineraries": total_itineraries,
            "completed_itineraries": completed_itineraries,
            "total_ratings": total_ratings,
            "avg_rating_given": float(avg_rating_given) if avg_rating_given else None,
            "_sa_instance_state": None  # Eliminar atributo interno
        }
    
    @staticmethod
    def update_computed_profile(
        db: Session,
        profile_id: int,
        computed_data: Dict
    ) -> UserProfile:
        """
        Actualizar el perfil computado (usado por ML)
        
        Args:
            db: Sesión de base de datos
            profile_id: ID del perfil
            computed_data: Datos computados por algoritmos ML
            
        Returns:
            UserProfile: Perfil actualizado
        """
        profile = UserProfileService.get_or_404(db, profile_id)
        
        try:
            profile.computed_profile = computed_data
            db.commit()
            db.refresh(profile)
            
            logger.info(f"Perfil computado actualizado para usuario {profile_id}")
            return profile
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al actualizar perfil computado {profile_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar perfil computado: {str(e)}"
            )
    
    @staticmethod
    def get_recommendations(
        db: Session,
        profile_id: int,
        destination_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Obtener recomendaciones personalizadas basadas en preferencias
        
        Args:
            db: Sesión de base de datos
            profile_id: ID del perfil
            destination_id: Filtrar por destino (opcional)
            limit: Número máximo de recomendaciones
            
        Returns:
            List[Dict]: Lista de atracciones recomendadas
        """
        from shared.database.models import Attraction
        
        profile = UserProfileService.get_or_404(db, profile_id)
        
        # Extraer intereses de las preferencias
        preferences = profile.preferences or {}
        interests = preferences.get('interests', [])
        
        if not interests:
            # Si no hay intereses, devolver las más populares
            query = db.query(Attraction)
            if destination_id:
                query = query.filter(Attraction.destination_id == destination_id)
            
            attractions = query.order_by(
                Attraction.popularity_score.desc()
            ).limit(limit).all()
            
            return [
                {
                    **attr.__dict__,
                    'recommendation_score': float(attr.popularity_score) if attr.popularity_score else 0.0,
                    'match_reason': 'popular'
                }
                for attr in attractions
            ]
        
        # Buscar atracciones que coincidan con los intereses
        query = db.query(Attraction)
        
        if destination_id:
            query = query.filter(Attraction.destination_id == destination_id)
        
        # Filtrar por categorías de interés
        interest_categories = []
        category_map = {
            'historia': 'historico',
            'arte': 'cultural',
            'museos': 'cultural',
            'gastronomia': 'gastronomia',
            'comida': 'gastronomia',
            'naturaleza': 'naturaleza',
            'aventura': 'aventura',
            'deportes': 'deportivo',
            'compras': 'compras',
            'entretenimiento': 'entretenimiento'
        }
        
        for interest in interests:
            category = category_map.get(interest.lower())
            if category and category not in interest_categories:
                interest_categories.append(category)
        
        if interest_categories:
            query = query.filter(Attraction.category.in_(interest_categories))
        
        price_map = {
            'bajo': ['gratis', 'bajo'],
            'medio': ['gratis', 'bajo', 'medio'],
            'alto': ['gratis', 'bajo', 'medio', 'alto'],
            'lujo': ['gratis', 'bajo', 'medio', 'alto']
        }
        
        # Filtrar por budget si está disponible
        budget_range = profile.budget_range
        if budget_range:
            allowed_prices = price_map.get(budget_range.lower(), [])
            if allowed_prices:
                query = query.filter(Attraction.price_range.in_(allowed_prices))
        
        
        # Ordenar por rating y popularidad
        attractions = query.order_by(
            Attraction.rating.desc(),
            Attraction.popularity_score.desc()
        ).limit(limit).all()
        
        # Calcular score de recomendación
        recommendations = []
        for attr in attractions:
            score = 0.0
            reasons = []
            
            # Score por categoría de interés
            if attr.category in interest_categories:
                score += 50.0
                reasons.append(f"coincide con interés: {attr.category}")
            
            # Score por rating
            if attr.rating:
                score += float(attr.rating) * 10
                reasons.append(f"rating: {attr.rating}")
            
            # Score por popularidad
            if attr.popularity_score:
                score += float(attr.popularity_score) * 0.3
            
            # Score por presupuesto
            if budget_range and attr.price_range:
                if attr.price_range.lower() in price_map.get(budget_range.lower(), []):
                    score += 10.0
                    reasons.append("dentro de presupuesto")
            
            recommendations.append({
                **attr.__dict__,
                'recommendation_score': round(score, 2),
                'match_reasons': reasons,
                '_sa_instance_state': None
            })
        
        # Ordenar por score
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        logger.info(f"Generadas {len(recommendations)} recomendaciones para perfil {profile_id}")
        return recommendations
    
    @staticmethod
    def add_historical_rating(
        db: Session,
        profile_id: int,
        attraction_id: int,
        rating: int
    ) -> UserProfile:
        """
        Agregar rating histórico al perfil
        
        Args:
            db: Sesión de base de datos
            profile_id: ID del perfil
            attraction_id: ID de la atracción
            rating: Rating dado (1-5)
            
        Returns:
            UserProfile: Perfil actualizado
        """
        profile = UserProfileService.get_or_404(db, profile_id)
        
        try:
            historical_ratings = profile.historical_ratings or {}
            historical_ratings[str(attraction_id)] = rating
            
            profile.historical_ratings = historical_ratings
            db.commit()
            db.refresh(profile)
            
            logger.info(f"Rating histórico agregado para perfil {profile_id}")
            return profile
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al agregar rating histórico: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al agregar rating histórico: {str(e)}"
            )