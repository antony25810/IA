# backend/services/destinations/service.py
"""
Servicio CRUD para gestionar destinos turísticos
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from shared.database.models import Destination
from shared.schemas.destination import (
    DestinationCreate,
    DestinationUpdate,
    DestinationRead,
    DestinationWithStats
)
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class DestinationService:
    """Servicio para operaciones CRUD de destinos"""
    
    @staticmethod
    def create(db: Session, data: DestinationCreate) -> Destination:
        """
        Crear un nuevo destino
        
        Args:
            db: Sesión de base de datos
            data: Datos del destino a crear
            
        Returns:
            Destination: Destino creado
            
        Raises:
            HTTPException: Si hay error en la creación
        """
        try:
            # Convertir location dict a formato WKT para PostGIS
            lat = data.location.get('lat')
            lon = data.location.get('lon')
            
            if lat is None or lon is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="location debe contener 'lat' y 'lon'"
                )
            
            # Crear el objeto Destination
            destination_data = data.model_dump(exclude={'location'})
            destination = Destination(**destination_data)
            
            # Asignar la ubicación en formato WKT
            destination.location = f"POINT({lon} {lat})"
            
            db.add(destination)
            db.commit()
            db.refresh(destination)
            
            logger.info(f"Destino creado: {destination.name} (ID: {destination.id})")
            return destination
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error al crear destino: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear destino: {str(e)}"
            )
    
    @staticmethod
    def get(db: Session, destination_id: int) -> Optional[Destination]:
        """
        Obtener un destino por ID
        
        Args:
            db: Sesión de base de datos
            destination_id: ID del destino
            
        Returns:
            Optional[Destination]: Destino encontrado o None
        """
        return db.query(Destination).filter(Destination.id == destination_id).first()
    
    @staticmethod
    def get_or_404(db: Session, destination_id: int) -> Destination:
        """
        Obtener un destino por ID o lanzar 404
        
        Args:
            db: Sesión de base de datos
            destination_id: ID del destino
            
        Returns:
            Destination: Destino encontrado
            
        Raises:
            HTTPException: Si el destino no existe
        """
        destination = DestinationService.get(db, destination_id)
        if not destination:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destino con ID {destination_id} no encontrado"
            )
        return destination
    
    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        country: Optional[str] = None,
        search: Optional[str] = None
    ) -> tuple[List[Destination], int]:
        """
        Obtener lista de destinos con filtros y paginación
        
        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar (paginación)
            limit: Número máximo de registros a devolver
            country: Filtrar por país (opcional)
            search: Buscar en nombre o descripción (opcional)
            
        Returns:
            tuple: (lista de destinos, total de registros)
        """
        query = db.query(Destination)
        
        # Aplicar filtros
        if country:
            query = query.filter(Destination.country.ilike(f"%{country}%"))
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Destination.name.ilike(search_pattern)) |
                (Destination.description.ilike(search_pattern))
            )
        
        # Contar total antes de aplicar paginación
        total = query.count()
        
        # Aplicar paginación
        destinations = query.offset(skip).limit(limit).all()
        
        return destinations, total
    
    @staticmethod
    def update(
        db: Session,
        destination_id: int,
        data: DestinationUpdate
    ) -> Destination:
        """
        Actualizar un destino existente
        
        Args:
            db: Sesión de base de datos
            destination_id: ID del destino a actualizar
            data: Datos a actualizar
            
        Returns:
            Destination: Destino actualizado
            
        Raises:
            HTTPException: Si el destino no existe
        """
        destination = DestinationService.get_or_404(db, destination_id)
        
        try:
            # Actualizar solo los campos proporcionados (exclude_unset=True)
            update_data = data.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                setattr(destination, field, value)
            
            db.commit()
            db.refresh(destination)
            
            logger.info(f"Destino actualizado: {destination.name} (ID: {destination.id})")
            return destination
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al actualizar destino {destination_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar destino: {str(e)}"
            )
    
    @staticmethod
    def delete(db: Session, destination_id: int) -> dict:
        """
        Eliminar un destino
        
        Args:
            db: Sesión de base de datos
            destination_id: ID del destino a eliminar
            
        Returns:
            dict: Mensaje de confirmación
            
        Raises:
            HTTPException: Si el destino no existe
        """
        destination = DestinationService.get_or_404(db, destination_id)
        
        try:
            db.delete(destination)
            db.commit()
            
            logger.info(f"Destino eliminado: {destination.name} (ID: {destination.id})")
            return {"message": f"Destino '{destination.name}' eliminado exitosamente"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al eliminar destino {destination_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar destino: {str(e)}"
            )
    
    @staticmethod
    def get_with_stats(db: Session, destination_id: int) -> dict:
        """
        Obtener un destino con estadísticas de atracciones
        
        Args:
            db: Sesión de base de datos
            destination_id: ID del destino
            
        Returns:
            dict: Destino con estadísticas
        """
        from shared.database.models import Attraction
        
        destination = DestinationService.get_or_404(db, destination_id)
        
        # Calcular estadísticas
        attractions_query = db.query(Attraction).filter(
            Attraction.destination_id == destination_id
        )
        
        total_attractions = attractions_query.count()
        
        avg_rating = db.query(
            func.avg(Attraction.rating)
        ).filter(
            Attraction.destination_id == destination_id,
            Attraction.rating.isnot(None)
        ).scalar()
        
        # Construir respuesta con estadísticas
        result = {
            **destination.__dict__,
            "total_attractions": total_attractions,
            "avg_rating": float(avg_rating) if avg_rating else None
        }
        
        # Eliminar atributos internos de SQLAlchemy
        result.pop('_sa_instance_state', None)
        
        return result
    
    @staticmethod
    def get_by_country(db: Session, country: str) -> List[Destination]:
        """
        Obtener todos los destinos de un país
        
        Args:
            db: Sesión de base de datos
            country: Nombre del país
            
        Returns:
            List[Destination]: Lista de destinos del país
        """
        return db.query(Destination).filter(
            Destination.country.ilike(f"%{country}%")
        ).all()