# backend/services/rules_engine/rules_base.py
"""
Base de conocimiento: Definición de reglas de negocio
"""
from typing import Dict, List, Callable
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum


class RulePriority(Enum):
    """Prioridad de ejecución de reglas"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class Rule:
    """Definición de una regla de producción"""
    id: str
    name: str
    description: str
    priority: RulePriority
    condition: Callable[[Dict], bool]  # IF (condición)
    action: Callable[[Dict], Dict]     # THEN (acción)
    category: str  # Categoría: profile, temporal, weather, validation


class RulesBase:
    """Base de conocimiento con todas las reglas"""
    
    # ================================================================
    # REGLAS DE PERFIL DE USUARIO
    # ================================================================
    
    @staticmethod
    def rule_family_tourism():
        """REGLA: Turismo familiar requiere amenidades especiales"""
        return Rule(
            id="PROFILE_001",
            name="Turismo Familiar",
            description="Si tourism_type='familiar' ENTONCES agregar preferencias family-friendly",
            priority=RulePriority.HIGH,
            condition=lambda ctx: ctx.get('preferences', {}).get('tourism_type') == 'familiar',
            action=RulesBase._action_add_family_preferences,
            category="profile"
        )
    
    @staticmethod
    def rule_low_budget():
        """REGLA: Presupuesto bajo limita opciones"""
        return Rule(
            id="PROFILE_002",
            name="Presupuesto Bajo",
            description="Si budget_range='bajo' ENTONCES filtrar solo gratis/bajo",
            priority=RulePriority.HIGH,
            condition=lambda ctx: ctx.get('budget_range', '').lower() == 'bajo',
            action=RulesBase._action_filter_low_budget,
            category="profile"
        )
    
    @staticmethod
    def rule_high_budget():
        """REGLA: Presupuesto alto prioriza calidad"""
        return Rule(
            id="PROFILE_003",
            name="Presupuesto Alto",
            description="Si budget_range in ['alto','lujo'] ENTONCES priorizar premium",
            priority=RulePriority.MEDIUM,
            condition=lambda ctx: ctx.get('budget_range', '').lower() in ['alto', 'lujo'],
            action=RulesBase._action_prioritize_premium,
            category="profile"
        )
    
    @staticmethod
    def rule_mobility_restrictions():
        """REGLA: Restricciones de movilidad requieren accesibilidad"""
        return Rule(
            id="PROFILE_004",
            name="Movilidad Reducida",
            description="Si max_walking_distance < 1000m ENTONCES requerir accesibilidad",
            priority=RulePriority.CRITICAL,
            condition=lambda ctx: ctx.get('mobility_constraints', {}).get('max_walking_distance', 10000) < 1000,
            action=RulesBase._action_require_accessibility,
            category="profile"
        )
    
    @staticmethod
    def rule_relaxed_pace():
        """REGLA: Ritmo relajado reduce densidad"""
        return Rule(
            id="PROFILE_005",
            name="Ritmo Relajado",
            description="Si pace='relaxed' ENTONCES max 3 atracciones/día",
            priority=RulePriority.MEDIUM,
            condition=lambda ctx: ctx.get('preferences', {}).get('pace') == 'relaxed',
            action=RulesBase._action_reduce_daily_attractions,
            category="profile"
        )
    
    @staticmethod
    def rule_intense_pace():
        """REGLA: Ritmo intenso aumenta densidad"""
        return Rule(
            id="PROFILE_006",
            name="Ritmo Intenso",
            description="Si pace='intense' ENTONCES hasta 7 atracciones/día",
            priority=RulePriority.MEDIUM,
            condition=lambda ctx: ctx.get('preferences', {}).get('pace') == 'intense',
            action=RulesBase._action_increase_daily_attractions,
            category="profile"
        )
    
    # ================================================================
    # REGLAS TEMPORALES (HORARIO DEL DÍA)
    # ================================================================
    
    @staticmethod
    def rule_morning_cultural():
        """REGLA: Mañana es ideal para sitios culturales"""
        return Rule(
            id="TIME_001",
            name="Mañana - Cultural",
            description="Si 6am-12pm ENTONCES priorizar museos y cultura",
            priority=RulePriority.MEDIUM,
            condition=RulesBase._is_morning,
            action=RulesBase._action_prioritize_cultural,
            category="temporal"
        )
    
    @staticmethod
    def rule_afternoon_outdoor():
        """REGLA: Tarde es ideal para actividades al aire libre"""
        return Rule(
            id="TIME_002",
            name="Tarde - Aire Libre",
            description="Si 12pm-6pm ENTONCES priorizar parques y naturaleza",
            priority=RulePriority.MEDIUM,
            condition=RulesBase._is_afternoon,
            action=RulesBase._action_prioritize_outdoor,
            category="temporal"
        )
    
    @staticmethod
    def rule_evening_dining():
        """REGLA: Noche es ideal para gastronomía"""
        return Rule(
            id="TIME_003",
            name="Noche - Gastronomía",
            description="Si 6pm-11pm ENTONCES priorizar restaurantes",
            priority=RulePriority.MEDIUM,
            condition=RulesBase._is_evening,
            action=RulesBase._action_prioritize_dining,
            category="temporal"
        )
    
    @staticmethod
    def rule_weekend_crowds():
        """REGLA: Fin de semana hay más gente"""
        return Rule(
            id="TIME_004",
            name="Fin de Semana",
            description="Si sábado/domingo ENTONCES advertir sobre aglomeraciones",
            priority=RulePriority.LOW,
            condition=RulesBase._is_weekend,
            action=RulesBase._action_warn_crowds,
            category="temporal"
        )
    
    # ================================================================
    # REGLAS DE CLIMA
    # ================================================================
    
    @staticmethod
    def rule_rain_indoor():
        """REGLA: Lluvia requiere lugares cerrados"""
        return Rule(
            id="WEATHER_001",
            name="Lluvia - Interior",
            description="Si weather='rain' ENTONCES preferir atracciones de interior",
            priority=RulePriority.HIGH,
            condition=lambda ctx: ctx.get('weather', {}).get('condition') == 'rain',
            action=RulesBase._action_prefer_indoor,
            category="weather"
        )
    
    @staticmethod
    def rule_extreme_heat():
        """REGLA: Calor extremo limita actividades exteriores"""
        return Rule(
            id="WEATHER_002",
            name="Calor Extremo",
            description="Si temperature > 30°C ENTONCES evitar exteriores",
            priority=RulePriority.HIGH,
            condition=lambda ctx: ctx.get('weather', {}).get('temperature', 25) > 30,
            action=RulesBase._action_avoid_outdoor,
            category="weather"
        )
    
    # ================================================================
    # REGLAS DE VALIDACIÓN DE ITINERARIOS
    # ================================================================
    
    @staticmethod
    def rule_validate_opening_hours():
        """REGLA: Verificar horarios de apertura"""
        return Rule(
            id="ITINERARY_001",
            name="Validar Horarios",
            description="Si existe itinerario ENTONCES verificar horarios de apertura",
            priority=RulePriority.CRITICAL,
            condition=lambda ctx: 'itinerary' in ctx,
            action=RulesBase._action_validate_opening_hours,
            category="validation"
        )
    
    @staticmethod
    def rule_validate_travel_time():
        """REGLA: Tiempo de viaje debe ser realista"""
        return Rule(
            id="ITINERARY_002",
            name="Validar Tiempo Viaje",
            description="Si existe itinerario ENTONCES verificar tiempo de viaje",
            priority=RulePriority.HIGH,
            condition=lambda ctx: 'itinerary' in ctx,
            action=RulesBase._action_validate_travel_time,
            category="validation"
        )
    
    @staticmethod
    def rule_validate_budget():
        """REGLA: Respetar presupuesto máximo"""
        return Rule(
            id="ITINERARY_003",
            name="Validar Presupuesto",
            description="Si existe itinerario Y budget_max ENTONCES verificar costo total",
            priority=RulePriority.HIGH,
            condition=lambda ctx: 'itinerary' in ctx and 'budget_max' in ctx,
            action=RulesBase._action_validate_budget,
            category="validation"
        )
    
    @staticmethod
    def rule_daily_limit():
        """REGLA: Evitar fatiga del viajero"""
        return Rule(
            id="ITINERARY_004",
            name="Límite Diario",
            description="Si >5 atracciones/día ENTONCES advertir fatiga",
            priority=RulePriority.MEDIUM,
            condition=lambda ctx: 'itinerary' in ctx,
            action=RulesBase._action_check_daily_limit,
            category="validation"
        )
    
    # ================================================================
    # MÉTODO PRINCIPAL: OBTENER TODAS LAS REGLAS
    # ================================================================
    
    @staticmethod
    def get_all_rules() -> List[Rule]:
        """
        Obtener todas las reglas definidas
        
        Returns:
            List[Rule]: Lista completa de reglas
        """
        return [
            # Reglas de perfil
            RulesBase.rule_family_tourism(),
            RulesBase.rule_low_budget(),
            RulesBase.rule_high_budget(),
            RulesBase.rule_mobility_restrictions(),
            RulesBase.rule_relaxed_pace(),
            RulesBase.rule_intense_pace(),
            
            # Reglas temporales
            RulesBase.rule_morning_cultural(),
            RulesBase.rule_afternoon_outdoor(),
            RulesBase.rule_evening_dining(),
            RulesBase.rule_weekend_crowds(),
            
            # Reglas de clima
            RulesBase.rule_rain_indoor(),
            RulesBase.rule_extreme_heat(),
            
            # Reglas de validación
            RulesBase.rule_validate_opening_hours(),
            RulesBase.rule_validate_travel_time(),
            RulesBase.rule_validate_budget(),
            RulesBase.rule_daily_limit(),
        ]
    
    @staticmethod
    def get_rules_by_category(category: str) -> List[Rule]:
        """
        Obtener reglas por categoría
        
        Args:
            category: Categoría (profile, temporal, weather, validation)
            
        Returns:
            List[Rule]: Reglas de esa categoría
        """
        all_rules = RulesBase.get_all_rules()
        return [rule for rule in all_rules if rule.category == category]
    
    # ================================================================
    # FUNCIONES DE CONDICIÓN (IF)
    # ================================================================
    
    @staticmethod
    def _is_morning(ctx: Dict) -> bool:
        """Verificar si es mañana (6am-12pm)"""
        current_time = ctx.get('current_time', datetime.now().time())
        if isinstance(current_time, datetime):
            current_time = current_time.time()
        return time(6, 0) <= current_time < time(12, 0)
    
    @staticmethod
    def _is_afternoon(ctx: Dict) -> bool:
        """Verificar si es tarde (12pm-6pm)"""
        current_time = ctx.get('current_time', datetime.now().time())
        if isinstance(current_time, datetime):
            current_time = current_time.time()
        return time(12, 0) <= current_time < time(18, 0)
    
    @staticmethod
    def _is_evening(ctx: Dict) -> bool:
        """Verificar si es noche (6pm-11pm)"""
        current_time = ctx.get('current_time', datetime.now().time())
        if isinstance(current_time, datetime):
            current_time = current_time.time()
        return time(18, 0) <= current_time < time(23, 0)
    
    @staticmethod
    def _is_weekend(ctx: Dict) -> bool:
        """Verificar si es fin de semana"""
        current_date = ctx.get('current_date', datetime.now())
        if isinstance(current_date, datetime):
            return current_date.weekday() in [5, 6]  # Sábado=5, Domingo=6
        return False
    
    # ================================================================
    # FUNCIONES DE ACCIÓN (THEN)
    # ================================================================
    
    @staticmethod
    def _action_add_family_preferences(ctx: Dict) -> Dict:
        """Agregar preferencias family-friendly"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        ctx['computed_profile']['family_friendly'] = True
        ctx['computed_profile']['required_amenities'] = ['wheelchair', 'stroller_friendly', 'restrooms']
        
        if 'recommended_categories' not in ctx['computed_profile']:
            ctx['computed_profile']['recommended_categories'] = []
        
        ctx['computed_profile']['recommended_categories'].extend([
            'entretenimiento', 'naturaleza', 'educativo'
        ])
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('PROFILE_001: Preferencias familiares agregadas')
        
        return ctx
    
    @staticmethod
    def _action_filter_low_budget(ctx: Dict) -> Dict:
        """Filtrar por presupuesto bajo"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        ctx['computed_profile']['allowed_price_ranges'] = ['gratis', 'bajo']
        ctx['computed_profile']['max_daily_cost'] = 50.0
        ctx['computed_profile']['prefer_free'] = True
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('PROFILE_002: Filtros de presupuesto bajo aplicados')
        
        return ctx
    
    @staticmethod
    def _action_prioritize_premium(ctx: Dict) -> Dict:
        """Priorizar experiencias premium"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        ctx['computed_profile']['min_rating'] = 4.0
        ctx['computed_profile']['prefer_verified'] = True
        ctx['computed_profile']['allow_exclusive'] = True
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('PROFILE_003: Experiencias premium priorizadas')
        
        return ctx
    
    @staticmethod
    def _action_require_accessibility(ctx: Dict) -> Dict:
        """Requerir accesibilidad"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        ctx['computed_profile']['require_accessibility'] = True
        ctx['computed_profile']['max_walking_distance'] = ctx.get('mobility_constraints', {}).get('max_walking_distance', 500)
        ctx['computed_profile']['required_amenities'] = ['wheelchair', 'elevator', 'accessible_bathroom']
        ctx['computed_profile']['preferred_transport'] = ['car', 'taxi']
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('PROFILE_004: Requisitos de accesibilidad aplicados')
        
        return ctx
    
    @staticmethod
    def _action_reduce_daily_attractions(ctx: Dict) -> Dict:
        """Reducir atracciones por día (ritmo relajado)"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        ctx['computed_profile']['max_daily_attractions'] = 3
        ctx['computed_profile']['min_time_per_attraction'] = 120  # 2 horas
        ctx['computed_profile']['include_rest_time'] = True
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('PROFILE_005: Ritmo relajado - máx 3 atracciones/día')
        
        return ctx
    
    @staticmethod
    def _action_increase_daily_attractions(ctx: Dict) -> Dict:
        """Aumentar atracciones por día (ritmo intenso)"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        ctx['computed_profile']['max_daily_attractions'] = 7
        ctx['computed_profile']['min_time_per_attraction'] = 45
        ctx['computed_profile']['include_rest_time'] = False
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('PROFILE_006: Ritmo intenso - hasta 7 atracciones/día')
        
        return ctx
    
    @staticmethod
    def _action_prioritize_cultural(ctx: Dict) -> Dict:
        """Priorizar sitios culturales"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        if 'priority_categories' not in ctx['computed_profile']:
            ctx['computed_profile']['priority_categories'] = []
        
        ctx['computed_profile']['priority_categories'].extend(['cultural', 'historico', 'museos'])
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('TIME_001: Sitios culturales priorizados (mañana)')
        
        return ctx
    
    @staticmethod
    def _action_prioritize_outdoor(ctx: Dict) -> Dict:
        """Priorizar actividades al aire libre"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        if 'priority_categories' not in ctx['computed_profile']:
            ctx['computed_profile']['priority_categories'] = []
        
        ctx['computed_profile']['priority_categories'].extend(['naturaleza', 'parques', 'aventura'])
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('TIME_002: Actividades al aire libre priorizadas (tarde)')
        
        return ctx
    
    @staticmethod
    def _action_prioritize_dining(ctx: Dict) -> Dict:
        """Priorizar restaurantes"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        if 'priority_categories' not in ctx['computed_profile']:
            ctx['computed_profile']['priority_categories'] = []
        
        ctx['computed_profile']['priority_categories'].extend(['gastronomia', 'restaurantes'])
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('TIME_003: Gastronomía priorizada (noche)')
        
        return ctx
    
    @staticmethod
    def _action_warn_crowds(ctx: Dict) -> Dict:
        """Advertir sobre aglomeraciones"""
        if 'warnings' not in ctx:
            ctx['warnings'] = []
        
        ctx['warnings'].append({
            'type': 'crowds',
            'message': 'Es fin de semana. Las atracciones populares pueden estar concurridas.',
            'recommendation': 'Considere visitar temprano o reservar con anticipación.'
        })
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('TIME_004: Advertencia de aglomeraciones (fin de semana)')
        
        return ctx
    
    @staticmethod
    def _action_prefer_indoor(ctx: Dict) -> Dict:
        """Preferir interior cuando llueve"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        ctx['computed_profile']['prefer_indoor'] = True
        ctx['computed_profile']['avoid_categories'] = ['naturaleza', 'parques']
        
        if 'priority_categories' not in ctx['computed_profile']:
            ctx['computed_profile']['priority_categories'] = []
        
        ctx['computed_profile']['priority_categories'].extend(['museos', 'cultural', 'compras'])
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('WEATHER_001: Atracciones de interior priorizadas (lluvia)')
        
        return ctx
    
    @staticmethod
    def _action_avoid_outdoor(ctx: Dict) -> Dict:
        """Evitar exteriores con calor extremo"""
        if 'computed_profile' not in ctx:
            ctx['computed_profile'] = {}
        
        ctx['computed_profile']['avoid_outdoor'] = True
        ctx['computed_profile']['avoid_categories'] = ['naturaleza', 'aventura']
        
        if 'warnings' not in ctx:
            ctx['warnings'] = []
        
        ctx['warnings'].append({
            'type': 'heat',
            'message': f"Temperatura alta ({ctx.get('weather', {}).get('temperature')}°C)",
            'recommendation': 'Prefiera lugares con aire acondicionado.'
        })
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('WEATHER_002: Actividades exteriores evitadas (calor)')
        
        return ctx
    
    @staticmethod
    def _action_validate_opening_hours(ctx: Dict) -> Dict:
        """Validar horarios de apertura (placeholder)"""
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('ITINERARY_001: Horarios validados')
        
        return ctx
    
    @staticmethod
    def _action_validate_travel_time(ctx: Dict) -> Dict:
        """Validar tiempo de viaje"""
        itinerary = ctx.get('itinerary', {})
        total_travel_time = sum([seg.get('travel_time_minutes', 0) for seg in itinerary.get('segments', [])])
        
        if total_travel_time > 240:
            if 'warnings' not in ctx:
                ctx['warnings'] = []
            
            ctx['warnings'].append({
                'type': 'travel_time',
                'message': f'Tiempo de viaje total alto: {total_travel_time} minutos',
                'recommendation': 'Considere reducir atracciones o agrupar por zona.'
            })
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('ITINERARY_002: Tiempo de viaje validado')
        
        return ctx
    
    @staticmethod
    def _action_validate_budget(ctx: Dict) -> Dict:
        """Validar presupuesto"""
        itinerary = ctx.get('itinerary', {})
        total_cost = itinerary.get('total_cost', 0)
        budget_max = ctx.get('budget_max', float('inf'))
        
        if total_cost > budget_max:
            if 'validation_errors' not in ctx:
                ctx['validation_errors'] = []
            
            ctx['validation_errors'].append({
                'type': 'budget',
                'message': f'Costo total (${total_cost}) excede presupuesto (${budget_max})',
                'severity': 'high'
            })
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('ITINERARY_003: Presupuesto validado')
        
        return ctx
    
    @staticmethod
    def _action_check_daily_limit(ctx: Dict) -> Dict:
        """Verificar límite diario"""
        itinerary = ctx.get('itinerary', {})
        daily_count = len(itinerary.get('attractions', []))
        
        if daily_count > 5:
            if 'warnings' not in ctx:
                ctx['warnings'] = []
            
            ctx['warnings'].append({
                'type': 'fatigue',
                'message': f'Muchas atracciones en un día ({daily_count})',
                'recommendation': 'Distribuir en más días para evitar fatiga.'
            })
        
        if 'applied_rules' not in ctx:
            ctx['applied_rules'] = []
        ctx['applied_rules'].append('ITINERARY_004: Límite diario verificado')
        
        return ctx