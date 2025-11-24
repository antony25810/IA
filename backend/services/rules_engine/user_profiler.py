# backend/services/rules_engine/user_profiler.py
"""
Procesador de perfiles de usuario usando el motor de reglas
Enriquece perfiles con inferencias basadas en contexto
"""
from typing import Dict, List, Optional
from datetime import datetime

from .forward_chaining import ForwardChainingEngine, InferenceResult
from .rules_base import RulesBase
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class UserProfiler:
    """Procesador de perfiles de usuario con reglas de negocio"""
    
    def __init__(self):
        """Inicializar profiler"""
        self.engine = ForwardChainingEngine()
    
    def enrich_profile(
        self,
        user_profile: Dict,
        context: Optional[Dict] = None,
        enable_trace: bool = False
    ) -> InferenceResult:
        """
        Enriquecer perfil de usuario aplicando reglas
        
        Args:
            user_profile: Perfil del usuario
            context: Contexto adicional (fecha, hora, clima, etc.)
            enable_trace: Si guardar traza de ejecución
            
        Returns:
            InferenceResult: Perfil enriquecido con metadatos
        """
        logger.info(f"Enriqueciendo perfil de usuario: {user_profile.get('name', 'Unknown')}")
        
        # Construir working memory inicial
        working_memory = self._build_working_memory(user_profile, context)
        
        # Ejecutar inferencia solo con reglas de perfil
        wm_enriched = self.engine.infer_by_category(
            working_memory=working_memory,
            category='profile',
            enable_trace=enable_trace
        )
        
        # Aplicar también reglas temporales si hay contexto de tiempo
        if context and ('current_time' in context or 'current_date' in context):
            wm_enriched = self.engine.infer_by_category(
                working_memory=wm_enriched,
                category='temporal',
                enable_trace=enable_trace
            )
        
        # Aplicar reglas de clima si hay información meteorológica
        if context and 'weather' in context:
            wm_enriched = self.engine.infer_by_category(
                working_memory=wm_enriched,
                category='weather',
                enable_trace=enable_trace
            )
        
        result = InferenceResult(wm_enriched)
        
        logger.info(
            f"Perfil enriquecido: {result.rules_fired_count} reglas aplicadas "
            f"en {result.iterations_count} iteraciones"
        )
        
        return result
    
    def _build_working_memory(
        self,
        user_profile: Dict,
        context: Optional[Dict]
    ) -> Dict:
        """
        Construir memoria de trabajo inicial
        
        Args:
            user_profile: Perfil del usuario
            context: Contexto adicional
            
        Returns:
            Dict: Working memory inicial
        """
        wm = {
            # Datos del perfil
            'user_id': user_profile.get('user_id'),
            'name': user_profile.get('name'),
            'preferences': user_profile.get('preferences', {}),
            'budget_range': user_profile.get('budget_range'),
            'budget_min': user_profile.get('budget_min'),
            'budget_max': user_profile.get('budget_max'),
            'mobility_constraints': user_profile.get('mobility_constraints', {}),
            
            # Inicializar estructuras para inferencia
            'computed_profile': {},
            'warnings': [],
            'validation_errors': [],
            'applied_rules': []
        }
        
        # Agregar contexto si existe
        if context:
            wm.update(context)
        
        # Agregar timestamp si no existe
        if 'current_date' not in wm:
            wm['current_date'] = datetime.now()
        
        if 'current_time' not in wm:
            wm['current_time'] = datetime.now().time()
        
        return wm
    
    def validate_itinerary(
        self,
        itinerary: Dict,
        user_profile: Dict,
        enable_trace: bool = False
    ) -> InferenceResult:
        """
        Validar itinerario contra reglas de negocio
        
        Args:
            itinerary: Itinerario a validar
            user_profile: Perfil del usuario
            enable_trace: Si guardar traza
            
        Returns:
            InferenceResult: Resultado de validación
        """
        logger.info("Validando itinerario contra reglas de negocio")
        
        # Construir working memory
        working_memory = {
            'itinerary': itinerary,
            'budget_max': user_profile.get('budget_max'),
            'preferences': user_profile.get('preferences', {}),
            'warnings': [],
            'validation_errors': [],
            'applied_rules': []
        }
        
        # Ejecutar solo reglas de validación
        wm_validated = self.engine.infer_by_category(
            working_memory=working_memory,
            category='validation',
            enable_trace=enable_trace
        )
        
        result = InferenceResult(wm_validated)
        
        if result.has_errors():
            logger.warning(f"Itinerario tiene {len(result.validation_errors)} errores de validación")
        
        if result.has_warnings():
            logger.info(f"Itinerario tiene {len(result.warnings)} advertencias")
        
        return result
    
    def explain_profile_rules(self, user_profile: Dict, context: Optional[Dict] = None) -> List[Dict]:
        """
        Explicar qué reglas se aplicarían a un perfil
        
        Args:
            user_profile: Perfil del usuario
            context: Contexto adicional
            
        Returns:
            List[Dict]: Lista de reglas con explicaciones
        """
        working_memory = self._build_working_memory(user_profile, context)
        
        return self.engine.explain_rules(working_memory)
    
    def get_recommendations(
        self,
        user_profile: Dict,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Obtener recomendaciones basadas en el perfil enriquecido
        
        Args:
            user_profile: Perfil del usuario
            context: Contexto adicional
            
        Returns:
            Dict: Recomendaciones generadas
        """
        # Enriquecer perfil
        result = self.enrich_profile(user_profile, context)
        
        computed = result.computed_profile
        
        recommendations = {
            'recommended_categories': computed.get('recommended_categories', []),
            'priority_categories': computed.get('priority_categories', []),
            'avoid_categories': computed.get('avoid_categories', []),
            'max_daily_attractions': computed.get('max_daily_attractions', 5),
            'allowed_price_ranges': computed.get('allowed_price_ranges'),
            'min_rating': computed.get('min_rating'),
            'required_amenities': computed.get('required_amenities', []),
            'preferred_transport': computed.get('preferred_transport', []),
            'special_requirements': {
                'family_friendly': computed.get('family_friendly', False),
                'require_accessibility': computed.get('require_accessibility', False),
                'prefer_indoor': computed.get('prefer_indoor', False),
                'avoid_outdoor': computed.get('avoid_outdoor', False)
            }
        }
        
        return recommendations