"""GIS and risk-map API routes."""

from fastapi import APIRouter
from app.schemas.map import RiskMapResponse
from app.services.map_service import map_service

router = APIRouter()


@router.get(
    "/map/risk",
    response_model=RiskMapResponse,
    summary="Get GIS Risk Map Layer",
    description="Retrieve GeoJSON-compatible FeatureCollection of geographical risk monitoring zones.",
)
async def get_map_risk() -> RiskMapResponse:
    """Return GeoJSON spatial risk-map data."""
    return map_service.get_risk_map()
