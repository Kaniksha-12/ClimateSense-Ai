"""Convert prediction tables to geospatial data and export GeoJSON."""

from pathlib import Path

import geopandas as gpd
import pandas as pd


def to_geodataframe(predictions: pd.DataFrame) -> gpd.GeoDataFrame:
    """Create WGS84 point geometries while retaining prediction attributes."""
    coordinate_fields = {"latitude", "longitude"}
    missing_fields = coordinate_fields - set(predictions.columns)
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Predictions are missing coordinate fields: {missing}.")

    return gpd.GeoDataFrame(
        predictions.copy(),
        geometry=gpd.points_from_xy(predictions["longitude"], predictions["latitude"]),
        crs="EPSG:4326",
    )


def export_geojson(geodataframe: gpd.GeoDataFrame, output_path: str | Path) -> Path:
    """Write a GeoDataFrame to a GeoJSON file and return its path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(geodataframe.to_json(), encoding="utf-8")
    return path