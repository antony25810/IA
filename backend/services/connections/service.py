# backend/services/connections/service.py
"""
Servicio CRUD para gestionar conexiones entre atracciones
Fundamental para construcción de grafos y algoritmos de rutas
"""
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from geoalchemy2.functions import ST_Distance # type: ignore
from fastapi import HTTPException, status

from shared.database.models import AttractionConnection, Attraction
from shared.schemas.connection import (
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionRead,
    ConnectionSearchParams
)
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class ConnectionService:
    """Servicio para operaciones CRUD de conexiones entre atracciones"""
    
    @staticmethod
    def create(db: Session, data: ConnectionCreate) -> AttractionConnection:
        """
        Crear una nueva conexión entre dos atracciones
        
        Args:
            db: Sesión de base de datos
            data: Datos de la conexión a crear
            
        Returns:
            AttractionConnection: Conexión creada
        """
        try:
            # Verificar que las atracciones existen
            from_attraction = db.query(Attraction).filter(
                Attraction.id == data.from_attraction_id
            ).first()
            
            if not from_attraction:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Atracción origen con ID {data.from_attraction_id} no encontrada"
                )
            
            to_attraction = db.query(Attraction).filter(
                Attraction.id == data.to_attraction_id
            ).first()
            
            if not to_attraction:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Atracción destino con ID {data.to_attraction_id} no encontrada"
                )
            
            # Verificar que no exista una conexión duplicada
            existing = db.query(AttractionConnection).filter(
                and_(
                    AttractionConnection.from_attraction_id == data.from_attraction_id,
                    AttractionConnection.to_attraction_id == data.to_attraction_id
                )
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe una conexión entre las atracciones {data.from_attraction_id} y {data.to_attraction_id}"
                )
            
            # Crear la conexión
            connection = AttractionConnection(**data.model_dump())
            
            db.add(connection)
            db.commit()
            db.refresh(connection)
            
            logger.info(
                f"Conexión creada: {from_attraction.name} -> {to_attraction.name} "
                f"({data.transport_mode}, {data.distance_meters}m)"
            )
            return connection
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error al crear conexión: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear conexión: {str(e)}"
            )
    
    @staticmethod
    def create_bidirectional(
        db: Session,
        from_id: int,
        to_id: int,
        data: ConnectionCreate
    ) -> Tuple[AttractionConnection, AttractionConnection]:
        """
        Crear conexión bidireccional (A->B y B->A)
        
        Args:
            db: Sesión de base de datos
            from_id: ID de atracción origen
            to_id: ID de atracción destino
            data: Datos de la conexión
            
        Returns:
            Tuple: (conexión A->B, conexión B->A)
        """
        # Crear conexión A -> B
        data_ab = data.model_copy()
        data_ab.from_attraction_id = from_id
        data_ab.to_attraction_id = to_id
        connection_ab = ConnectionService.create(db, data_ab)
        
        # Crear conexión B -> A (inversa)
        data_ba = data.model_copy()
        data_ba.from_attraction_id = to_id
        data_ba.to_attraction_id = from_id
        connection_ba = ConnectionService.create(db, data_ba)
        
        logger.info(f"Conexión bidireccional creada entre {from_id} y {to_id}")
        return connection_ab, connection_ba
    
    @staticmethod
    def get(db: Session, connection_id: int) -> Optional[AttractionConnection]:
        """Obtener una conexión por ID"""
        return db.query(AttractionConnection).filter(
            AttractionConnection.id == connection_id
        ).first()
    
    @staticmethod
    def get_or_404(db: Session, connection_id: int) -> AttractionConnection:
        """Obtener una conexión por ID o lanzar 404"""
        connection = ConnectionService.get(db, connection_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conexión con ID {connection_id} no encontrada"
            )
        return connection
    
    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        from_attraction_id: Optional[int] = None,
        to_attraction_id: Optional[int] = None,
        transport_mode: Optional[str] = None
    ) -> Tuple[List[AttractionConnection], int]:
        """
        Obtener lista de conexiones con filtros
        
        Args:
            db: Sesión de base de datos
            skip: Registros a saltar (paginación)
            limit: Número máximo de registros
            from_attraction_id: Filtrar por atracción origen
            to_attraction_id: Filtrar por atracción destino
            transport_mode: Filtrar por modo de transporte
            
        Returns:
            Tuple: (lista de conexiones, total)
        """
        query = db.query(AttractionConnection)
        
        # Aplicar filtros
        if from_attraction_id:
            query = query.filter(
                AttractionConnection.from_attraction_id == from_attraction_id
            )
        
        if to_attraction_id:
            query = query.filter(
                AttractionConnection.to_attraction_id == to_attraction_id
            )
        
        if transport_mode:
            query = query.filter(
                AttractionConnection.transport_mode == transport_mode.lower()
            )
        
        # Contar total
        total = query.count()
        
        # Ordenar por distancia y aplicar paginación
        connections = query.order_by(
            AttractionConnection.distance_meters
        ).offset(skip).limit(limit).all()
        
        return connections, total
    
    @staticmethod
    def get_connections_from(
        db: Session,
        attraction_id: int,
        transport_mode: Optional[str] = None
    ) -> List[AttractionConnection]:
        """
        Obtener todas las conexiones que salen de una atracción
        Útil para construir grafos y algoritmos de búsqueda
        
        Args:
            db: Sesión de base de datos
            attraction_id: ID de la atracción origen
            transport_mode: Filtrar por modo de transporte (opcional)
            
        Returns:
            List[AttractionConnection]: Lista de conexiones salientes
        """
        query = db.query(AttractionConnection).filter(
            AttractionConnection.from_attraction_id == attraction_id
        )
        
        if transport_mode:
            query = query.filter(
                AttractionConnection.transport_mode == transport_mode.lower()
            )
        
        return query.order_by(
            AttractionConnection.distance_meters
        ).all()
    
    @staticmethod
    def get_connections_to(
        db: Session,
        attraction_id: int,
        transport_mode: Optional[str] = None
    ) -> List[AttractionConnection]:
        """
        Obtener todas las conexiones que llegan a una atracción
        
        Args:
            db: Sesión de base de datos
            attraction_id: ID de la atracción destino
            transport_mode: Filtrar por modo de transporte (opcional)
            
        Returns:
            List[AttractionConnection]: Lista de conexiones entrantes
        """
        query = db.query(AttractionConnection).filter(
            AttractionConnection.to_attraction_id == attraction_id
        )
        
        if transport_mode:
            query = query.filter(
                AttractionConnection.transport_mode == transport_mode.lower()
            )
        
        return query.order_by(
            AttractionConnection.distance_meters
        ).all()
    
    @staticmethod
    def get_connection_between(
        db: Session,
        from_id: int,
        to_id: int
    ) -> Optional[AttractionConnection]:
        """
        Obtener conexión específica entre dos atracciones
        
        Args:
            db: Sesión de base de datos
            from_id: ID atracción origen
            to_id: ID atracción destino
            
        Returns:
            Optional[AttractionConnection]: Conexión encontrada o None
        """
        return db.query(AttractionConnection).filter(
            and_(
                AttractionConnection.from_attraction_id == from_id,
                AttractionConnection.to_attraction_id == to_id
            )
        ).first()
    
    @staticmethod
    def build_graph(
        db: Session,
        destination_id: Optional[int] = None,
        transport_mode: Optional[str] = None
    ) -> Dict[int, List[Dict]]:
        """
        Construir grafo de conexiones para algoritmos (BFS, A*)
        
        Args:
            db: Sesión de base de datos
            destination_id: Filtrar por destino (opcional)
            transport_mode: Filtrar por transporte (opcional)
            
        Returns:
            Dict: Grafo en formato {attraction_id: [{to: id, distance: m, time: min, cost: f}]}
        """
        query = db.query(AttractionConnection)
        
        # Filtrar por destino si se especifica
        if destination_id:
            query = query.join(
                Attraction,
                AttractionConnection.from_attraction_id == Attraction.id
            ).filter(
                Attraction.destination_id == destination_id
            )
        
        # Filtrar por transporte
        if transport_mode:
            query = query.filter(
                AttractionConnection.transport_mode == transport_mode.lower()
            )
        
        connections = query.all()
        
        # Construir el grafo
        graph = {}
        for conn in connections:
            if conn.from_attraction_id not in graph:
                graph[conn.from_attraction_id] = []
            
            graph[conn.from_attraction_id].append({
                'to': conn.to_attraction_id,
                'distance_meters': float(conn.distance_meters),
                'travel_time_minutes': conn.travel_time_minutes,
                'transport_mode': conn.transport_mode,
                'cost': float(conn.cost) if conn.cost else 0.0,
                'traffic_factor': float(conn.traffic_factor) if conn.traffic_factor else 1.0
            })
        
        logger.info(f"Grafo construido con {len(graph)} nodos")
        return graph
    
    @staticmethod
    def update(
        db: Session,
        connection_id: int,
        data: ConnectionUpdate
    ) -> AttractionConnection:
        """
        Actualizar una conexión existente
        
        Args:
            db: Sesión de base de datos
            connection_id: ID de la conexión
            data: Datos a actualizar
            
        Returns:
            AttractionConnection: Conexión actualizada
        """
        connection = ConnectionService.get_or_404(db, connection_id)
        
        try:
            update_data = data.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                setattr(connection, field, value)
            
            db.commit()
            db.refresh(connection)
            
            logger.info(f"Conexión {connection_id} actualizada")
            return connection
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al actualizar conexión {connection_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar conexión: {str(e)}"
            )
    
    @staticmethod
    def delete(db: Session, connection_id: int) -> dict:
        """
        Eliminar una conexión
        
        Args:
            db: Sesión de base de datos
            connection_id: ID de la conexión
            
        Returns:
            dict: Mensaje de confirmación
        """
        connection = ConnectionService.get_or_404(db, connection_id)
        
        try:
            db.delete(connection)
            db.commit()
            
            logger.info(f"Conexión {connection_id} eliminada")
            return {"message": f"Conexión {connection_id} eliminada exitosamente"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al eliminar conexión {connection_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al eliminar conexión: {str(e)}"
            )
    
    @staticmethod
    def calculate_connection_from_locations(
        db: Session,
        from_id: int,
        to_id: int,
        transport_mode: str = "walking"
    ) -> Dict:
        """
        Calcular automáticamente distancia y tiempo entre dos atracciones
        usando PostGIS y estimaciones de velocidad
        
        Args:
            db: Sesión de base de datos
            from_id: ID atracción origen
            to_id: ID atracción destino
            transport_mode: Modo de transporte
            
        Returns:
            Dict: Datos calculados para la conexión
        """
        from geoalchemy2 import Geography as GeoType # type: ignore
        from sqlalchemy import cast, func as sql_func
        
        from_attr = db.query(Attraction).filter(Attraction.id == from_id).first()
        to_attr = db.query(Attraction).filter(Attraction.id == to_id).first()
        
        if not from_attr or not to_attr:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Una o ambas atracciones no encontradas"
            )
        
        distance = db.query(
            ST_Distance(
                cast(from_attr.location, GeoType),
                cast(to_attr.location, GeoType)
            )
        ).scalar()
        
        if distance is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al calcular distancia geográfica"
            )
        
        distance_meters = float(distance)
        
        # Validar que la distancia sea razonable
        if distance_meters < 1:
            logger.warning(
                f"Distancia muy pequeña calculada: {distance_meters}m entre "
                f"atracción {from_id} y {to_id}. Verificar coordenadas."
            )
        
        # Velocidades promedio por modo de transporte (km/h)
        speeds = {
            'walking': 5.0,
            'bicycle': 15.0,
            'car': 30.0,
            'public_transport': 20.0,
            'taxi': 30.0
        }
        
        speed_kmh = speeds.get(transport_mode.lower(), 5.0)
        distance_km = distance_meters / 1000
        time_hours = distance_km / speed_kmh
        time_minutes = int(time_hours * 60)
        
        # Costos aproximados
        costs = {
            'walking': 0.0,
            'bicycle': 0.0,
            'car': distance_km * 2.0,  # $2 por km
            'public_transport': 2.5,  # Tarifa fija
            'taxi': max(5.0, distance_km * 3.0)  # Mínimo $5
        }
        
        cost = costs.get(transport_mode.lower(), 0.0)
        
        logger.info(
            f"Conexión calculada: {from_attr.name} -> {to_attr.name} = "
            f"{distance_meters:.2f}m, {time_minutes}min, ${cost:.2f} ({transport_mode})"
        )
        
        return {
            'distance_meters': round(distance_meters, 2),
            'travel_time_minutes': max(time_minutes, 1),
            'cost': round(cost, 2),
            'transport_mode': transport_mode.lower()
        }
    
    @staticmethod
    def get_statistics(db: Session, attraction_id: int) -> Dict:
        """
        Obtener estadísticas de conectividad de una atracción
        
        Args:
            db: Sesión de base de datos
            attraction_id: ID de la atracción
            
        Returns:
            Dict: Estadísticas de conexiones
        """
        outgoing = db.query(AttractionConnection).filter(
            AttractionConnection.from_attraction_id == attraction_id
        ).count()
        
        incoming = db.query(AttractionConnection).filter(
            AttractionConnection.to_attraction_id == attraction_id
        ).count()
        
        avg_distance_out = db.query(
            func.avg(AttractionConnection.distance_meters)
        ).filter(
            AttractionConnection.from_attraction_id == attraction_id
        ).scalar()
        
        return {
            'attraction_id': attraction_id,
            'outgoing_connections': outgoing,
            'incoming_connections': incoming,
            'total_connections': outgoing + incoming,
            'avg_distance_meters': float(avg_distance_out) if avg_distance_out else 0.0
        }