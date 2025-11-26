# backend/services/rules_engine/service.py
"""
Servicio para motor de reglas y procesamiento de perfiles
"""
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from .forward_chaining import ForwardChainingEngine, InferenceResult
from .user_profiler import UserProfiler
from .rules_base import RulesBase
from shared.database.models import UserProfile
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class RulesEngineService:
    """Servicio de motor de reglas"""
    
    @staticmethod
    def enrich_user_profile(
        db: Session,
        user_profile_id: int,
        context: Optional[Dict] = None,
        enable_trace: bool = False
    ) -> Dict:
        """
        Enriquecer perfil de usuario aplicando reglas
        
        Args:
            db: Sesión de base de datos
            user_profile_id: ID del perfil de usuario
            context: Contexto adicional (fecha, hora, clima)
            enable_trace: Si guardar traza de ejecución
            
        Returns:
            Dict: Perfil enriquecido con recomendaciones
        """
        try:
            # Obtener perfil de usuario
            user_profile = db.query(UserProfile).filter(
                UserProfile.id == user_profile_id
            ).first()
            
            if not user_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Perfil de usuario {user_profile_id} no encontrado"
                )
            
            # Convertir a diccionario
            profile_dict = {
                'user_id': str(user_profile.user_id),
                'name': user_profile.name,
                'preferences': user_profile.preferences or {},
                'budget_range': user_profile.budget_range,
                'budget_min': user_profile.budget_min,
                'budget_max': user_profile.budget_max,
                'mobility_constraints': user_profile.mobility_constraints or {}
            }
            
            # Agregar contexto por defecto si no se proporciona
            if context is None:
                context = {
                    'current_date': datetime.now(),
                    'current_time': datetime.now().time()
                }
            
            # Procesar con UserProfiler
            profiler = UserProfiler()
            result = profiler.enrich_profile(
                user_profile=profile_dict,
                context=context,
                enable_trace=enable_trace
            )
            
            logger.info(
                f"Perfil {user_profile_id} enriquecido: "
                f"{result.rules_fired_count} reglas aplicadas"
            )
            
            # Actualizar computed_profile en BD
            user_profile.computed_profile = result.computed_profile # type: ignore
            db.commit()
            
            # Construir respuesta
            return {
                'user_profile_id': user_profile_id,
                'original_profile': {
                    'name': user_profile.name,
                    'preferences': user_profile.preferences,
                    'budget_range': user_profile.budget_range
                },
                'computed_profile': result.computed_profile,
                'warnings': result.warnings,
                'validation_errors': result.validation_errors,
                'applied_rules': result.applied_rules,
                'metadata': {
                    'rules_fired': result.rules_fired_count,
                    'iterations': result.iterations_count
                },
                'execution_trace': result.execution_trace if enable_trace else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error enriqueciendo perfil {user_profile_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al enriquecer perfil: {str(e)}"
            )
    
    @staticmethod
    def validate_itinerary(
        db: Session,
        itinerary: Dict,
        user_profile_id: int,
        enable_trace: bool = False
    ) -> Dict:
        """
        Validar itinerario contra reglas de negocio
        
        Args:
            db: Sesión de base de datos
            itinerary: Itinerario a validar
            user_profile_id: ID del perfil de usuario
            enable_trace: Si guardar traza
            
        Returns:
            Dict: Resultado de validación
        """
        try:
            # Obtener perfil de usuario
            user_profile = db.query(UserProfile).filter(
                UserProfile.id == user_profile_id
            ).first()
            
            if not user_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Perfil de usuario {user_profile_id} no encontrado"
                )
            
            # Convertir a diccionario
            profile_dict = {
                'preferences': user_profile.preferences or {},
                'budget_max': user_profile.budget_max
            }
            
            # Validar con UserProfiler
            profiler = UserProfiler()
            result = profiler.validate_itinerary(
                itinerary=itinerary,
                user_profile=profile_dict,
                enable_trace=enable_trace
            )
            
            is_valid = result.is_valid()
            
            logger.info(
                f"Itinerario validado: {'VÁLIDO' if is_valid else 'INVÁLIDO'} "
                f"({len(result.validation_errors)} errores, {len(result.warnings)} advertencias)"
            )
            
            return {
                'is_valid': is_valid,
                'warnings': result.warnings,
                'validation_errors': result.validation_errors,
                'applied_rules': result.applied_rules,
                'metadata': {
                    'rules_fired': result.rules_fired_count,
                    'iterations': result.iterations_count
                },
                'execution_trace': result.execution_trace if enable_trace else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validando itinerario: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al validar itinerario: {str(e)}"
            )
    
    @staticmethod
    def explain_rules(
        db: Session,
        user_profile_id: int,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Explicar qué reglas se aplicarían a un perfil
        
        Args:
            db: Sesión de base de datos
            user_profile_id: ID del perfil de usuario
            context: Contexto adicional
            
        Returns:
            Dict: Explicación de reglas
        """
        try:
            # Obtener perfil
            user_profile = db.query(UserProfile).filter(
                UserProfile.id == user_profile_id
            ).first()
            
            if not user_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Perfil de usuario {user_profile_id} no encontrado"
                )
            
            # Convertir a diccionario
            profile_dict = {
                'preferences': user_profile.preferences or {},
                'budget_range': user_profile.budget_range,
                'budget_min': user_profile.budget_min,
                'budget_max': user_profile.budget_max,
                'mobility_constraints': user_profile.mobility_constraints or {}
            }
            
            # Agregar contexto
            if context is None:
                context = {
                    'current_date': datetime.now(),
                    'current_time': datetime.now().time()
                }
            
            # Explicar reglas
            profiler = UserProfiler()
            explanations = profiler.explain_profile_rules(profile_dict, context)
            
            # Agrupar por categoría
            by_category = {}
            applicable_count = 0
            
            for exp in explanations:
                category = exp['category']
                if category not in by_category:
                    by_category[category] = []
                
                by_category[category].append(exp)
                
                if exp['is_applicable']:
                    applicable_count += 1
            
            logger.info(
                f"Explicación de reglas para perfil {user_profile_id}: "
                f"{applicable_count}/{len(explanations)} aplicables"
            )
            
            return {
                'user_profile_id': user_profile_id,
                'total_rules': len(explanations),
                'applicable_rules': applicable_count,
                'rules_by_category': by_category,
                'all_rules': explanations
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error explicando reglas: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al explicar reglas: {str(e)}"
            )
    
    @staticmethod
    def get_recommendations(
        db: Session,
        user_profile_id: int,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Obtener recomendaciones basadas en reglas
        
        Args:
            db: Sesión de base de datos
            user_profile_id: ID del perfil de usuario
            context: Contexto adicional
            
        Returns:
            Dict: Recomendaciones generadas
        """
        try:
            # Obtener perfil
            user_profile = db.query(UserProfile).filter(
                UserProfile.id == user_profile_id
            ).first()
            
            if not user_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Perfil de usuario {user_profile_id} no encontrado"
                )
            
            # Convertir a diccionario
            profile_dict = {
                'preferences': user_profile.preferences or {},
                'budget_range': user_profile.budget_range,
                'budget_min': user_profile.budget_min,
                'budget_max': user_profile.budget_max,
                'mobility_constraints': user_profile.mobility_constraints or {}
            }
            
            # Agregar contexto
            if context is None:
                context = {
                    'current_date': datetime.now(),
                    'current_time': datetime.now().time()
                }
            
            # Obtener recomendaciones
            profiler = UserProfiler()
            recommendations = profiler.get_recommendations(profile_dict, context)
            
            logger.info(f"Recomendaciones generadas para perfil {user_profile_id}")
            
            return {
                'user_profile_id': user_profile_id,
                'recommendations': recommendations,
                'context': {
                    'date': str(context.get('current_date')),
                    'time': str(context.get('current_time'))
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generando recomendaciones: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al generar recomendaciones: {str(e)}"
            )
    
    @staticmethod
    def list_all_rules() -> Dict:
        """
        Listar todas las reglas disponibles
        
        Returns:
            Dict: Lista de reglas
        """
        try:
            all_rules = RulesBase.get_all_rules()
            
            rules_info = []
            by_category = {}
            
            for rule in all_rules:
                rule_info = {
                    'id': rule.id,
                    'name': rule.name,
                    'description': rule.description,
                    'priority': rule.priority.name,
                    'category': rule.category
                }
                
                rules_info.append(rule_info)
                
                # Agrupar por categoría
                if rule.category not in by_category:
                    by_category[rule.category] = []
                by_category[rule.category].append(rule_info)
            
            return {
                'total_rules': len(all_rules),
                'categories': list(by_category.keys()),
                'rules_by_category': by_category,
                'all_rules': rules_info
            }
            
        except Exception as e:
            logger.error(f"Error listando reglas: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al listar reglas: {str(e)}"
            )