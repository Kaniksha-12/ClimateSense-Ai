"""API v1 router aggregator."""

from fastapi import APIRouter
from app.api.routes import alerts, aqi, health, map as map_route, predictions, risk, weather

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(weather.router, tags=["Weather"])
api_router.include_router(aqi.router, tags=["Air Quality"])
api_router.include_router(predictions.router, tags=["Predictions"])
api_router.include_router(risk.router, tags=["Risk Assessment"])
api_router.include_router(map_route.router, tags=["GIS / Map"])
api_router.include_router(alerts.router, tags=["Alerts"])

__all__ = ["api_router"]
