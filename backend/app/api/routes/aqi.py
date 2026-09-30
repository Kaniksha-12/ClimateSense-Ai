"""Air Quality Index (AQI) API routes."""

from typing import Optional
from fastapi import APIRouter, Query
from app.schemas.aqi import AQIResponse
from app.services.aqi_service import aqi_service

router = APIRouter()


@router.get(
    "/aqi",
    response_model=AQIResponse,
    summary="Get Air Quality Index",
    description="Retrieve current AQI and pollutant concentrations (PM2.5, PM10, NO2, SO2, CO, O3).",
)
async def get_aqi(
    location: Optional[str] = Query(
        default=None,
        description="Optional location or station name to filter AQI reading",
    ),
) -> AQIResponse:
    """Return air quality metrics."""
    return aqi_service.get_current_aqi(location=location)
