"""Data provider interface module.

Provides a clean abstract contract and development/test implementation
for weather, rainfall, and air quality environmental datasets.
Member 1 (Data Collection & Preprocessing) can connect real-time streams
or processed batch datasets by implementing BaseDataProvider.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from app.schemas.aqi import AQIResponse
from app.schemas.weather import WeatherResponse


class BaseDataProvider(ABC):
    """Abstract interface defining data acquisition for weather and air quality."""

    @abstractmethod
    def get_weather(self, location: Optional[str] = None) -> WeatherResponse:
        """Fetch current or preprocessed weather metrics for a designated location."""
        pass

    @abstractmethod
    def get_aqi(self, location: Optional[str] = None) -> AQIResponse:
        """Fetch current or preprocessed AQI and pollutant concentrations."""
        pass


class DevTestDataProvider(BaseDataProvider):
    """Development and test baseline provider.

    Returns deterministic baseline records until Member 1 links real data sources.
    """

    def get_weather(self, location: Optional[str] = None) -> WeatherResponse:
        """Provide baseline atmospheric observations."""
        target_location = location or "Default Station (Dev/Test)"
        return WeatherResponse(
            location=target_location,
            latitude=28.6139,
            longitude=77.2090,
            temperature=29.5,
            humidity=62.0,
            rainfall=14.2,
            wind_speed=18.5,
            pressure=1012.3,
            timestamp=datetime.now(timezone.utc),
        )

    def get_aqi(self, location: Optional[str] = None) -> AQIResponse:
        """Provide baseline air quality measurements."""
        target_location = location or "Default Station (Dev/Test)"
        return AQIResponse(
            location=target_location,
            latitude=28.6139,
            longitude=77.2090,
            aqi=165,
            pm25=78.4,
            pm10=142.1,
            no2=34.6,
            so2=12.1,
            co=1.8,
            o3=45.2,
            timestamp=datetime.now(timezone.utc),
        )


# Global provider instance with setter for pluggable Member 1 datasets
_current_data_provider: BaseDataProvider = DevTestDataProvider()


def get_data_provider() -> BaseDataProvider:
    """Retrieve the currently active data provider."""
    return _current_data_provider


def set_data_provider(provider: BaseDataProvider) -> None:
    """Register a custom data provider (e.g. Member 1 pipeline or test mock)."""
    global _current_data_provider
    _current_data_provider = provider
