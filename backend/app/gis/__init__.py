"""Geographic Information System (GIS) and spatial processing package.

Member 3 Integration Anchor:
Connect spatial shapefiles, QGIS layers, or raster matrices using BaseGISProvider.
"""

from app.gis.gis_provider import (
    BaseGISProvider,
    DevTestGISProvider,
    SpatialRiskRecord,
    get_gis_provider,
    set_gis_provider,
)

__all__ = [
    "BaseGISProvider",
    "DevTestGISProvider",
    "SpatialRiskRecord",
    "get_gis_provider",
    "set_gis_provider",
]
