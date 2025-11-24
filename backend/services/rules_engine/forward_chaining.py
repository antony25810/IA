# backend/services/rules_engine/forward_chaining.py
"""
Motor de inferencia con encadenamiento hacia adelante (Forward Chaining)
Procesa reglas desde los hechos hacia las conclusiones
"""
from typing import Dict, List, Set, Optional
from copy import deepcopy

from .rules_base import Rule, RulesBase, RulePriority
from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class ForwardChainingEngine:
    """
    Motor de inferencia con Forward Chaining
    
    Algoritmo:
    1. Inicializar working memory con hechos iniciales
    2. Mientras haya reglas que puedan dispararse:
       a. Evaluar condiciones de todas las reglas
       b. Seleccionar reglas aplicables (conflict resolution)
       c. Ejecutar acción de la regla con mayor prioridad
       d. Actualizar working memory
       e. Marcar regla como ejecutada
    3. Retornar working memory final (estado enriquecido)
    """
    
    def __init__(
        self,
        rules: Optional[List[Rule]] = None,
        max_iterations: int = 100
    ):
        """
        Inicializar motor de inferencia
        
        Args:
            rules: Lista de reglas (si None, usa todas las reglas de RulesBase)
            max_iterations: Máximo de iteraciones para evitar loops infinitos
        """
        self.rules = rules if rules else RulesBase.get_all_rules()
        self.max_iterations = max_iterations
        self.executed_rules: Set[str] = set()
        self.iteration_count = 0
        
        # Ordenar reglas por prioridad
        self.rules.sort(key=lambda r: r.priority.value)
        
        logger.info(f"Motor de inferencia inicializado con {len(self.rules)} reglas")
    
    def infer(
        self,
        working_memory: Dict,
        enable_trace: bool = False
    ) -> Dict:
        """
        Ejecutar inferencia con forward chaining
        
        Args:
            working_memory: Memoria de trabajo (contexto inicial)
            enable_trace: Si True, guarda traza de ejecución
            
        Returns:
            Dict: Memoria de trabajo enriquecida
        """
        # Hacer copia profunda para no modificar el original
        wm = deepcopy(working_memory)
        
        # Inicializar metadatos
        wm['inference_metadata'] = {
            'iterations': 0,
            'rules_fired': 0,
            'execution_trace': [] if enable_trace else None
        }
        
        self.executed_rules = set()
        self.iteration_count = 0
        
        logger.info("Iniciando inferencia Forward Chaining")
        
        # ALGORITMO FORWARD CHAINING
        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            
            # MATCH: Encontrar reglas aplicables
            applicable_rules = self._match_rules(wm)
            
            if not applicable_rules:
                # No hay más reglas que disparar -> FIN
                logger.info(f"Inferencia completada en {self.iteration_count} iteraciones")
                break
            
            # CONFLICT RESOLUTION: Seleccionar regla a ejecutar
            selected_rule = self._resolve_conflict(applicable_rules)
            
            if selected_rule is None:
                logger.warning("No se pudo resolver conflicto de reglas")
                break
            
            # EXECUTE: Ejecutar acción de la regla
            wm = self._execute_rule(selected_rule, wm, enable_trace)
            
            # Marcar regla como ejecutada
            self.executed_rules.add(selected_rule.id)
            wm['inference_metadata']['rules_fired'] += 1
        
        # Actualizar metadatos finales
        wm['inference_metadata']['iterations'] = self.iteration_count
        wm['inference_metadata']['max_iterations_reached'] = (self.iteration_count >= self.max_iterations)
        
        if self.iteration_count >= self.max_iterations:
            logger.warning(f"Límite de iteraciones alcanzado ({self.max_iterations})")
        
        logger.info(
            f"Inferencia finalizada: {wm['inference_metadata']['rules_fired']} reglas ejecutadas "
            f"en {self.iteration_count} iteraciones"
        )
        
        return wm
    
    def _match_rules(self, working_memory: Dict) -> List[Rule]:
        """
        MATCH: Encontrar reglas cuyas condiciones se cumplen
        
        Args:
            working_memory: Memoria de trabajo actual
            
        Returns:
            List[Rule]: Reglas aplicables
        """
        applicable_rules = []
        
        for rule in self.rules:
            # Saltar si ya fue ejecutada
            if rule.id in self.executed_rules:
                continue
            
            try:
                # Evaluar condición
                if rule.condition(working_memory):
                    applicable_rules.append(rule)
                    logger.debug(f"Regla {rule.id} es aplicable")
            
            except Exception as e:
                logger.error(f"Error evaluando condición de regla {rule.id}: {str(e)}")
        
        return applicable_rules
    
    def _resolve_conflict(self, applicable_rules: List[Rule]) -> Optional[Rule]:
        """
        CONFLICT RESOLUTION: Seleccionar qué regla ejecutar
        
        Estrategia:
        1. Mayor prioridad (CRITICAL > HIGH > MEDIUM > LOW)
        2. Orden de definición (primera en la lista)
        
        Args:
            applicable_rules: Lista de reglas aplicables
            
        Returns:
            Optional[Rule]: Regla seleccionada o None
        """
        if not applicable_rules:
            return None
        
        # Ya están ordenadas por prioridad, tomar la primera
        selected = applicable_rules[0]
        
        logger.debug(
            f"Regla seleccionada: {selected.id} ({selected.name}) "
            f"- Prioridad: {selected.priority.name}"
        )
        
        return selected
    
    def _execute_rule(
        self,
        rule: Rule,
        working_memory: Dict,
        enable_trace: bool
    ) -> Dict:
        """
        EXECUTE: Ejecutar acción de la regla
        
        Args:
            rule: Regla a ejecutar
            working_memory: Memoria de trabajo
            enable_trace: Si guardar traza
            
        Returns:
            Dict: Memoria de trabajo actualizada
        """
        logger.info(f"Ejecutando regla: {rule.id} - {rule.name}")
        
        try:
            # Ejecutar acción
            wm = rule.action(working_memory)
            
            # Guardar traza si está habilitada
            if enable_trace and wm.get('inference_metadata', {}).get('execution_trace') is not None:
                wm['inference_metadata']['execution_trace'].append({
                    'iteration': self.iteration_count,
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'rule_category': rule.category,
                    'priority': rule.priority.name
                })
            
            logger.debug(f"Regla {rule.id} ejecutada exitosamente")
            
            return wm
        
        except Exception as e:
            logger.error(f"Error ejecutando regla {rule.id}: {str(e)}")
            # Retornar working memory sin cambios en caso de error
            return working_memory
    
    def infer_by_category(
        self,
        working_memory: Dict,
        category: str,
        enable_trace: bool = False
    ) -> Dict:
        """
        Ejecutar inferencia solo con reglas de una categoría específica
        
        Args:
            working_memory: Memoria de trabajo
            category: Categoría de reglas (profile, temporal, weather, validation)
            enable_trace: Si guardar traza
            
        Returns:
            Dict: Memoria de trabajo enriquecida
        """
        # Filtrar reglas por categoría
        category_rules = [r for r in self.rules if r.category == category]
        
        logger.info(f"Inferencia por categoría '{category}': {len(category_rules)} reglas")
        
        # Crear motor temporal con solo esas reglas
        temp_engine = ForwardChainingEngine(
            rules=category_rules,
            max_iterations=self.max_iterations
        )
        
        return temp_engine.infer(working_memory, enable_trace)
    
    def explain_rules(self, working_memory: Dict) -> List[Dict]:
        """
        Explicar qué reglas se aplicarían al contexto actual
        
        Args:
            working_memory: Memoria de trabajo
            
        Returns:
            List[Dict]: Lista de reglas aplicables con explicaciones
        """
        explanations = []
        
        for rule in self.rules:
            try:
                is_applicable = rule.condition(working_memory)
                
                explanations.append({
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'description': rule.description,
                    'priority': rule.priority.name,
                    'category': rule.category,
                    'is_applicable': is_applicable,
                    'already_executed': rule.id in self.executed_rules
                })
            
            except Exception as e:
                explanations.append({
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'description': rule.description,
                    'priority': rule.priority.name,
                    'category': rule.category,
                    'is_applicable': False,
                    'error': str(e)
                })
        
        return explanations
    
    def get_applicable_rules(self, working_memory: Dict) -> List[Rule]:
        """
        Obtener lista de reglas aplicables sin ejecutarlas
        
        Args:
            working_memory: Memoria de trabajo
            
        Returns:
            List[Rule]: Reglas aplicables
        """
        return self._match_rules(working_memory)
    
    def reset(self):
        """Reiniciar motor (limpiar reglas ejecutadas)"""
        self.executed_rules = set()
        self.iteration_count = 0
        logger.info("Motor de inferencia reiniciado")


