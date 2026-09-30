"""Climate hazard prediction response schema."""

from datetime import datetime
from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    """Schema for individual hazard prediction response (Development / Test Baseline)."""

    hazard: str = Field(..., description="Climate hazard identifier (e.g. flood, drought, heatwave, air_quality)")
    location: str = Field(..., description="Target geographical location")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    risk_level: str = Field(..., description="Assessed risk level (e.g. Low, Moderate, High, Severe)")
    risk_score: float = Field(..., description="Calculated risk score between 0.0 and 1.0 (or 0 to 100)")
    prediction: str = Field(..., description="Prediction summary or advisory statement")
    model: str = Field(..., description="Model identifier placeholder (to be substituted by Member 2 ML model)")
    timestamp: datetime = Field(..., description="Prediction generation timestamp")
