# backend/services/router_optimizer/service.py
"""
Servicio para optimización de rutas usando A*
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from .a_star import AStar
from .path_generator import OptimizedRoute
from shared.database. models import Attraction
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class RouterOptimizerService:
    """Servicio de optimización de rutas"""
    
    # ═══════════════════════════════════════════════════════════
    # CONFIGURACIÓN DE PESOS POR MODO
    # ═══════════════════════════════════════════════════════════
    
    MODE_WEIGHTS = {
        "balanced": {"distance": 1.0, "time": 1.0, "cost": 1.0},
        "distance": {"distance": 5.0, "time": 0.5, "cost": 0.2},
        "time":     {"distance": 0.5, "time": 5.0, "cost": 0.2},
        "cost":     {"distance": 0.1, "time": 0.1, "cost": 10.0},
        "score":    {"distance": 0.3, "time": 0.3, "cost": 0.3},
    }
    
    # Umbrales de costo para penalizaciones
    COST_THRESHOLDS = {
        "free": 0,
        "cheap": 10,      # Bus, metro
        "medium": 30,     # Uber compartido
        "expensive": 50   # Taxi
    }
    
    # ═══════════════════════════════════════════════════════════
    
    @staticmethod
    def optimize_route(
        db: Session,
        start_attraction_id: int,
        end_attraction_id: int,
        optimization_mode: str,
        heuristic_type: str = "euclidean",
        attraction_scores: Optional[Dict[int, float]] = None,
        max_iterations: int = 10000
    ) -> Dict:
        """
        Optimizar ruta entre dos atracciones usando A*
        """
        try:
            start_attr = db.query(Attraction).filter(
                Attraction.id == start_attraction_id
            ).first()
            
            end_attr = db.query(Attraction).filter(
                Attraction.id == end_attraction_id
            ).first()
            
            if not start_attr:
                raise HTTPException(
                    status_code=status. HTTP_404_NOT_FOUND,
                    detail=f"Atracción de inicio {start_attraction_id} no encontrada"
                )
            
            if not end_attr:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Atracción destino {end_attraction_id} no encontrada"
                )
            
            astar = AStar(
                db=db,
                optimization_mode=optimization_mode,
                heuristic_type=heuristic_type
            )
            
            route = astar.find_path(
                start_attraction_id=start_attraction_id,
                end_attraction_id=end_attraction_id,
                attraction_scores=attraction_scores,
                max_iterations=max_iterations
            )
            
            response = RouterOptimizerService._format_route_response(
                route,
                start_attr,
                end_attr
            )
            
            logger.info(
                f"Ruta optimizada ({optimization_mode}): {start_attr.name} → {end_attr.name} "
                f"({route.total_distance:.0f}m, {route.total_time}min, ${route.total_cost:.2f})"
            )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error optimizando ruta: {str(e)}")
            raise HTTPException(
                status_code=status. HTTP_500_INTERNAL_SERVER_ERROR,
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
        """
        try:
            if not waypoints:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debe proporcionar al menos una parada (waypoint)"
                )
            
            start_attr = db.query(Attraction).filter(
                Attraction.id == start_attraction_id
            ).first()
            
            if not start_attr:
                raise HTTPException(
                    status_code=status. HTTP_404_NOT_FOUND,
                    detail=f"Atracción de inicio {start_attraction_id} no encontrada"
                )
            
            if end_attraction_id is None:
                end_attraction_id = start_attraction_id
            
            # Inicializar A*
            astar = AStar(
                db=db,
                optimization_mode=optimization_mode
            )
            
            # ═══════════════════════════════════════════════════════════
            # OBTENER PESOS SEGÚN MODO
            # ═══════════════════════════════════════════════════════════
            
            weights = RouterOptimizerService.MODE_WEIGHTS.get(
                optimization_mode, 
                RouterOptimizerService.MODE_WEIGHTS["balanced"]
            )
            
            logger.info(f"🎯 Optimizando ruta en modo '{optimization_mode}' con pesos: {weights}")
            
            # ═══════════════════════════════════════════════════════════
            
            current_location = start_attraction_id
            remaining_stops = waypoints. copy()
            
            all_attractions = []
            all_segments = []
            total_distance = 0.0
            total_time = 0
            total_cost = 0.0
            total_nodes = 0
            
            # Contadores para análisis
            transport_stats = {
                "walking": 0,
                "public_transit": 0,
                "taxi": 0
            }
            
            all_attractions.append({
                'id': start_attr.id,
                'name': start_attr.name,
                'category': start_attr. category,
                'order': 0
            })
            
            order = 1
            
            while remaining_stops:
                best_next = None
                best_route = None
                best_weighted_cost = float('inf')
                
                for next_stop in remaining_stops:
                    route = astar.find_path(
                        start_attraction_id=current_location,
                        end_attraction_id=next_stop,
                        attraction_scores=attraction_scores
                    )
                    
                    if route. path_found:
                        # ═══════════════════════════════════════════════════
                        # CALCULAR COSTO PONDERADO SEGÚN MODO
                        # ═══════════════════════════════════════════════════
                        
                        weighted_cost = RouterOptimizerService._calculate_weighted_route_cost(
                            route=route,
                            weights=weights,
                            optimization_mode=optimization_mode
                        )
                        
                        # ═══════════════════════════════════════════════════
                        
                        if weighted_cost < best_weighted_cost:
                            best_weighted_cost = weighted_cost
                            best_next = next_stop
                            best_route = route
                
                if best_next is None:
                    logger.warning(f"No se encontró ruta desde {current_location}")
                    break
                
                # ═══════════════════════════════════════════════════════════
                # LOG DETALLADO PARA MODO COST
                # ═══════════════════════════════════════════════════════════
                
                if optimization_mode == "cost":
                    logger.info(
                        f"💰 Seleccionada ruta: costo=${best_route.total_cost:.2f}, "
                        f"distancia={best_route.total_distance:.0f}m, "
                        f"weighted={best_weighted_cost:.3f}"
                    )
                
                # ═══════════════════════════════════════════════════════════
                
                for attr in best_route.attractions[1:]:
                    attr['order'] = order
                    all_attractions.append(attr)
                    order += 1
                
                # Procesar segmentos y contar tipos de transporte
                for seg in best_route.segments:
                    segment_dict = {
                        'from_attraction_id': seg.from_attraction_id,
                        'to_attraction_id': seg.to_attraction_id,
                        'distance_meters': seg.distance_meters,
                        'travel_time_minutes': seg.travel_time_minutes,
                        'transport_mode': seg.transport_mode,
                        'cost': seg.cost
                    }
                    all_segments.append(segment_dict)
                    
                    # Estadísticas de transporte
                    if seg.cost == 0:
                        transport_stats["walking"] += 1
                    elif seg.cost <= RouterOptimizerService.COST_THRESHOLDS["medium"]:
                        transport_stats["public_transit"] += 1
                    else:
                        transport_stats["taxi"] += 1
                
                total_distance += best_route.total_distance
                total_time += best_route. total_time
                total_cost += best_route.total_cost
                total_nodes += best_route.nodes_explored
                
                current_location = best_next
                remaining_stops. remove(best_next)
            
            # Ruta de regreso
            if current_location != end_attraction_id:
                final_route = astar.find_path(
                    start_attraction_id=current_location,
                    end_attraction_id=end_attraction_id,
                    attraction_scores=attraction_scores
                )
                
                if final_route. path_found:

                    
                    if optimization_mode == "cost":
                        logger.info(
                            f"💰 Ruta de regreso: costo=${final_route. total_cost:.2f}, "
                            f"distancia={final_route. total_distance:.0f}m"
                        )
                    
                    # ═══════════════════════════════════════════════════════════
                    
                    for attr in final_route.attractions[1:]:
                        attr['order'] = order
                        all_attractions.append(attr)
                        order += 1
                    
                    for seg in final_route.segments:
                        segment_dict = {
                            'from_attraction_id': seg.from_attraction_id,
                            'to_attraction_id': seg.to_attraction_id,
                            'distance_meters': seg.distance_meters,
                            'travel_time_minutes': seg.travel_time_minutes,
                            'transport_mode': seg.transport_mode,
                            'cost': seg.cost
                        }
                        all_segments.append(segment_dict)
                        
                        if seg.cost == 0:
                            transport_stats["walking"] += 1
                        elif seg. cost <= RouterOptimizerService. COST_THRESHOLDS["medium"]:
                            transport_stats["public_transit"] += 1
                        else:
                            transport_stats["taxi"] += 1
                    
                    total_distance += final_route. total_distance
                    total_time += final_route.total_time
                    total_cost += final_route.total_cost
                    total_nodes += final_route.nodes_explored
            
            # ═══════════════════════════════════════════════════════════
            # CALCULAR SCORE DE OPTIMIZACIÓN SEGÚN MODO
            # ═══════════════════════════════════════════════════════════
            
            optimization_score = RouterOptimizerService._calculate_optimization_score(
                optimization_mode=optimization_mode,
                total_distance=total_distance,
                total_time=total_time,
                total_cost=total_cost,
                transport_stats=transport_stats
            )
            
            # ═══════════════════════════════════════════════════════════
            # LOG RESUMEN FINAL
            # ═══════════════════════════════════════════════════════════
            
            logger.info(
                f"✅ Ruta completada ({optimization_mode}): "
                f"{len(all_attractions)} atracciones, "
                f"{total_distance:.0f}m, {total_time}min, ${total_cost:.2f}"
            )
            
            if optimization_mode == "cost":
                logger.info(
                    f"📊 Transporte: {transport_stats['walking']} caminando, "
                    f"{transport_stats['public_transit']} transporte público, "
                    f"{transport_stats['taxi']} taxi"
                )
            
            # ═══════════════════════════════════════════════════════════
            
            return {
                "path_found": len(all_attractions) > 0,
                "start_attraction": {
                    "id": start_attr. id,
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
                    "nodes_explored": total_nodes,
                    "transport_breakdown": transport_stats  # ← NUEVO
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
            logger. error(f"Error optimizando ruta multi-stop: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al optimizar ruta multi-stop: {str(e)}"
            )
    
    @staticmethod
    def _calculate_weighted_route_cost(
        route: OptimizedRoute,
        weights: Dict[str, float],
        optimization_mode: str
    ) -> float:
        """
        Calcular costo ponderado de una ruta según el modo de optimización
        
        Args:
            route: Ruta calculada por A*
            weights: Pesos para distance, time, cost
            optimization_mode: Modo de optimización
            
        Returns:
            float: Costo ponderado
        """
        # Normalizar valores
        norm_distance = route.total_distance / 1000  # km
        norm_time = route.total_time / 60            # horas
        norm_cost = route.total_cost                  # valor directo
        
        # Costo base ponderado
        weighted_cost = (
            norm_distance * weights['distance'] +
            norm_time * weights['time'] +
            norm_cost * weights['cost']
        )
        
        # ═══════════════════════════════════════════════════════════
        # AJUSTES ESPECIALES SEGÚN MODO
        # ═══════════════════════════════════════════════════════════
        
        if optimization_mode == "cost":
            # Bonificar rutas gratuitas (caminando)
            if route.total_cost == 0:
                weighted_cost *= 0.3  # 70% de descuento
            # Bonificar rutas muy baratas
            elif route.total_cost <= RouterOptimizerService.COST_THRESHOLDS["cheap"]:
                weighted_cost *= 0.6  # 40% de descuento
            # Penalizar rutas caras
            elif route.total_cost >= RouterOptimizerService.COST_THRESHOLDS["expensive"]:
                weighted_cost *= 2.5  # 150% de penalización
                
        elif optimization_mode == "distance":
            # Penalizar rutas largas exponencialmente
            if route.total_distance > 3000:  # Más de 3km
                weighted_cost *= 1.5
                
        elif optimization_mode == "time":
            # Penalizar rutas lentas
            if route.total_time > 30:  # Más de 30 min
                weighted_cost *= 1.5
        
        # ═══════════════════════════════════════════════════════════
        
        return weighted_cost
    
    @staticmethod
    def _calculate_optimization_score(
        optimization_mode: str,
        total_distance: float,
        total_time: int,
        total_cost: float,
        transport_stats: Dict[str, int]
    ) -> float:
        """
        Calcular score de optimización según el modo
        
        Returns:
            float: Score de 0-100
        """
        base_score = 100.0
        
        if optimization_mode == "cost":
            # En modo costo, el score depende de cuánto se gastó
            if total_cost == 0:
                return 100.0  # Perfecto - todo gratis
            elif total_cost <= 20:
                return 90.0
            elif total_cost <= 50:
                return 75.0
            elif total_cost <= 100:
                return 50.0
            else:
                return max(0, 100 - total_cost)
                
        elif optimization_mode == "distance":
            # En modo distancia, score depende de km recorridos
            km = total_distance / 1000
            return max(0, 100 - (km * 10))
            
        elif optimization_mode == "time":
            # En modo tiempo, score depende de minutos
            return max(0, 100 - (total_time * 0.5))
            
        else:  # balanced, score
            # Score balanceado
            distance_penalty = min(50, (total_distance / 10000) * 50)
            cost_penalty = min(30, total_cost * 0.3)
            return max(0, base_score - distance_penalty - cost_penalty)
    
    @staticmethod
    def compare_routes(
        db: Session,
        start_attraction_id: int,
        end_attraction_id: int,
        attraction_scores: Optional[Dict[int, float]] = None
    ) -> Dict:
        """
        Comparar rutas con diferentes modos de optimización
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
                            "attractions_count": len(route. attractions)
                        })
                    else:
                        comparisons.append({
                            "mode": mode,
                            "path_found": False
                        })
                        
                except Exception as e:
                    logger.warning(f"Error con modo {mode}: {str(e)}")
                    comparisons. append({
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
            logger. error(f"Error comparando rutas: {str(e)}")
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
                "name": end_attr. name,
                "category": end_attr.category
            },
            "attractions": route.attractions,
            "segments": [
                {
                    "from_attraction_id": seg.from_attraction_id,
                    "to_attraction_id": seg.to_attraction_id,
                    "distance_meters": seg. distance_meters,
                    "travel_time_minutes": seg.travel_time_minutes,
                    "transport_mode": seg.transport_mode,
                    "cost": seg.cost
                }
                for seg in route. segments
            ],
            "summary": {
                "total_distance_meters": route. total_distance,
                "total_distance_km": round(route.total_distance / 1000, 2),
                "total_time_minutes": route. total_time,
                "total_time_hours": round(route.total_time / 60, 2),
                "total_cost": route.total_cost,
                "optimization_score": route.optimization_score,
                "nodes_explored": route.nodes_explored
            },
            "metadata": {
                "optimization_mode": route. optimization_mode,
                "algorithm": "A*",
                "hops": len(route.attractions) - 1
            }
        }