class InferenceResult:
    """Resultado de la inferencia con metadatos"""
    
    def __init__(self, working_memory: Dict):
        """
        Inicializar resultado
        
        Args:
            working_memory: Memoria de trabajo enriquecida
        """
        self.working_memory = working_memory
        self.metadata = working_memory.get('inference_metadata', {})
    
    @property
    def computed_profile(self) -> Dict:
        """Obtener perfil computado"""
        return self.working_memory.get('computed_profile', {})
    
    @property
    def warnings(self) -> List[Dict]:
        """Obtener advertencias generadas"""
        return self.working_memory.get('warnings', [])
    
    @property
    def validation_errors(self) -> List[Dict]:
        """Obtener errores de validación"""
        return self.working_memory.get('validation_errors', [])
    
    @property
    def applied_rules(self) -> List[str]:
        """Obtener lista de reglas aplicadas"""
        return self.working_memory.get('applied_rules', [])
    
    @property
    def rules_fired_count(self) -> int:
        """Obtener cantidad de reglas ejecutadas"""
        return self.metadata.get('rules_fired', 0)
    
    @property
    def iterations_count(self) -> int:
        """Obtener cantidad de iteraciones"""
        return self.metadata.get('iterations', 0)
    
    @property
    def execution_trace(self) -> Optional[List[Dict]]:
        """Obtener traza de ejecución"""
        return self.metadata.get('execution_trace')
    
    def to_dict(self) -> Dict:
        """Convertir a diccionario"""
        return {
            'computed_profile': self.computed_profile,
            'warnings': self.warnings,
            'validation_errors': self.validation_errors,
            'applied_rules': self.applied_rules,
            'metadata': {
                'rules_fired': self.rules_fired_count,
                'iterations': self.iterations_count,
                'max_iterations_reached': self.metadata.get('max_iterations_reached', False)
            },
            'execution_trace': self.execution_trace
        }
    
    def has_warnings(self) -> bool:
        """Verificar si hay advertencias"""
        return len(self.warnings) > 0
    
    def has_errors(self) -> bool:
        """Verificar si hay errores de validación"""
        return len(self.validation_errors) > 0
    
    def is_valid(self) -> bool:
        """Verificar si el resultado es válido (sin errores críticos)"""
        return not self.has_errors()