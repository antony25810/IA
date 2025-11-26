import logging
import sys
from shared.config.settings import get_settings

settings = get_settings()

def setup_logger(name: str) -> logging.Logger:
    """Configura y retorna un logger"""
    
    logger = logging.getLogger(name)
    
    # ✅ Evitar duplicar handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Handler para consola
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger