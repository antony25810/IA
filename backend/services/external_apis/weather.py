# backend/services/external_apis/weather.py
"""
Servicio de integración con OpenWeatherMap API
"""
from typing import Dict, Optional, Any, List
from datetime import datetime
from .base import BaseExternalAPI
from shared.utils.logger import setup_logger
from shared.config.settings import settings

logger = setup_logger(__name__)


class WeatherService(BaseExternalAPI):
    """
    Cliente para OpenWeatherMap API
    Documentación: https://openweathermap.org/api
    
    Límites (plan gratuito):
    - 1000 requests/día
    - 60 requests/minuto
    
    Uso: Datos de clima en tiempo real para el motor de reglas
    """
    
    # Mapeo de condiciones a categorías internas
    CONDITION_MAP = {
        "Thunderstorm": "storm",
        "Drizzle": "rain",
        "Rain": "rain",
        "Snow": "snow",
        "Clear": "sunny",
        "Clouds": "cloudy",
        "Mist": "foggy",
        "Fog": "foggy",
        "Haze": "hazy"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            api_key=api_key or settings.OPENWEATHER_API_KEY,
            base_url="https://api.openweathermap.org/data/2.5",
            calls_per_minute=55,
            calls_per_day=900,
            cache_ttl_seconds=1800,  # 30 minutos (clima cambia)
            timeout_seconds=10
        )
    
    async def search_places(self, query: str, lat: float, lon: float, radius_meters: int) -> list:
        """No aplica para weather API"""
        return []
    
    async def get_place_details(self, place_id: str) -> dict:
        """No aplica para weather API"""
        return {}
    
    async def get_current_weather(
        self,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """
        Obtener clima actual
        
        Args:
            lat: Latitud
            lon: Longitud
        
        Returns:
            Diccionario con datos de clima
        """
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "es"
        }
        
        try:
            data = await self._make_request(
                "GET",
                "weather",
                params,
                cache_ttl=1800  # 30 min
            )
            
            return self._parse_current_weather(data)
            
        except Exception as e:
            logger.error(f"Error obteniendo clima: {str(e)}")
            return self._get_default_weather()
    
    async def get_forecast(
        self,
        lat: float,
        lon: float,
        days: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Obtener pronóstico de 5 días
        """
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "es",
            "cnt": min(days * 8, 40)  # 8 datos por día (cada 3 horas)
        }
        
        try:
            data = await self._make_request(
                "GET",
                "forecast",
                params,
                cache_ttl=3600  # 1 hora
            )
            
            forecasts = data.get("list", [])
            return [self._parse_forecast_item(item) for item in forecasts]
            
        except Exception as e:
            logger.error(f"Error obteniendo pronóstico: {str(e)}")
            return []
    
    async def get_weather_for_date(
        self,
        lat: float,
        lon: float,
        target_date: datetime
    ) -> Dict[str, Any]:
        """
        Obtener clima estimado para una fecha específica
        Útil para planificación de itinerarios
        """
        forecasts = await self.get_forecast(lat, lon, days=5)
        
        # Buscar pronóstico más cercano a la fecha objetivo
        target_ts = target_date.timestamp()
        closest = None
        min_diff = float('inf')
        
        for forecast in forecasts:
            dt = forecast.get("datetime")
            if dt:
                diff = abs(dt.timestamp() - target_ts)
                if diff < min_diff:
                    min_diff = diff
                    closest = forecast
        
        return closest or self._get_default_weather()
    
    def _parse_current_weather(self, data: Dict) -> Dict[str, Any]:
        """Parsear respuesta de clima actual"""
        weather = data.get("weather", [{}])[0]
        main = data.get("main", {})
        wind = data.get("wind", {})
        
        condition_raw = weather.get("main", "Clear")
        
        return {
            "condition": self.CONDITION_MAP.get(condition_raw, "sunny"),
            "condition_raw": condition_raw,
            "description": weather.get("description", ""),
            "temperature": main.get("temp"),
            "feels_like": main.get("feels_like"),
            "temp_min": main.get("temp_min"),
            "temp_max": main.get("temp_max"),
            "humidity": main.get("humidity"),
            "wind_speed": wind.get("speed"),  # m/s
            "wind_speed_kmh": round((wind.get("speed", 0) * 3.6), 1),
            "clouds_percent": data.get("clouds", {}).get("all", 0),
            "visibility_meters": data.get("visibility"),
            "sunrise": datetime.fromtimestamp(data.get("sys", {}).get("sunrise", 0)),
            "sunset": datetime.fromtimestamp(data.get("sys", {}).get("sunset", 0)),
            "timestamp": datetime.now(),
            "is_outdoor_friendly": self._is_outdoor_friendly(condition_raw, main)
        }
    
    def _parse_forecast_item(self, item: Dict) -> Dict[str, Any]:
        """Parsear item de pronóstico"""
        weather = item.get("weather", [{}])[0]
        main = item.get("main", {})
        
        return {
            "datetime": datetime.fromtimestamp(item.get("dt", 0)),
            "condition": self.CONDITION_MAP.get(weather.get("main", "Clear"), "sunny"),
            "description": weather.get("description", ""),
            "temperature": main.get("temp"),
            "feels_like": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "pop": item.get("pop", 0)  # Probabilidad de precipitación
        }
    
    def _is_outdoor_friendly(self, condition: str, main: Dict) -> bool:
        """
        Determinar si el clima es apto para actividades al aire libre
        Útil para el motor de reglas
        """
        bad_conditions = ["Thunderstorm", "Rain", "Snow", "Fog"]
        temp = main.get("temp", 25)
        
        if condition in bad_conditions:
            return False
        if temp < 10 or temp > 35:
            return False
        
        return True
    
    def _get_default_weather(self) -> Dict[str, Any]:
        """Clima por defecto si la API falla"""
        return {
            "condition": "sunny",
            "condition_raw": "Clear",
            "description": "Cielo despejado",
            "temperature": 25,
            "feels_like": 25,
            "humidity": 50,
            "wind_speed_kmh": 10,
            "is_outdoor_friendly": True,
            "timestamp": datetime.now(),
            "is_default": True
        }
    
    async def get_weather_context_for_rules(
        self,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """
        Obtener contexto de clima formateado para el motor de reglas
        """
        weather = await self.get_current_weather(lat, lon)
        
        return {
            "weather": {
                "condition": weather.get("condition"),
                "temperature": weather.get("temperature"),
                "is_outdoor_friendly": weather.get("is_outdoor_friendly"),
                "humidity": weather.get("humidity"),
                "wind_kmh": weather.get("wind_speed_kmh")
            }
        }
