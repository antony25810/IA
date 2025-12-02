# backend/services/itinerary_generator/service.py
from typing import List, Dict, Optional
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape # type: ignore

from shared.database.models import UserProfile, Attraction, Itinerary, ItineraryAttraction, ItineraryDay
from shared.config.constants import SCORING_WEIGHTS, DEFAULT_VISIT_DURATION
from services.search_service import SearchService
from services.route_optimizer import RouterOptimizerService
from services.rules_engine import RulesEngineService
from .clustering import DayClustering
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)

class ItineraryGeneratorService:
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
        
        logger.info(f"🚀 Generando itinerario de {num_days} días para perfil {user_profile_id}")
        
        # 1. Enriquecer Perfil
        context = {
            "current_date": start_date,
            "current_time": start_date.time(),
            "weather": {"condition": "sunny", "temperature": 24}
        }
        
        enrichment_result = RulesEngineService.enrich_user_profile(
            db=self.db,
            user_profile_id=user_profile_id,
            context=context
        )
        computed_profile = enrichment_result['computed_profile']

        # 2. Exploración BFS
        bfs_result = self.search_service.bfs_explore(
            db=self.db,
            start_attraction_id=city_center_attraction_id,
            user_profile_id=user_profile_id,
            max_candidates=max_candidates,
            max_radius_km=max_radius_km,
            optimization_mode=optimization_mode
        )
        
        raw_candidates = bfs_result['candidates']
        if not raw_candidates:
            return {"error": "No se encontraron atracciones cercanas"}

        # 3. Scoring
        ranked_candidates = self._rank_candidates(raw_candidates, computed_profile)
        daily_limit = computed_profile.get('max_daily_attractions', 4)
        total_needed = num_days * daily_limit
        selected_candidates = ranked_candidates[:total_needed]

        # 4. Preparar para Clustering
        attractions_pool = []
        scores_map = {}
        duration_map = {} 
        
        for item in selected_candidates:
            attr = item['attraction']
            score = item['score']
            
            db_attr = self.db.query(Attraction).filter(Attraction.id == attr['id']).first()
            if not db_attr or not db_attr.location:
                continue
            
            try:
                point = to_shape(db_attr.location)
                lat, lon = point.y, point.x
            except Exception:
                continue
            
            real_duration = db_attr.average_visit_duration or DEFAULT_VISIT_DURATION
            
            attractions_pool.append({
                'id': attr['id'],
                'name': attr['name'],
                'location_coords': (lat, lon),
                'score': score,
                'duration': real_duration
            })
            scores_map[attr['id']] = score
            duration_map[attr['id']] = real_duration

        # 5. Clustering
        daily_groups = DayClustering.cluster_attractions(attractions_pool, num_days)

        # 6. Crear Itinerario en BD
        hotel_id = hotel_attraction_id or city_center_attraction_id
        
        # Asegurar que start_date es datetime
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))

        itinerary = Itinerary(
            user_profile_id=user_profile_id,
            destination_id=destination_id,
            start_point_id=hotel_id,
            name=f"Itinerario {num_days} días",
            num_days=num_days,
            start_date=start_date.date(),
            end_date=(start_date + timedelta(days=num_days - 1)).date(),
            generation_params={
                "optimization_mode": optimization_mode,
                "max_radius_km": max_radius_km,
                "max_candidates": max_candidates
            },
            algorithms_used={"search": "BFS", "routing": "A*", "clustering": "KMeans"},
            status='draft'
        )
        
        self.db.add(itinerary)
        self.db.flush()

        # 7. Optimizar Días
        total_distance = 0.0
        total_time = 0
        total_cost = 0.0
        total_attractions_count = 0
        visit_order_global = 1
        
        for day_idx, group in enumerate(daily_groups):
            day_num = day_idx + 1
            day_date = start_date.date() + timedelta(days=day_idx)
            
            if not group:
                continue
            
            waypoints = [a['id'] for a in group]
            
            # Optimizar con A*
            route_result = self.optimizer_service.optimize_multi_stop(
                db=self.db,
                start_attraction_id=hotel_id,
                waypoints=waypoints,
                end_attraction_id=hotel_id,
                optimization_mode=optimization_mode,
                attraction_scores=scores_map
            )
            
            # Fallback si no encuentra ruta
            final_attractions_list = route_result['attractions'] if route_result['path_found'] else [{'id': wid, 'name': next((a['name'] for a in attractions_pool if a['id']==wid), '')} for wid in waypoints]
            final_segments_list = route_result['segments'] if route_result['path_found'] else []
            day_distance = route_result['summary']['total_distance_meters'] if route_result['path_found'] else 0.0
            day_time = route_result['summary']['total_time_minutes'] if route_result['path_found'] else 0
            day_cost = route_result['summary']['total_cost'] if route_result['path_found'] else 0.0

            centroid_lat = sum(a['location_coords'][0] for a in group) / len(group)
            centroid_lon = sum(a['location_coords'][1] for a in group) / len(group)
            
            # Preparar JSON
            day_data_attractions = []
            for i, attr_data in enumerate(final_attractions_list):
                attr_id = attr_data['id']
                duration = duration_map.get(attr_id, DEFAULT_VISIT_DURATION)
                day_data_attractions.append({
                    "attraction_id": attr_id,
                    "order": i + 1,
                    "visit_duration_minutes": duration,
                    "score": scores_map.get(attr_id)
                })

            day_data_json = {
                "attractions": day_data_attractions,
                "segments": final_segments_list
            }
            
            itinerary_day = ItineraryDay(
                itinerary_id=itinerary.id,
                day_number=day_num,
                date=day_date,
                cluster_id=day_idx,
                cluster_centroid_lat=centroid_lat,
                cluster_centroid_lon=centroid_lon,
                day_data=day_data_json,
                total_distance_meters=day_distance,
                total_time_minutes=day_time,
                total_cost=day_cost,
                attractions_count=len(waypoints),
                optimization_score=route_result['summary'].get('optimization_score', 0)
            )
            
            self.db.add(itinerary_day)
            self.db.flush()
            
            for idx, attr_data in enumerate(final_attractions_list):
                attr_id = attr_data['id']
                duration = duration_map.get(attr_id, DEFAULT_VISIT_DURATION)
                itinerary_attr = ItineraryAttraction(
                    itinerary_id=itinerary.id,
                    day_id=itinerary_day.id,
                    attraction_id=attr_id,
                    visit_order=visit_order_global,
                    day_order=idx + 1,
                    attraction_score=scores_map.get(attr_id),
                    visit_duration_minutes=duration
                )
                self.db.add(itinerary_attr)
                visit_order_global += 1
            
            total_distance = total_distance + day_distance
            total_time = total_time + day_time
            total_cost = total_cost + day_cost
            total_attractions_count = total_attractions_count + len(waypoints)
        
        itinerary.total_distance_meters = total_distance
        itinerary.total_duration_minutes = total_time
        itinerary.total_cost = total_cost
        itinerary.total_attractions = total_attractions_count
        itinerary.average_optimization_score = 85.0
        
        self.db.commit()
        self.db.refresh(itinerary)
        
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
        scored_list = []
        priority_cats = set(profile.get('priority_categories', []))
        recommended_cats = set(profile.get('recommended_categories', []))
        avoid_cats = set(profile.get('avoid_categories', []))
        allowed_prices = set(profile.get('allowed_price_ranges', ['gratis', 'bajo', 'medio', 'alto']))
        required_amenities = set(profile.get('required_amenities', []))
        min_rating = profile.get('min_rating', 0.0)

        for item in candidates_data:
            attr = item['attraction']
            dist_meters = item.get('distance_from_start', 0)
            
            score = 0.0
            rating = attr.get('rating') or 3.0
            
            # Cálculos seguros
            score = score + (rating * SCORING_WEIGHTS['rating_multiplier'])
            
            cat = attr.get('category', '').lower()
            if cat in priority_cats:
                score = score + SCORING_WEIGHTS['priority_category']
            elif cat in recommended_cats:
                score = score + SCORING_WEIGHTS['recommended_category']
            elif cat in avoid_cats:
                score = score + SCORING_WEIGHTS['avoid_category']
            
            price = attr.get('price_range', '').lower()
            if price not in allowed_prices:
                score = score + SCORING_WEIGHTS['price_mismatch']
            
            attr_amenities = set(attr.get('amenities') or [])
            missing_reqs = required_amenities - attr_amenities
            if missing_reqs:
                score = score + (len(missing_reqs) * SCORING_WEIGHTS['missing_amenity'])
            
            if rating < min_rating:
                score = score + SCORING_WEIGHTS['rating_below_min']
            
            dist_km = dist_meters / 1000.0
            score = score - (dist_km * SCORING_WEIGHTS['distance_penalty_per_km'])
            
            scored_list.append({'attraction': attr, 'score': round(score, 2)})
        
        scored_list.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_list