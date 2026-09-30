"""Health check response schema."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Schema for health status response."""

    status: str
    service: str
    version: str
