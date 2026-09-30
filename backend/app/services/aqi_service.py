"""Air Quality Index (AQI) service module.

Delegates environmental air quality retrieval to the pluggable Data Provider interface,
allowing Member 1 (Data Collection & Preprocessing) to substitute
real-time sensor feeds or preprocessed environmental data seamlessly.
"""

from typing import Optional
from app.schemas.aqi import AQIResponse
from app.services.data_provider import get_data_provider


class AQIService:
    """Service handling environmental air quality index and pollutant levels."""

    @staticmethod
    def get_current_aqi(location: Optional[str] = None) -> AQIResponse:
        """Fetch current AQI and pollutant concentrations from active data provider."""
        return get_data_provider().get_aqi(location=location)


aqi_service = AQIService()
