"""GeoJSON-compatible risk map schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GeoJSONGeometry(BaseModel):
    """GeoJSON geometry object conforming to RFC 7946."""

    type: str = Field(..., description="Geometry type: Point, Polygon, MultiPolygon, etc.", examples=["Point"])
    coordinates: List[Any] = Field(..., description="Coordinates array [longitude, latitude] or nested arrays")


class GeoJSONFeature(BaseModel):
    """GeoJSON feature object with environmental risk properties."""

    type: str = Field(default="Feature", description="GeoJSON Feature identifier")
    id: Optional[str] = Field(default=None, description="Optional feature identifier")
    geometry: GeoJSONGeometry = Field(..., description="Feature geometry definition")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Feature properties including risk indicators, scores, and station data",
    )


class RiskMapResponse(BaseModel):
    """GeoJSON FeatureCollection representing spatial environmental risk map data."""

    type: str = Field(default="FeatureCollection", description="GeoJSON FeatureCollection type")
    features: List[GeoJSONFeature] = Field(..., description="List of spatial risk features")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional GIS layer metadata, coordinate reference system info, or attribution",
    )
