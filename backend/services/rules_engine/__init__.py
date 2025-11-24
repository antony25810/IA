# backend/services/rules_engine/__init__.py
"""
Módulo de motor de reglas con Forward Chaining
"""
from .service import RulesEngineService
from .router import router as rules_engine_router
from .forward_chaining import ForwardChainingEngine, InferenceResult
from .user_profiler import UserProfiler
from .rules_base import RulesBase, Rule, RulePriority

__all__ = [
    "RulesEngineService",
    "rules_engine_router",
    "ForwardChainingEngine",
    "InferenceResult",
    "UserProfiler",
    "RulesBase",
    "Rule",
    "RulePriority"
]