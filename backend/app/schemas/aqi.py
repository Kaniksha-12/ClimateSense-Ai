"""Air Quality Index (AQI) response schema."""

from datetime import datetime
from pydantic import BaseModel, Field


class AQIResponse(BaseModel):
    """Schema for Air Quality Index and pollutant concentrations (Development / Test Baseline)."""

    location: str = Field(..., description="Location name or station identifier")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    aqi: int = Field(..., description="Air Quality Index value")
    pm25: float = Field(..., description="Particulate Matter PM2.5 in µg/m³")
    pm10: float = Field(..., description="Particulate Matter PM10 in µg/m³")
    no2: float = Field(..., description="Nitrogen Dioxide in µg/m³")
    so2: float = Field(..., description="Sulfur Dioxide in µg/m³")
    co: float = Field(..., description="Carbon Monoxide in mg/m³")
    o3: float = Field(..., description="Ozone in µg/m³")
    timestamp: datetime = Field(..., description="Timestamp of the AQI reading or test baseline")
