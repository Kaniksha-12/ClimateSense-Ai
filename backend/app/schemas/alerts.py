"""Early-warning environmental hazard alert response schema."""

from datetime import datetime
from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    """Schema for individual climate/hazard alert notification (Development / Test Baseline)."""

    id: str = Field(..., description="Unique alert identifier")
    hazard: str = Field(..., description="Target hazard type (e.g. flood, heatwave, storm, aqi)")
    severity: str = Field(..., description="Severity category (e.g. Low, Moderate, High, Severe)")
    title: str = Field(..., description="Short advisory title or headline")
    message: str = Field(..., description="Full descriptive warning message and instructions")
    location: str = Field(..., description="Impacted geographic region or city")
    timestamp: datetime = Field(..., description="Timestamp when alert was issued")
    active: bool = Field(..., description="Flag indicating if alert is currently active")
