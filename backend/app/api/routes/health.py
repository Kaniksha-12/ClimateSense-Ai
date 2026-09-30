"""Health check endpoint routes."""

from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check whether the ClimateSense AI backend service is running and healthy.",
)
async def get_health() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(
        status="ok",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
    )
