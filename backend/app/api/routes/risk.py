"""Risk assessment API routes."""

from typing import Optional
from fastapi import APIRouter, Query
from app.schemas.risk import RiskResponse
from app.services.risk_service import risk_service

router = APIRouter()


@router.get(
    "/risk",
    response_model=RiskResponse,
    summary="Get Multi-Hazard Risk Assessment",
    description="Retrieve aggregated multi-hazard environmental risk score and breakdown across flood, drought, heatwave, and air quality.",
)
async def get_risk(
    location: Optional[str] = Query(
        default=None,
        description="Optional location name for risk evaluation",
    ),
) -> RiskResponse:
    """Return composite risk assessment."""
    return risk_service.get_risk_assessment(location=location)
