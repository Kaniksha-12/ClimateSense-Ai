"""GIS risk-map service module.

Delegates GeoJSON spatial risk-map retrieval to the pluggable GIS Provider interface,
allowing Member 3 (GIS & Risk Visualization) to connect shapefiles, QGIS exports,
or geo-raster layers seamlessly.
"""

from app.gis.gis_provider import get_gis_provider
from app.schemas.map import RiskMapResponse


class MapService:
    """Service handling GeoJSON spatial risk-map datasets."""

    @staticmethod
    def get_risk_map() -> RiskMapResponse:
        """Fetch spatial risk map as a GeoJSON FeatureCollection."""
        return get_gis_provider().get_risk_map()


map_service = MapService()
