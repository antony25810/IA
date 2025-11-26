# backend/services/itinerary_generator/service.py
"""
Servicio de generación de itinerarios (VERSIÓN MEJORADA)
Ahora GUARDA en base de datos
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta, date
from sqlalchemy. orm import Session
from geoalchemy2.shape import to_shape # type: ignore

from shared.database.models import UserProfile, Attraction, Itinerary, ItineraryAttraction
from shared.database.models import ItineraryDay
from services.search_service import SearchService
from services. route_optimizer import RouterOptimizerService
from services. rules_engine import RulesEngineService
from . clustering import DayClustering
from shared.utils. logger import setup_logger

logger = setup_logger(__name__)


class ItineraryGeneratorService:
    """
    Orquestador principal para generar itinerarios completos
    Integra: Rules Engine -> BFS -> Scoring -> Clustering -> A*
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.search_service = SearchService()
        self.optimizer_service = RouterOptimizerService()

    def generate_itinerary(
        self, 
        user_profile_id: int, 
        destination_id: int,
        city_center_attraction_id: int, 
        num_days: int,
        start_date: datetime,
        hotel_attraction_id: Optional[int] = None,
        optimization_mode: str = "balanced",
        max_radius_km: float = 10.0,
        max_candidates: int = 50
    ) -> Dict:
        """
        Genera un itinerario optimizado multi-día y lo GUARDA en BD
        """
        logger.info(f"🚀 Generando itinerario de {num_days} días para perfil {user_profile_id}")
        
        # ---------------------------------------------------------
        # PASO 1: Enriquecer Perfil
        # ---------------------------------------------------------
        context = {
            "current_date": start_date,
            "current_time": start_date. time(),
            "weather": {"condition": "sunny", "temperature": 24}
        }
        
        enrichment_result = RulesEngineService.enrich_user_profile(
            db=self.db,
            user_profile_id=user_profile_id,
            context=context
        )
        
        computed_profile = enrichment_result['computed_profile']
        logger.info("✅ Perfil enriquecido")

        # ---------------------------------------------------------
        # PASO 2: Exploración BFS
        # ---------------------------------------------------------
        bfs_result = self.search_service.bfs_explore(
            db=self.db,
            start_attraction_id=city_center_attraction_id,
            user_profile_id=user_profile_id,
            max_candidates=max_candidates,
            max_radius_km=max_radius_km,
        )
        
        raw_candidates = bfs_result['candidates']
        if not raw_candidates:
            return {"error": "No se encontraron atracciones cercanas"}

        logger.info(f"✅ BFS completado: {len(raw_candidates)} candidatos")

        # ---------------------------------------------------------
        # PASO 3: Scoring
        # ---------------------------------------------------------
        ranked_candidates = self._rank_candidates(raw_candidates, computed_profile)
        
        daily_limit = computed_profile.get('max_daily_attractions', 4)
        total_needed = num_days * daily_limit
        selected_candidates = ranked_candidates[:total_needed]
        
        logger.info(f"✅ Scoring completado: {len(selected_candidates)} candidatos seleccionados")

        # ---------------------------------------------------------
        # PASO 4: Preparar para Clustering
        # ---------------------------------------------------------
        attractions_pool = []
        scores_map = {}
        
        for item in selected_candidates:
            attr = item['attraction']
            score = item['score']
            
            # Obtener coordenadas
            db_attr = self.db.query(Attraction). filter(Attraction.id == attr['id']).first()
            if not db_attr or not db_attr.location:
                continue
            
            try:
                point = to_shape(db_attr.location)
                lat, lon = point.y, point. x
            except Exception as e:
                logger.warning(f"Error extrayendo coordenadas: {e}")
                continue
            
            attractions_pool.append({
                'id': attr['id'],
                'name': attr['name'],
                'location_coords': (lat, lon),
                'score': score
            })
            scores_map[attr['id']] = score

        # ---------------------------------------------------------
        # PASO 5: Clustering
        # ---------------------------------------------------------
        daily_groups = DayClustering.cluster_attractions(attractions_pool, num_days)
        logger.info(f"✅ Clustering completado: {len(daily_groups)} grupos")

        # ---------------------------------------------------------
        # PASO 6: Crear Itinerario en BD
        # ---------------------------------------------------------
        hotel_id = hotel_attraction_id or city_center_attraction_id
        
        itinerary = Itinerary(
            user_profile_id=user_profile_id,
            destination_id=destination_id,
            start_point_id=hotel_id,
            name=f"Itinerario {num_days} días",
            num_days=num_days,
            start_date=start_date. date(),
            end_date=(start_date + timedelta(days=num_days - 1)). date(),
            generation_params={
                "optimization_mode": optimization_mode,
                "max_radius_km": max_radius_km,
                "max_candidates": max_candidates
            },
            algorithms_used={
                "search": "BFS",
                "routing": "A*",
                "clustering": "KMeans",
                "scoring": "RulesBased"
            },
            status='draft'
        )
        
        self.db.add(itinerary)
        self.db.flush()  # Obtener itinerary. id sin commit
        
        logger.info(f"✅ Itinerario creado en BD: ID {itinerary.id}")

        # ---------------------------------------------------------
        # PASO 7: Optimizar y Guardar Días
        # ---------------------------------------------------------
        total_distance = 0.0
        total_time = 0
        total_cost = 0.0
        total_attractions_count = 0
        visit_order_global = 1
        
        for day_idx, group in enumerate(daily_groups):
            day_num = day_idx + 1
            day_date = start_date. date() + timedelta(days=day_idx)
            
            if not group:
                continue
            
            waypoints = [a['id'] for a in group]
            
            logger.info(f"🔄 Optimizando Día {day_num} con {len(waypoints)} paradas")
            
            # Optimizar con A*
            route_result = self.optimizer_service. optimize_multi_stop(
                db=self.db,
                start_attraction_id=hotel_id,
                waypoints=waypoints,
                end_attraction_id=hotel_id,
                optimization_mode=optimization_mode,
                attraction_scores=scores_map
            )
            
            # Calcular centroide del cluster
            centroid_lat = sum(a['location_coords'][0] for a in group) / len(group)
            centroid_lon = sum(a['location_coords'][1] for a in group) / len(group)
            
            # Crear día en BD
            day_data_json = {
                "attractions": [
                    {
                        "attraction_id": route_result['attractions'][i]['id'],
                        "order": i + 1,
                        "arrival_time": None,  # TODO: Calcular horarios
                        "departure_time": None,
                        "visit_duration_minutes": 90,  # Default
                        "score": scores_map. get(route_result['attractions'][i]['id'])
                    }
                    for i in range(len(route_result['attractions']))
                ],
                "segments": route_result['segments']
            }
            
            itinerary_day = ItineraryDay(
                itinerary_id=itinerary.id,
                day_number=day_num,
                date=day_date,
                cluster_id=day_idx,
                cluster_centroid_lat=centroid_lat,
                cluster_centroid_lon=centroid_lon,
                day_data=day_data_json,
                total_distance_meters=route_result['summary']['total_distance_meters'],
                total_time_minutes=route_result['summary']['total_time_minutes'],
                total_cost=route_result['summary']['total_cost'],
                attractions_count=len(waypoints),
                optimization_score=route_result['summary']. get('optimization_score')
            )
            
            self.db.add(itinerary_day)
            self.db.flush()
            
            # Crear relaciones en ItineraryAttraction
            for idx, attr_id in enumerate(waypoints):
                itinerary_attr = ItineraryAttraction(
                    itinerary_id=itinerary.id,
                    day_id=itinerary_day.id,
                    attraction_id=attr_id,
                    visit_order=visit_order_global,
                    day_order=idx + 1,
                    attraction_score=scores_map.get(attr_id),
                    visit_duration_minutes=90
                )
                self.db.add(itinerary_attr)
                visit_order_global += 1
            
            # Acumular métricas
            total_distance += route_result['summary']['total_distance_meters']
            total_time += route_result['summary']['total_time_minutes']
            total_cost += route_result['summary']['total_cost']
            total_attractions_count += len(waypoints)
        
        # Actualizar métricas globales del itinerario
        itinerary.total_distance_meters = total_distance
        itinerary. total_duration_minutes = total_time
        itinerary.total_cost = total_cost
        itinerary.total_attractions = total_attractions_count
        itinerary.average_optimization_score = 85.0  # Calcular promedio real si es necesario
        
        self. db.commit()
        self.db.refresh(itinerary)
        
        logger.info(f"🎉 Itinerario {itinerary.id} generado exitosamente")
        
        return {
            "itinerary_id": itinerary.id,
            "message": "Itinerario generado exitosamente",
            "summary": {
                "num_days": num_days,
                "total_attractions": total_attractions_count,
                "total_distance_km": round(total_distance / 1000, 2),
                "total_time_hours": round(total_time / 60, 2),
                "total_cost": float(total_cost)
            }
        }

    def _rank_candidates(self, candidates_data: List[Dict], profile: Dict) -> List[Dict]:
        """
        Puntúa y ordena candidatos (MISMO ALGORITMO)
        """
        scored_list = []
        
        priority_cats = set(profile.get('priority_categories', []))
        recommended_cats = set(profile.get('recommended_categories', []))
        avoid_cats = set(profile.get('avoid_categories', []))
        allowed_prices = set(profile.get('allowed_price_ranges', ['gratis', 'bajo', 'medio', 'alto']))
        required_amenities = set(profile.get('required_amenities', []))
        min_rating = profile.get('min_rating', 0.0)

        for item in candidates_data:
            attr = item['attraction']
            bfs_context = {'dist': item. get('distance_from_start_meters', 0)}
            
            score = 0.0
            rating = attr.get('rating') or 3.0
            score += (rating * 10)
            
            cat = attr.get('category', '').lower()
            if cat in priority_cats:
                score += 30.0
            elif cat in recommended_cats:
                score += 15.0
            elif cat in avoid_cats:
                score -= 50.0
            
            price = attr.get('price_range', '').lower()
            if price not in allowed_prices:
                score -= 100.0
            
            attr_amenities = set(attr.get('amenities', []))
            missing_reqs = required_amenities - attr_amenities
            if missing_reqs:
                score -= (len(missing_reqs) * 40.0)
            
            if rating < min_rating:
                score -= 50.0
            
            score -= (bfs_context['dist'] / 1000.0)
            
            scored_list.append({
                'attraction': attr,
                'score': round(score, 2),
                'debug_info': f"Cat:{cat} | Rat:{rating}"
            })
        
        scored_list.sort(key=lambda x: x['score'], reverse=True)
        valid_candidates = [x for x in scored_list if x['score'] > -50.0]
        
        logger.info(f"✅ Ranking: {len(valid_candidates)} candidatos viables")
        return valid_candidates