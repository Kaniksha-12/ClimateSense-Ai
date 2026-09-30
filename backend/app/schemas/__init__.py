"""Pydantic schemas package for ClimateSense AI."""

from app.schemas.alerts import AlertResponse
from app.schemas.aqi import AQIResponse
from app.schemas.health import HealthResponse
from app.schemas.map import GeoJSONFeature, GeoJSONGeometry, RiskMapResponse
from app.schemas.predictions import PredictionResponse
from app.schemas.risk import RiskResponse
from app.schemas.weather import WeatherResponse

__all__ = [
    "AlertResponse",
    "AQIResponse",
    "GeoJSONFeature",
    "GeoJSONGeometry",
    "HealthResponse",
    "PredictionResponse",
    "RiskMapResponse",
    "RiskResponse",
    "WeatherResponse",
]
