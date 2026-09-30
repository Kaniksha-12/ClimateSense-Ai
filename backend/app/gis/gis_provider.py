"""GIS and spatial risk map provider interface.

Defines the spatial risk record format and GeoJSON provider interface.
Member 3 (GIS and Risk Visualization) can connect QGIS exports, shapefiles,
or GeoPandas outputs directly through this provider interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.schemas.map import GeoJSONFeature, GeoJSONGeometry, RiskMapResponse


class SpatialRiskRecord:
    """Standard spatial risk input record from GIS processing."""

    def __init__(
        self,
        id: str,
        latitude: float,
        longitude: float,
        hazard: str,
        risk_level: str,
        risk_score: float,
        geometry: Optional[Dict[str, Any]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.latitude = latitude
        self.longitude = longitude
        self.hazard = hazard
        self.risk_level = risk_level
        self.risk_score = risk_score
        self.geometry = geometry or {
            "type": "Point",
            "coordinates": [longitude, latitude],
        }
        self.properties = properties or {}


class BaseGISProvider(ABC):
    """Abstract interface defining spatial risk data delivery."""

    @abstractmethod
    def get_risk_map(self) -> RiskMapResponse:
        """Fetch spatial risk map as a GeoJSON FeatureCollection."""
        pass

    @abstractmethod
    def add_spatial_feature(self, record: SpatialRiskRecord) -> None:
        """Add or update a spatial risk record."""
        pass


class DevTestGISProvider(BaseGISProvider):
    """Development and test baseline GIS provider.

    Supplies GeoJSON FeatureCollection formatted risk zones.
    Allows Member 3 to inject spatial layers without modifying endpoints.
    """

    def __init__(self):
        self._features: List[GeoJSONFeature] = []
        self._load_baseline_zones()

    def _load_baseline_zones(self) -> None:
        """Load baseline development spatial risk zones."""
        baseline_records = [
            SpatialRiskRecord(
                id="zone-01",
                latitude=28.6139,
                longitude=77.2090,
                hazard="air_quality",
                risk_level="High",
                risk_score=74.2,
                properties={
                    "name": "Central Monitoring Zone (Dev/Test)",
                    "aqi": 165,
                    "flood_index": 0.65,
                },
            ),
            SpatialRiskRecord(
                id="zone-02",
                latitude=28.7041,
                longitude=77.1025,
                hazard="flood",
                risk_level="Severe",
                risk_score=82.5,
                properties={
                    "name": "Northern Drainage Basin (Dev/Test)",
                    "flood_index": 0.88,
                    "soil_saturation": 85.0,
                },
            ),
            SpatialRiskRecord(
                id="zone-03",
                latitude=28.4089,
                longitude=77.3178,
                hazard="heatwave",
                risk_level="Moderate",
                risk_score=58.0,
                properties={
                    "name": "Southern Industrial Belt (Dev/Test)",
                    "surface_temp": 38.4,
                },
            ),
        ]
        for record in baseline_records:
            self.add_spatial_feature(record)

    def add_spatial_feature(self, record: SpatialRiskRecord) -> None:
        """Convert a SpatialRiskRecord to GeoJSONFeature and register it."""
        props = {
            "dominant_hazard": record.hazard,
            "overall_risk_level": record.risk_level,
            "overall_risk_score": record.risk_score,
            **record.properties,
        }
        geom = GeoJSONGeometry(
            type=record.geometry.get("type", "Point"),
            coordinates=record.geometry.get("coordinates", [record.longitude, record.latitude]),
        )
        feature = GeoJSONFeature(
            id=record.id,
            geometry=geom,
            properties=props,
        )
        self._features.append(feature)

    def get_risk_map(self) -> RiskMapResponse:
        """Return the GeoJSON FeatureCollection."""
        return RiskMapResponse(
            type="FeatureCollection",
            features=list(self._features),
            metadata={
                "crs": "EPSG:4326",
                "status": "development_baseline",
                "feature_count": len(self._features),
                "description": "GeoJSON risk map interface ready for Member 3 GIS outputs",
            },
        )


# Global GIS provider instance
_current_gis_provider: BaseGISProvider = DevTestGISProvider()


def get_gis_provider() -> BaseGISProvider:
    """Retrieve the active GIS provider."""
    return _current_gis_provider


def set_gis_provider(provider: BaseGISProvider) -> None:
    """Register a custom GIS provider (e.g. Member 3 QGIS/GeoJSON export)."""
    global _current_gis_provider
    _current_gis_provider = provider
