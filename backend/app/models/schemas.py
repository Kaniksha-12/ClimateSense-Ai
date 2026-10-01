from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskType(str, Enum):
    FLOOD = "flood"
    DROUGHT = "drought"
    HEATWAVE = "heatwave"
    AIR_QUALITY = "air_quality"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClimateCondition(StrictModel):
    location: str
    temperature: float
    humidity: float
    rainfall: float
    air_quality: int
    updated_at: datetime | None = None
    demo: bool
    source: str


class Risk(StrictModel):
    location: str
    risk_type: RiskType
    risk_score: float = Field(ge=0, le=1)
    risk_level: RiskLevel


class Prediction(Risk):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Alert(StrictModel):
    id: str
    location: str
    risk_type: RiskType
    risk_level: RiskLevel
    message: str
    severity: RiskLevel


class PredictionSubmission(StrictModel):
    items: list[Prediction] = Field(min_length=1)


class PredictionAccepted(StrictModel):
    accepted: bool
    persisted: bool
    message: str
    items: list[Prediction]


class PredictionCollection(StrictModel):
    demo: bool
    source: str
    items: list[Prediction]


class RiskCollection(StrictModel):
    demo: bool
    source: str
    items: list[Risk]


class AlertCollection(StrictModel):
    demo: bool
    source: str
    items: list[Alert]


class GISAvailable(StrictModel):
    status: Literal["ok"]
    source: Literal["gis"]
    data: dict[str, Any]


class GISUnavailable(StrictModel):
    status: Literal["unavailable"]
    source: Literal["gis"]
    message: str


GISResponse = GISAvailable | GISUnavailable
