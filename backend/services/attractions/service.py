# backend/services/attractions/service.py
"""
Servicio CRUD para gestionar atracciones turísticas
Incluye búsquedas geoespaciales con PostGIS
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, cast
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint # type: ignore
from geoalchemy2.elements import WKTElement # type: ignore
from fastapi import HTTPException, status
from geoalchemy2 import Geography as GeoType # type: ignore        

from shared.database.models import Attraction, Destination
from shared.schemas.attraction import (
    AttractionCreate,
    AttractionUpdate,
    AttractionRead,
    AttractionSearchParams,
    AttractionWithDistance
)
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class AttractionService:
    """Servicio para operaciones CRUD y búsqueda de atracciones"""
    
    @staticmethod
    def create(db: Session, data: AttractionCreate) -> Attraction:
        """
        Crear una nueva atracción
        
        Args:
            db: Sesión de base de datos
            data: Datos de la atracción a crear
            
        Returns:
            Attraction: Atracción creada
        """
        try:
            # Verificar que el destino existe
            destination = db.query(Destination).filter(
                Destination.id == data.destination_id
            ).first()
            
            if not destination:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Destino con ID {data.destination_id} no encontrado"
                )
            
            # Convertir location dict a formato WKT para PostGIS
            lat = data.location.get('lat')
            lon = data.location.get('lon')
            
            if lat is None or lon is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="location debe contener 'lat' y 'lon'"
                )
            
            # Validar rangos de coordenadas
            if not (-90 <= lat <= 90):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="lat debe estar entre -90 y 90"
                )
            
            if not (-180 <= lon <= 180):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="lon debe estar entre -180 y 180"
                )
            
            # Crear el objeto Attraction
            attraction_data = data.model_dump(exclude={'location'})
            attraction = Attraction(**attraction_data)
            
            # Asignar la ubicación en formato WKT (Geography usa lon, lat)
            attraction.location = f"POINT({lon} {lat})"
            
            db.add(attraction)
            db.commit()
            db.refresh(attraction)
            
            logger.info(f"Atracción creada: {attraction.name} (ID: {attraction.id})")
            return attraction
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error al crear atracción: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear atracción: {str(e)}"
            )
    
    @staticmethod
    def get(db: Session, attraction_id: int) -> Optional[Attraction]:
        """Obtener una atracción por ID"""
        return db.query(Attraction).filter(Attraction.id == attraction_id).first()
    
    @staticmethod
    def get_or_404(db: Session, attraction_id: int) -> Attraction:
        """Obtener una atracción por ID o lanzar 404"""
        attraction = AttractionService.get(db, attraction_id)
        if not attraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Atracción con ID {attraction_id} no encontrada"
            )
        return attraction
    
    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        destination_id: Optional[int] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        min_rating: Optional[float] = None,
        verified_only: bool = False
    ) -> Tuple[List[Attraction], int]:
        """
        Obtener lista de atracciones con filtros y paginación
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar
            limit: Número máximo de registros
            destination_id: Filtrar por destino (opcional)
            category: Filtrar por categoría (opcional)
            min_rating: Rating mínimo (opcional)
            verified_only: Solo atracciones verificadas (opcional)
            
        Returns:
            Tuple: (lista de atracciones, total de registros)
        """
        query = db.query(Attraction)
        
        # Aplicar filtros
        if destination_id:
            query = query.filter(Attraction.destination_id == destination_id)
        
        if category:
            query = query.filter(Attraction.category == category.lower())

        if search:
            query = query.filter(Attraction.name.ilike(f"%{search}%"))
        
        if min_rating:
            query = query.filter(Attraction.rating >= min_rating)
        
        if verified_only:
            query = query.filter(Attraction.verified == True)
        
        # Contar total
        total = query.count()
        
        # Ordenar por popularidad y aplicar paginación
        attractions = query.order_by(
            Attraction.popularity_score.desc()
        ).offset(skip).limit(limit).all()
        
        return attractions, total
    
    @staticmethod
    def search(db: Session, params: AttractionSearchParams) -> Tuple[List[Attraction], int]:
        """
        Búsqueda avanzada de atracciones con múltiples filtros
        
        Args:
            db: Sesión de base de datos
            params: Parámetros de búsqueda (sin geolocalización)
            
        Returns:
            Tuple: (lista de atracciones, total)
        """
        query = db.query(Attraction)
        
        # Filtro por categoría
        if params.category:
            query = query.filter(Attraction.category == params.category.lower())
        
        # Filtro por subcategoría
        if params.subcategory:
            query = query.filter(Attraction.subcategory == params.subcategory.lower())
        
        # Filtro por rating mínimo
        if params.min_rating:
            query = query.filter(Attraction.rating >= params.min_rating)
        
        # Filtro por rango de precio
        if params.price_range:
            query = query.filter(Attraction.price_range == params.price_range.lower())
        
        # Solo verificadas
        if params.verified_only:
            query = query.filter(Attraction.verified == True)
        
        # Filtro por tags (búsqueda en JSONB)
        if params.tags:
            for tag in params.tags:
                query = query.filter(
                    Attraction.tags.contains([tag])
                )
        
        total = query.count()
        
        # Ordenar por popularidad
        attractions = query.order_by(
            Attraction.popularity_score.desc()
        ).all()
        
        return attractions, total
    
    @staticmethod
    def search_nearby(
        db: Session,
        lat: float,
        lon: float,
        radius_km: float = 5.0,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        """
        Buscar atracciones cercanas a un punto geográfico
        
        Args:
            db: Sesión de base de datos
            lat: Latitud del punto de referencia
            lon: Longitud del punto de referencia
            radius_km: Radio de búsqueda en kilómetros
            category: Filtrar por categoría (opcional)
            limit: Número máximo de resultados
            
        Returns:
            List[dict]: Lista de atracciones con distancia calculada
        """        
        # Crear punto de referencia (Geography espera lon, lat)
        reference_point = WKTElement(f'POINT({lon} {lat})', srid=4326)
        
        # Construir query con ST_Distance usando cast explícito
        query = db.query(
            Attraction,
            ST_Distance(
                cast(Attraction.location, GeoType),
                cast(reference_point, GeoType)
            ).label('distance')
        )
        
        # Filtrar por radio (convertir km a metros)
        radius_meters = radius_km * 1000
        query = query.filter(
            ST_DWithin(
                cast(Attraction.location, GeoType),
                cast(reference_point, GeoType),
                radius_meters
            )
        )
        
        # Filtrar por categoría si se especifica
        if category:
            query = query.filter(Attraction.category == category.lower())
        
        # Ordenar por distancia y limitar resultados
        results = query.order_by('distance').limit(limit).all()
        
        # Formatear resultados
        nearby_attractions = []
        for attraction, distance in results:
            distance_meters = float(distance)
            
            attraction_dict = {
                **attraction.__dict__,
                'distance_meters': round(distance_meters, 2),
                'travel_time_minutes': AttractionService._estimate_travel_time(distance_meters)
            }
            # Eliminar atributos internos de SQLAlchemy
            attraction_dict.pop('_sa_instance_state', None)
            nearby_attractions.append(attraction_dict)
        
        logger.info(f"Búsqueda cercana: encontradas {len(nearby_attractions)} atracciones en {radius_km}km")
        return nearby_attractions
        
    @staticmethod
    def _estimate_travel_time(distance_meters: float) -> int:
        """
        Estimar tiempo de viaje en minutos basado en distancia
        Asume velocidad promedio de caminata: 5 km/h
        
        Args:
            distance_meters: Distancia en metros
            
        Returns:
            int: Tiempo estimado en minutos
        """
        walking_speed_kmh = 5.0
        distance_km = distance_meters / 1000
        time_hours = distance_km / walking_speed_kmh
        time_minutes = int(time_hours * 60)
        return max(time_minutes, 1)  # Mínimo 1 minuto
    
    @staticmethod
    def get_by_category(
        db: Session,
        category: str,
        destination_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Attraction]:
        """
        Obtener atracciones por categoría
        
        Args:
            db: Sesión de base de datos
            category: Categoría de atracción
            destination_id: Filtrar por destino (opcional)
            limit: Número máximo de resultados
            
        Returns:
            List[Attraction]: Lista de atracciones
        """
        query = db.query(Attraction).filter(
            Attraction.category == category.lower()
        )
        
        if destination_id:
            query = query.filter(Attraction.destination_id == destination_id)
        
        return query.order_by(
            Attraction.rating.desc()
        ).limit(limit).all()
    
    @staticmethod
    def update(
        db: Session,
        attraction_id: int,
        data: AttractionUpdate
    ) -> Attraction:
        """
        Actualizar una atracción existente
        
        Args:
            db: Sesión de base de datos
            attraction_id: ID de la atracción a actualizar
            data: Datos a actualizar
            
        Returns:
            Attraction: Atracción actualizada
        """
        attraction = AttractionService.get_or_404(db, attraction_id)
        
        try:
            # Actualizar solo los campos proporcionados
            update_data = data.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                setattr(attraction, field, value)
            
            db.commit()
            db.refresh(attraction)
            
            logger.info(f"Atracción actualizada: {attraction.name} (ID: {attraction.id})")
            return attraction
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al actualizar atracción {attraction_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar atracción: {str(e)}"
            )
    
    @staticmethod
    def delete(db: Session, attraction_id: int) -> dict:
        """
        Eliminar una atracción
        
        Args:
            db: Sesión de base de datos
            attraction_id: ID de la atracción a eliminar
            
        Returns:
            dict: Mensaje de confirmación
        """
        attraction = AttractionService.get_or_404(db, attraction_id)
        
        try:
            attraction_name = attraction.name
            db.delete(attraction)
            db.commit()
            
            logger.info(f"Atracción eliminada: {attraction_name} (ID: {attraction_id})")
            return {"message": f"Atracción '{attraction_name}' eliminada exitosamente"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al eliminar atracción {attraction_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar atracción: {str(e)}"
            )
    
    @staticmethod
    def get_statistics(db: Session, attraction_id: int) -> dict:
        """
        Obtener estadísticas de una atracción
        
        Args:
            db: Sesión de base de datos
            attraction_id: ID de la atracción
            
        Returns:
            dict: Estadísticas de la atracción
        """
        from shared.database.models import Review, AttractionRating
        
        attraction = AttractionService.get_or_404(db, attraction_id)
        
        # Calcular estadísticas de reviews
        total_reviews = db.query(Review).filter(
            Review.attraction_id == attraction_id
        ).count()
        
        avg_sentiment = db.query(
            func.avg(Review.sentiment_score)
        ).filter(
            Review.attraction_id == attraction_id,
            Review.sentiment_score.isnot(None)
        ).scalar()
        
        # Calcular estadísticas de ratings
        total_ratings = db.query(AttractionRating).filter(
            AttractionRating.attraction_id == attraction_id
        ).count()
        
        avg_user_rating = db.query(
            func.avg(AttractionRating.rating)
        ).filter(
            AttractionRating.attraction_id == attraction_id
        ).scalar()
        
        return {
            "attraction_id": attraction_id,
            "name": attraction.name,
            "total_reviews": total_reviews,
            "avg_sentiment_score": float(avg_sentiment) if avg_sentiment else None,
            "total_user_ratings": total_ratings,
            "avg_user_rating": float(avg_user_rating) if avg_user_rating else None,
            "popularity_score": float(attraction.popularity_score) if attraction.popularity_score else None # type: ignore
        }