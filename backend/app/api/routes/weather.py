"""Weather API routes."""

from typing import Optional
from fastapi import APIRouter, Query
from app.schemas.weather import WeatherResponse
from app.services.weather_service import weather_service

router = APIRouter()


@router.get(
    "/weather",
    response_model=WeatherResponse,
    summary="Get Current Weather",
    description="Retrieve current atmospheric and rainfall observations. Returns baseline test data until live ingestion is connected.",
)
async def get_weather(
    location: Optional[str] = Query(
        default=None,
        description="Optional location or station name to filter observations",
    ),
) -> WeatherResponse:
    """Return current weather parameters."""
    return weather_service.get_current_weather(location=location)
