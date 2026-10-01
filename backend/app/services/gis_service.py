"""GIS output adapter; no GeoJSON artifact is present on this branch."""

from app.models import GISUnavailable


def get_gis_output() -> GISUnavailable:
    """Report that the Member 3 GIS output is not yet available to serve."""
    return GISUnavailable(
        status="unavailable",
        source="gis",
        message="GIS output is not available yet.",
    )
