"""Climate alerts API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from app.schemas.alerts import AlertResponse
from app.services.alert_service import alert_service

router = APIRouter()


@router.get(
    "/alerts",
    response_model=List[AlertResponse],
    summary="Get Active Climate Alerts",
    description="Retrieve all active early-warning climate and hazard alerts.",
)
async def get_alerts(
    location: Optional[str] = Query(
        default=None,
        description="Optional location filter for alerts",
    ),
) -> List[AlertResponse]:
    """Return list of active alerts."""
    return alert_service.get_active_alerts(location=location)
