# backend/services/user_profiles/service.py
"""
Servicio CRUD para gestión de perfiles de usuario
Incluye preferencias para personalización de recomendaciones
"""
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from shared.database.models.attraction import Attraction
from shared.database.models import UserProfile, AttractionRating, Itinerary
from shared.database.models import User 
from shared.schemas.user_profile import (
    UserProfileCreate,
    UserProfileUpdate,
    PreferencesSchema
)
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class UserProfileService:
    """Servicio para operaciones CRUD de perfiles de usuario"""
    
    @staticmethod
    def create(db: Session, user_id: int, data: UserProfileCreate) -> UserProfile:
        """
        Crear un nuevo perfil de usuario vinculado a un User ID
        
        Args:
            db: Sesión de base de datos
            user_id: ID del usuario (tabla users)
            data: Datos del perfil a crear
            
        Returns:
            UserProfile: Perfil creado
        """
        try:
            # 1. Verificar que el usuario no tenga ya un perfil (Relación 1 a 1)
            existing_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if existing_profile:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"El usuario con ID {user_id} ya tiene un perfil creado."
                )

            # 2. Verificar si el email opcional ya existe en otro perfil
            if data.email:
                existing_email = db.query(UserProfile).filter(
                    UserProfile.email == data.email
                ).first()
                
                if existing_email:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Ya existe un perfil asociado al email {data.email}"
                    )
            
            # Convertir preferences a dict si es un objeto Pydantic
            profile_data = data.model_dump()
            if isinstance(profile_data.get('preferences'), PreferencesSchema):
                profile_data['preferences'] = profile_data['preferences'].model_dump()
            
            # 3. Crear el perfil inyectando el user_id
            profile = UserProfile(user_id=user_id, **profile_data)
            
            db.add(profile)
            db.commit()
            db.refresh(profile)
            
            logger.info(f"Perfil creado para User ID {user_id}: {profile.name} (ID: {profile.id})")
            return profile
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            # Capturar errores de integridad de FK (si el usuario no existe)
            if "foreign key constraint" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El usuario con ID {user_id} no existe."
                )
            
            logger.error(f"Error al crear perfil de usuario: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error interno al crear perfil: {str(e)}"
            )
    
    @staticmethod
    def get(db: Session, profile_id: int) -> Optional[UserProfile]:
        """Obtener un perfil por ID"""
        return db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    
    @staticmethod
    def get_by_user_id(db: Session, user_id: int) -> Optional[UserProfile]:
        """Obtener un perfil por user_id (Integer)"""
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
        """
        query = db.query(UserProfile)
        
        if budget_range:
            query = query.filter(UserProfile.budget_range == budget_range.lower())
        
        total = query.count()
        
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
        """
        profile = UserProfileService.get_or_404(db, profile_id)
        
        try:
            update_data = data.model_dump(exclude_unset=True)
            
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
        """
        profile = UserProfileService.get_or_404(db, profile_id)
        
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
        
        completed_itineraries = db.query(Itinerary).filter(
            Itinerary.user_profile_id == profile_id,
            Itinerary.status == 'completed'
        ).count()
        
        
        return {
            **profile.__dict__,
            "total_itineraries": total_itineraries,
            "completed_itineraries": completed_itineraries,
            "total_ratings": total_ratings,
            "avg_rating_given": float(avg_rating_given) if avg_rating_given else None,
            "_sa_instance_state": None
        }
    
    @staticmethod
    def get_recommendations(
        db: Session,
        profile_id: int,
        destination_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Obtener recomendaciones personalizadas basadas en preferencias
        """
        profile = UserProfileService.get_or_404(db, profile_id)
        preferences = profile.preferences or {}
        interests = preferences.get('interests', [])
        
        # Lógica de fallback si no hay intereses
        if not interests:
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
                    'match_reason': 'popular',
                     '_sa_instance_state': None
                }
                for attr in attractions
            ]
        
        query = db.query(Attraction)
        if destination_id:
            query = query.filter(Attraction.destination_id == destination_id)
        
        # Mapeo simple de intereses
        interest_categories = []
        category_map = {
            'historia': 'historico', 'arte': 'cultural', 'museos': 'cultural',
            'gastronomia': 'gastronomia', 'comida': 'gastronomia',
            'naturaleza': 'naturaleza', 'aventura': 'aventura',
            'deportes': 'deportivo', 'compras': 'compras'
        }
        
        for interest in interests:
            cat = category_map.get(interest.lower())
            if cat and cat not in interest_categories:
                interest_categories.append(cat)
        
        if interest_categories:
            query = query.filter(Attraction.category.in_(interest_categories))
        
        # Filtrar por presupuesto
        price_map = {
            'bajo': ['gratis', 'bajo'],
            'medio': ['gratis', 'bajo', 'medio'],
            'alto': ['gratis', 'bajo', 'medio', 'alto'],
            'lujo': ['gratis', 'bajo', 'medio', 'alto', 'lujo']
        }
        
        budget_range = profile.budget_range
        if budget_range and budget_range.lower() in price_map:
             allowed = price_map[budget_range.lower()]
             # Solo filtrar si tenemos datos de precio en las atracciones
             query = query.filter(Attraction.price_range.in_(allowed))
             pass 

        attractions = query.order_by(
            Attraction.rating.desc(),
            Attraction.popularity_score.desc()
        ).limit(limit).all()
        
        recommendations = []
        for attr in attractions:
            score = 0.0
            reasons = []
            
            if attr.category in interest_categories:
                score += 50.0
                reasons.append(f"Interés: {attr.category}")
            
            if attr.rating:
                score += float(attr.rating) * 10
            
            if budget_range and attr.price_range:
                 if attr.price_range.lower() in price_map.get(budget_range.lower(), []):
                     score += 10
                     reasons.append("En presupuesto")

            recommendations.append({
                **attr.__dict__,
                'recommendation_score': round(score, 2),
                'match_reasons': reasons,
                '_sa_instance_state': None
            })
        
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return recommendations

    @staticmethod
    def update_computed_profile(
        db: Session,
        profile_id: int,
        computed_data: Dict
    ) -> UserProfile:
        """Actualizar el perfil computado (usado por ML)"""
        profile = UserProfileService.get_or_404(db, profile_id)
        try:
            profile.computed_profile = computed_data
            db.commit()
            db.refresh(profile)
            return profile
        except Exception as e:
            db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    def add_historical_rating(
        db: Session,
        profile_id: int,
        attraction_id: int,
        rating: int
    ) -> UserProfile:
        """Agregar rating histórico al perfil"""
        profile = UserProfileService.get_or_404(db, profile_id)
        try:
            historical_ratings = dict(profile.historical_ratings or {})
            historical_ratings[str(attraction_id)] = rating
            profile.historical_ratings = historical_ratings
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(profile, "historical_ratings")
            
            db.commit()
            db.refresh(profile)
            return profile
        except Exception as e:
            db.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
