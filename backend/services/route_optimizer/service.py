# backend/services/router_optimizer/service.py
"""
Servicio para optimización de rutas usando A*
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from .a_star import AStar
from .path_generator import OptimizedRoute
from shared.database.models import Attraction
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class RouterOptimizerService:
    """Servicio de optimización de rutas"""
    
    @staticmethod
    def optimize_route(
        db: Session,
        start_attraction_id: int,
        end_attraction_id: int,
        optimization_mode: str = "balanced",
        heuristic_type: str = "euclidean",
        attraction_scores: Optional[Dict[int, float]] = None,
        max_iterations: int = 10000
    ) -> Dict:
        """
        Optimizar ruta entre dos atracciones usando A*
        
        Args:
            db: Sesión de base de datos
            start_attraction_id: ID de atracción de inicio
            end_attraction_id: ID de atracción destino
            optimization_mode: Modo de optimización
            heuristic_type: Tipo de heurística
            attraction_scores: Scores de idoneidad (opcional)
            max_iterations: Máximo de iteraciones
            
        Returns:
            Dict: Ruta optimizada con detalles
        """
        try:
            # Verificar que las atracciones existen
            start_attr = db.query(Attraction).filter(
                Attraction.id == start_attraction_id
            ).first()
            
            end_attr = db.query(Attraction).filter(
                Attraction.id == end_attraction_id
            ).first()
            
            if not start_attr:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Atracción de inicio {start_attraction_id} no encontrada"
                )
            
            if not end_attr:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Atracción destino {end_attraction_id} no encontrada"
                )
            
            # Inicializar A*
            astar = AStar(
                db=db,
                optimization_mode=optimization_mode,
                heuristic_type=heuristic_type
            )
            
            # Encontrar ruta óptima
            route = astar.find_path(
                start_attraction_id=start_attraction_id,
                end_attraction_id=end_attraction_id,
                attraction_scores=attraction_scores,
                max_iterations=max_iterations
            )
            
            # Formatear respuesta
            response = RouterOptimizerService._format_route_response(
                route,
                start_attr,
                end_attr
            )
            
            logger.info(
                f"Ruta optimizada: {start_attr.name} → {end_attr.name} "
                f"({route.total_distance:.0f}m, {route.total_time}min)"
            )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error optimizando ruta: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al optimizar ruta: {str(e)}"
            )
    
    @staticmethod
    def optimize_multi_stop(
        db: Session,
        start_attraction_id: int,
        waypoints: List[int],
        end_attraction_id: Optional[int] = None,
        optimization_mode: str = "balanced",
        attraction_scores: Optional[Dict[int, float]] = None
    ) -> Dict:
        """
        Optimizar ruta con múltiples paradas
        
        Args:
            db: Sesión de base de datos
            start_attraction_id: ID de inicio
            waypoints: Lista de IDs de atracciones a visitar
            end_attraction_id: ID de destino final (opcional)
            optimization_mode: Modo de optimización
            attraction_scores: Scores de idoneidad
            
        Returns:
            Dict: Ruta completa optimizada
        """
        try:
            if not waypoints:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debe proporcionar al menos una parada (waypoint)"
                )
            
            # Verificar que el inicio existe
            start_attr = db.query(Attraction).filter(
                Attraction.id == start_attraction_id
            ).first()
            
            if not start_attr:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Atracción de inicio {start_attraction_id} no encontrada"
                )
            
            # Si no hay destino final, volver al inicio
            if end_attraction_id is None:
                end_attraction_id = start_attraction_id
            
            # Inicializar A*
            astar = AStar(
                db=db,
                optimization_mode=optimization_mode
            )
            
            # Variables para la ruta completa
            current_location = start_attraction_id
            remaining_stops = waypoints.copy()
            
            all_attractions = []
            all_segments = []
            total_distance = 0.0
            total_time = 0
            total_cost = 0.0
            total_nodes = 0
            
            # Agregar atracción de inicio
            all_attractions.append({
                'id': start_attr.id,
                'name': start_attr.name,
                'category': start_attr.category,
                'order': 0
            })
            
            order = 1
            
            # Visitar cada parada (estrategia greedy: siguiente más cercano)
            while remaining_stops:
                best_next = None
                best_route = None
                best_cost = float('inf')
                
                # Encontrar la parada más óptima siguiente
                for next_stop in remaining_stops:
                    route = astar.find_path(
                        start_attraction_id=current_location,
                        end_attraction_id=next_stop,
                        attraction_scores=attraction_scores
                    )
                    
                    if route.path_found:
                        # Usar costo total como métrica
                        route_cost = (
                            route.total_distance / 10000 +
                            route.total_time / 120 +
                            route.total_cost / 100
                        )
                        
                        if route_cost < best_cost:
                            best_cost = route_cost
                            best_next = next_stop
                            best_route = route
                
                # Si no se pudo alcanzar ninguna parada
                if best_next is None:
                    logger.warning(f"No se encontró ruta desde {current_location} a ninguna parada restante")
                    break
                
                # Agregar atracciones de la ruta (excepto la primera que ya está)
                for attr in best_route.attractions[1:]:
                    attr['order'] = order
                    all_attractions.append(attr)
                    order += 1
                
                # Agregar segmentos
                all_segments.extend([
                    {
                        'from_attraction_id': seg.from_attraction_id,
                        'to_attraction_id': seg.to_attraction_id,
                        'distance_meters': seg.distance_meters,
                        'travel_time_minutes': seg.travel_time_minutes,
                        'transport_mode': seg.transport_mode,
                        'cost': seg.cost
                    }
                    for seg in best_route.segments
                ])
                
                # Acumular totales
                total_distance += best_route.total_distance
                total_time += best_route.total_time
                total_cost += best_route.total_cost
                total_nodes += best_route.nodes_explored
                
                # Actualizar ubicación actual y remover parada visitada
                current_location = best_next
                remaining_stops.remove(best_next)
            
            # Ruta final al destino (si es diferente de la última parada)
            if current_location != end_attraction_id:
                final_route = astar.find_path(
                    start_attraction_id=current_location,
                    end_attraction_id=end_attraction_id,
                    attraction_scores=attraction_scores
                )
                
                if final_route.path_found:
                    # Agregar atracciones finales
                    for attr in final_route.attractions[1:]:
                        attr['order'] = order
                        all_attractions.append(attr)
                        order += 1
                    
                    # Agregar segmentos finales
                    all_segments.extend([
                        {
                            'from_attraction_id': seg.from_attraction_id,
                            'to_attraction_id': seg.to_attraction_id,
                            'distance_meters': seg.distance_meters,
                            'travel_time_minutes': seg.travel_time_minutes,
                            'transport_mode': seg.transport_mode,
                            'cost': seg.cost
                        }
                        for seg in final_route.segments
                    ])
                    
                    total_distance += final_route.total_distance
                    total_time += final_route.total_time
                    total_cost += final_route.total_cost
                    total_nodes += final_route.nodes_explored
            
            # Calcular score de optimización
            optimization_score = max(0, 100 - min(100, (total_distance / 10000) * 50))
            
            logger.info(
                f"Ruta multi-stop optimizada: {len(all_attractions)} atracciones, "
                f"{total_distance:.0f}m, {total_time}min"
            )
            
            return {
                "path_found": len(all_attractions) > 0,
                "start_attraction": {
                    "id": start_attr.id,
                    "name": start_attr.name
                },
                "attractions": all_attractions,
                "segments": all_segments,
                "summary": {
                    "total_attractions": len(all_attractions),
                    "total_distance_meters": round(total_distance, 2),
                    "total_distance_km": round(total_distance / 1000, 2),
                    "total_time_minutes": total_time,
                    "total_time_hours": round(total_time / 60, 2),
                    "total_cost": round(total_cost, 2),
                    "optimization_score": round(optimization_score, 2),
                    "nodes_explored": total_nodes
                },
                "metadata": {
                    "optimization_mode": optimization_mode,
                    "waypoints_requested": len(waypoints),
                    "waypoints_visited": len(waypoints) - len(remaining_stops)
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error optimizando ruta multi-stop: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al optimizar ruta multi-stop: {str(e)}"
            )
    
    @staticmethod
    def compare_routes(
        db: Session,
        start_attraction_id: int,
        end_attraction_id: int,
        attraction_scores: Optional[Dict[int, float]] = None
    ) -> Dict:
        """
        Comparar rutas con diferentes modos de optimización
        
        Args:
            db: Sesión de base de datos
            start_attraction_id: ID de inicio
            end_attraction_id: ID de destino
            attraction_scores: Scores de idoneidad
            
        Returns:
            Dict: Comparación de rutas
        """
        try:
            modes = ["distance", "time", "cost", "balanced", "score"]
            comparisons = []
            
            for mode in modes:
                try:
                    astar = AStar(db=db, optimization_mode=mode)
                    
                    route = astar.find_path(
                        start_attraction_id=start_attraction_id,
                        end_attraction_id=end_attraction_id,
                        attraction_scores=attraction_scores
                    )
                    
                    if route.path_found:
                        comparisons.append({
                            "mode": mode,
                            "path_found": True,
                            "total_distance_meters": route.total_distance,
                            "total_time_minutes": route.total_time,
                            "total_cost": route.total_cost,
                            "optimization_score": route.optimization_score,
                            "nodes_explored": route.nodes_explored,
                            "attractions_count": len(route.attractions)
                        })
                    else:
                        comparisons.append({
                            "mode": mode,
                            "path_found": False
                        })
                        
                except Exception as e:
                    logger.warning(f"Error con modo {mode}: {str(e)}")
                    comparisons.append({
                        "mode": mode,
                        "path_found": False,
                        "error": str(e)
                    })
            
            logger.info(f"Comparación de rutas completada: {len(comparisons)} modos")
            
            return {
                "start_attraction_id": start_attraction_id,
                "end_attraction_id": end_attraction_id,
                "comparisons": comparisons
            }
            
        except Exception as e:
            logger.error(f"Error comparando rutas: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al comparar rutas: {str(e)}"
            )
    
    @staticmethod
    def _format_route_response(
        route: OptimizedRoute,
        start_attr: Attraction,
        end_attr: Attraction
    ) -> Dict:
        """
        Formatear respuesta de ruta optimizada
        
        Args:
            route: Ruta optimizada
            start_attr: Atracción de inicio
            end_attr: Atracción de destino
            
        Returns:
            Dict: Respuesta formateada
        """
        return {
            "path_found": route.path_found,
            "start_attraction": {
                "id": start_attr.id,
                "name": start_attr.name,
                "category": start_attr.category
            },
            "end_attraction": {
                "id": end_attr.id,
                "name": end_attr.name,
                "category": end_attr.category
            },
            "attractions": route.attractions,
            "segments": [
                {
                    "from_attraction_id": seg.from_attraction_id,
                    "to_attraction_id": seg.to_attraction_id,
                    "distance_meters": seg.distance_meters,
                    "travel_time_minutes": seg.travel_time_minutes,
                    "transport_mode": seg.transport_mode,
                    "cost": seg.cost
                }
                for seg in route.segments
            ],
            "summary": {
                "total_distance_meters": route.total_distance,
                "total_distance_km": round(route.total_distance / 1000, 2),
                "total_time_minutes": route.total_time,
                "total_time_hours": round(route.total_time / 60, 2),
                "total_cost": route.total_cost,
                "optimization_score": route.optimization_score,
                "nodes_explored": route.nodes_explored
            },
            "metadata": {
                "optimization_mode": route.optimization_mode,
                "algorithm": "A*",
                "hops": len(route.attractions) - 1
            }
        }