"""Weather service module.

Delegates data retrieval to the pluggable Data Provider interface,
allowing Member 1 (Data Collection & Preprocessing) to substitute
real-time or cleaned datasets seamlessly.
"""

from typing import Optional
from app.schemas.weather import WeatherResponse
from app.services.data_provider import get_data_provider


class WeatherService:
    """Service handling weather and rainfall retrieval."""

    @staticmethod
    def get_current_weather(location: Optional[str] = None) -> WeatherResponse:
        """Fetch current weather data from active data provider."""
        return get_data_provider().get_weather(location=location)


weather_service = WeatherService()
