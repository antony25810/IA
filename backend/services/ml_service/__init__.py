"""
═══════════════════════════════════════════════════════════════════════════════
                           ML SERVICE MODULE
═══════════════════════════════════════════════════════════════════════════════

Servicio de Machine Learning para scoring de atracciones usando redes neuronales.

Componentes:
- neural_network: Red neuronal PyTorch para scoring
- inference: Módulo de inferencia con cache
- dataset_loader: Carga y preparación de datos
- router: Endpoints de la API

═══════════════════════════════════════════════════════════════════════════════
"""

from .router import router as ml_router

__all__ = [
    "ml_router"
]
