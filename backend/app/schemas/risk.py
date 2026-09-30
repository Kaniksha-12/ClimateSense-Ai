"""Multi-hazard environmental risk assessment response schema."""

from datetime import datetime
from pydantic import BaseModel, Field


class RiskResponse(BaseModel):
    """Schema for aggregated multi-hazard risk assessment (Development / Test Baseline)."""

    location: str = Field(..., description="Target location name")
    overall_risk_level: str = Field(..., description="Categorical risk level (e.g. Low, Moderate, High, Critical)")
    overall_risk_score: float = Field(..., description="Aggregated risk score on a scale of 0.0 to 100.0")
    flood_risk: float = Field(..., description="Flood risk index score (0.0 - 100.0)")
    drought_risk: float = Field(..., description="Drought risk index score (0.0 - 100.0)")
    heatwave_risk: float = Field(..., description="Heatwave risk index score (0.0 - 100.0)")
    air_quality_risk: float = Field(..., description="Air quality risk index score (0.0 - 100.0)")
    timestamp: datetime = Field(..., description="Assessment calculation timestamp")
