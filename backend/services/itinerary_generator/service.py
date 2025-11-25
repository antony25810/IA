# backend/services/itinerary_generator/service.py
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape # type: ignore

from shared.database.models import UserProfile, Attraction
from services.search_service import SearchService
from services.route_optimizer import RouterOptimizerService
from services.rules_engine import RulesEngineService
from .clustering import DayClustering
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)

class ItineraryGeneratorService:
    """
    Orquestador principal para generar itinerarios completos.
    Integra: Rules Engine -> BFS Exploration -> Scoring -> Clustering -> A* Routing
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.search_service = SearchService()
        self.optimizer_service = RouterOptimizerService()
        # RulesEngineService es estático, lo llamamos directamente

    def generate_itinerary(
        self, 
        user_profile_id: int, 
        city_center_attraction_id: int, 
        num_days: int,
        start_date: datetime,
        hotel_attraction_id: Optional[int] = None
    ) -> Dict:
        """
        Genera un itinerario optimizado multi-día.
        """
        logger.info(f"Generando itinerario de {num_days} días para perfil {user_profile_id}")
        
        # ---------------------------------------------------------
        # PASO 1: Enriquecer Perfil con Reglas de Negocio
        # ---------------------------------------------------------
        # Aquí el "Cerebro" decide qué necesita el usuario
        context = {
            "current_date": start_date,
            "current_time": start_date.time(),
            # Podríamos inyectar clima real aquí si tuviéramos servicio de clima
            "weather": {"condition": "sunny", "temperature": 24} 
        }
        
        enrichment_result = RulesEngineService.enrich_user_profile(
            db=self.db,
            user_profile_id=user_profile_id,
            context=context
        )
        
        computed_profile = enrichment_result['computed_profile']
        logger.info("Perfil enriquecido. Preferencias calculadas.")

        # ---------------------------------------------------------
        # PASO 2: Exploración (BFS) - "Abrir el abanico"
        # ---------------------------------------------------------
        # Buscamos muchos candidatos (ej: 50) para luego filtrar los mejores
        bfs_result = self.search_service.bfs_explore(
            db=self.db,
            start_attraction_id=city_center_attraction_id,
            user_profile_id=user_profile_id,
            max_candidates=50, # Traemos suficientes opciones
            max_radius_km=15.0,
        )
        
        raw_candidates = bfs_result['candidates']
        if not raw_candidates:
            logger.warning("No se encontraron candidatos con BFS.")
            return {"error": "No attractions found nearby"}

        # ---------------------------------------------------------
        # PASO 3: Selección y Puntuación (Scoring)
        # ---------------------------------------------------------
        # Aquí aplicamos la inteligencia del Motor de Reglas para elegir a los ganadores
        ranked_candidates = self._rank_candidates(raw_candidates, computed_profile)
        
        # Determinar cuántas atracciones necesitamos
        # El motor de reglas nos sugiere cuántas por día (max_daily_attractions)
        daily_limit = computed_profile.get('max_daily_attractions', 4)
        total_needed = num_days * daily_limit
        
        # Seleccionar los Top N
        selected_candidates = ranked_candidates[:total_needed]
        
        # Preparar datos para clustering (necesitamos coordenadas limpias)
        attractions_pool = []
        scores_map = {} # Para pasar al A* después
        
        for item in selected_candidates:
            attr = item['attraction']
            score = item['score']
            
            # Extraer coordenadas (PostGIS a Python)
            # Nota: Asumiendo que 'attr' es un dict serializado o modelo
            # Si viene del BFS serializado, location puede no estar accesible como objeto
            # Necesitamos asegurarnos de tener lat/lon
            lat, lon = 0.0, 0.0
            if 'location' in attr: 
                # Si es string o dict, depende de serialización
                pass 
            
            # Truco: Usamos el modelo original de la DB para geo
            db_attr = self.db.query(Attraction).filter(Attraction.id == attr['id']).first()
            if db_attr:
                point = to_shape(db_attr.location)
                lat, lon = point.y, point.x
            
            attractions_pool.append({
                'id': attr['id'],
                'name': attr['name'],
                'location_coords': (lat, lon), # Para clustering
                'score': score # Para debug
            })
            scores_map[attr['id']] = score

        # ---------------------------------------------------------
        # PASO 4: Clustering (Agrupación por Días)
        # ---------------------------------------------------------
        daily_groups = DayClustering.cluster_attractions(attractions_pool, num_days)

        # ---------------------------------------------------------
        # PASO 5: Optimización de Ruta (A*) por Día
        # ---------------------------------------------------------
        final_itinerary = []
        hotel_id = hotel_attraction_id or city_center_attraction_id
        
        for day_idx, group in enumerate(daily_groups):
            day_num = day_idx + 1
            if not group:
                continue
                
            waypoints = [a['id'] for a in group]
            
            logger.info(f"Optimizando Día {day_num} con {len(waypoints)} paradas.")
            
            # Llamar a A* Multi-Stop
            route_result = self.optimizer_service.optimize_multi_stop(
                db=self.db,
                start_attraction_id=hotel_id,
                waypoints=waypoints,
                end_attraction_id=hotel_id, # Vuelta al hotel
                optimization_mode="balanced", # O usar profile 'pace' para decidir
                attraction_scores=scores_map # A* usa esto para preferir mejores scores
            )
            
            final_itinerary.append({
                "day": day_num,
                "date": None, # Calcular fecha real sumando días a start_date
                "route_summary": route_result['summary'],
                "attractions": route_result['attractions'],
                "segments": route_result['segments']
            })

        return {
            "itinerary_id": "temp_generated", # Podrías guardar en DB
            "profile_used": computed_profile,
            "days": final_itinerary
        }

    def _rank_candidates(self, candidates_data: List[Dict], profile: Dict) -> List[Dict]:
        """
        Puntúa y ordena los candidatos basándose en el perfil enriquecido.
        """
        scored_list = []
        
        # Extraer listas clave del perfil para búsqueda rápida O(1)
        priority_cats = set(profile.get('priority_categories', []))
        recommended_cats = set(profile.get('recommended_categories', []))
        avoid_cats = set(profile.get('avoid_categories', []))
        allowed_prices = set(profile.get('allowed_price_ranges', ['gratis', 'bajo', 'medio', 'alto']))
        required_amenities = set(profile.get('required_amenities', []))
        min_rating = profile.get('min_rating', 0.0)

        for item in candidates_data:
            attr = item['attraction'] # Datos de la atracción
            bfs_context = { # Datos del BFS (distancia, etc)
                'dist': item.get('distance_from_start_meters', 0)
            }
            
            score = 0.0
            
            # 1. Puntuación Base (Rating)
            # Rating 0-5 mapeado a 0-50 puntos
            rating = attr.get('rating') or 3.0 # Asumir 3.0 si es nulo
            score += (rating * 10)
            
            # 2. Match de Categoría
            cat = attr.get('category', '').lower()
            if cat in priority_cats:
                score += 30.0 # Gran bono si es prioritaria (ej: Mañana -> Cultural)
            elif cat in recommended_cats:
                score += 15.0 # Bono normal si es recomendada (ej: Interés -> Arte)
            elif cat in avoid_cats:
                score -= 50.0 # Penalización fuerte (ej: Lluvia -> Parque)
            
            # 3. Precio
            price = attr.get('price_range', '').lower()
            if price not in allowed_prices:
                score -= 100.0 # Descarte virtual (o penalización masiva)
            
            # 4. Accesibilidad / Amenidades
            # Si el perfil requiere algo y la atracción no lo tiene -> Penalización
            # (Asumiendo que attr tiene lista de amenities)
            attr_amenities = set(attr.get('amenities', []))
            missing_reqs = required_amenities - attr_amenities
            if missing_reqs:
                score -= (len(missing_reqs) * 40.0) # Penalización severa por cada req faltante
            
            # 5. Rating Mínimo (Regla Hard)
            if rating < min_rating:
                score -= 50.0
            
            # 6. Factor de Distancia (Tie-breaker)
            # Pequeña penalización por distancia para preferir lo cercano si hay empate
            score -= (bfs_context['dist'] / 1000.0) # -1 punto por km
            
            # Guardar resultado
            scored_list.append({
                'attraction': attr,
                'score': round(score, 2),
                'debug_info': f"Cat:{cat} | Rat:{rating}" # Útil para ver por qué ganó
            })
        
        # Ordenar descendente por score
        scored_list.sort(key=lambda x: x['score'], reverse=True)
        
        # Filtrar candidatos con score muy negativo (inviables)
        valid_candidates = [x for x in scored_list if x['score'] > -50.0]
        
        logger.info(f"Ranking completado: {len(valid_candidates)} candidatos viables de {len(candidates_data)}")
        return valid_candidates
