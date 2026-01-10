# backend/services/external_apis/base.py
"""
Clase base para servicios de APIs externas con rate limiting y caché
"""
import asyncio
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from functools import wraps
import httpx

from shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class RateLimiter:
    """
    Rate limiter con ventana deslizante
    Evita exceder límites de APIs externas
    """
    def __init__(self, calls_per_minute: int = 60, calls_per_day: int = 1000):
        self.calls_per_minute = calls_per_minute
        self.calls_per_day = calls_per_day
        self.minute_calls: list = []
        self.day_calls: list = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Intentar adquirir permiso para hacer una llamada
        Returns: True si se permite, False si debe esperar
        """
        async with self._lock:
            now = datetime.now()
            
            # Limpiar llamadas antiguas
            minute_ago = now - timedelta(minutes=1)
            day_ago = now - timedelta(days=1)
            
            self.minute_calls = [t for t in self.minute_calls if t > minute_ago]
            self.day_calls = [t for t in self.day_calls if t > day_ago]
            
            # Verificar límites
            if len(self.minute_calls) >= self.calls_per_minute:
                logger.warning(f"Rate limit por minuto alcanzado: {len(self.minute_calls)}/{self.calls_per_minute}")
                return False
            
            if len(self.day_calls) >= self.calls_per_day:
                logger.warning(f"Rate limit diario alcanzado: {len(self.day_calls)}/{self.calls_per_day}")
                return False
            
            # Registrar llamada
            self.minute_calls.append(now)
            self.day_calls.append(now)
            return True
    
    async def wait_if_needed(self) -> None:
        """Esperar si es necesario antes de hacer una llamada"""
        while not await self.acquire():
            await asyncio.sleep(1)


class InMemoryCache:
    """
    Caché en memoria con TTL
    Para respuestas de APIs que no cambian frecuentemente
    """
    def __init__(self, default_ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl_seconds
        self._lock = asyncio.Lock()
    
    def _make_key(self, *args, **kwargs) -> str:
        """Crear key único basado en argumentos"""
        data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor del caché si existe y no expiró"""
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if datetime.now() < entry['expires_at']:
                    logger.debug(f"Cache HIT: {key[:16]}...")
                    return entry['value']
                else:
                    # Expirado, eliminar
                    del self.cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Guardar valor en caché"""
        async with self._lock:
            ttl = ttl_seconds or self.default_ttl
            self.cache[key] = {
                'value': value,
                'expires_at': datetime.now() + timedelta(seconds=ttl)
            }
            logger.debug(f"Cache SET: {key[:16]}... (TTL: {ttl}s)")
    
    async def clear_expired(self) -> int:
        """Limpiar entradas expiradas"""
        async with self._lock:
            now = datetime.now()
            expired_keys = [k for k, v in self.cache.items() if v['expires_at'] < now]
            for key in expired_keys:
                del self.cache[key]
            return len(expired_keys)
    
    @property
    def size(self) -> int:
        return len(self.cache)


class BaseExternalAPI(ABC):
    """
    Clase base abstracta para servicios de APIs externas
    Incluye rate limiting, caché y manejo de errores
    """
    
    def __init__(
        self, 
        api_key: str,
        base_url: str,
        calls_per_minute: int = 60,
        calls_per_day: int = 1000,
        cache_ttl_seconds: int = 3600,
        timeout_seconds: int = 30
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout_seconds
        
        # Rate limiter por API
        self.rate_limiter = RateLimiter(calls_per_minute, calls_per_day)
        
        # Caché compartido
        self.cache = InMemoryCache(cache_ttl_seconds)
        
        # Cliente HTTP async
        self.client = httpx.AsyncClient(timeout=timeout_seconds)
    
    @abstractmethod
    async def search_places(self, query: str, lat: float, lon: float, radius_meters: int) -> list:
        """Buscar lugares cerca de una ubicación"""
        pass
    
    @abstractmethod
    async def get_place_details(self, place_id: str) -> dict:
        """Obtener detalles de un lugar"""
        pass
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Realizar request con rate limiting y caché
        """
        url = f"{self.base_url}/{endpoint}"
        cache_key = self.cache._make_key(method, url, params)
        
        # Intentar obtener del caché
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Esperar si hay rate limiting
        await self.rate_limiter.wait_if_needed()
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, params=params)
            elif method.upper() == "POST":
                response = await self.client.post(url, json=params)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            
            response.raise_for_status()
            data = response.json()
            
            # Guardar en caché
            if use_cache:
                await self.cache.set(cache_key, data, cache_ttl)
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Error de conexión: {str(e)}")
            raise
    
    async def close(self):
        """Cerrar cliente HTTP"""
        await self.client.aclose()
