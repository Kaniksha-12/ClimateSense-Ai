"""Weather response schema."""

from datetime import datetime
from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    """Schema for current weather observation response (Development / Test Baseline)."""

    location: str = Field(..., description="Location name or identifier")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    temperature: float = Field(..., description="Current temperature in Celsius")
    humidity: float = Field(..., description="Relative humidity percentage")
    rainfall: float = Field(..., description="Precipitation / rainfall in millimeters (mm)")
    wind_speed: float = Field(..., description="Wind speed in kilometers per hour (km/h)")
    pressure: float = Field(..., description="Atmospheric pressure in hectopascals (hPa)")
    timestamp: datetime = Field(..., description="Timestamp of the weather observation or test baseline")
