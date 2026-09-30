"""Risk assessment service module.

NOTE ON RISK MODELING:
This service provides an application-level aggregation layer designed to integrate
hazard predictions into a unified risk assessment.
This is NOT scientifically validated risk modeling. It functions as an integration
bridge that aggregates outputs from Member 2's prediction models and can later be
calibrated with Member 3's GIS vulnerability matrices.
"""

from datetime import datetime, timezone
from typing import Dict, Optional
from app.schemas.risk import RiskResponse
from app.services.prediction_service import prediction_service

# Default application-level weights for composite risk estimation (integration baseline)
DEFAULT_HAZARD_WEIGHTS: Dict[str, float] = {
    "flood": 0.35,
    "air_quality": 0.25,
    "heatwave": 0.20,
    "drought": 0.20,
}


class RiskService:
    """Service handling multi-hazard composite risk assessment."""

    @staticmethod
    def calculate_risk_level(score: float) -> str:
        """Categorize numerical risk score (0-100 scale) into risk tier."""
        if score >= 80.0:
            return "Critical"
        elif score >= 60.0:
            return "High"
        elif score >= 40.0:
            return "Moderate"
        return "Low"

    @classmethod
    def aggregate_hazard_scores(
        cls,
        hazard_scores: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Combine individual hazard risk scores (0-100) using weighted aggregation.

        Args:
            hazard_scores: Dictionary of hazard names to numerical scores (0 - 100).
            weights: Optional custom weights mapping.

        Returns:
            Weighted aggregate risk score rounded to 1 decimal place.
        """
        active_weights = weights or DEFAULT_HAZARD_WEIGHTS
        total_weight = sum(active_weights.get(h, 0.0) for h in hazard_scores)
        if total_weight <= 0:
            return 0.0

        weighted_sum = sum(
            hazard_scores[h] * active_weights.get(h, 0.0)
            for h in hazard_scores
        )
        return round(weighted_sum / total_weight, 1)

    @classmethod
    def get_risk_assessment(
        cls,
        location: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> RiskResponse:
        """Dynamically fetch hazard predictions and synthesize overall risk assessment.

        Aggregates outputs from Member 2's prediction models across monitored hazards.
        """
        target_location = location or "National Capital Region (Dev/Test)"

        # Fetch predictions for monitored hazards
        flood_pred = prediction_service.get_prediction_by_hazard("flood", location=target_location)
        drought_pred = prediction_service.get_prediction_by_hazard("drought", location=target_location)
        heatwave_pred = prediction_service.get_prediction_by_hazard("heatwave", location=target_location)
        aqi_pred = prediction_service.get_prediction_by_hazard("air_quality", location=target_location)

        # Normalize scores to 0-100 scale
        def to_100_scale(pred) -> float:
            if not pred:
                return 0.0
            score = pred.risk_score
            return round(score * 100.0 if score <= 1.0 else score, 1)

        flood_score = to_100_scale(flood_pred)
        drought_score = to_100_scale(drought_pred)
        heatwave_score = to_100_scale(heatwave_pred)
        aqi_score = to_100_scale(aqi_pred)

        hazard_scores = {
            "flood": flood_score,
            "drought": drought_score,
            "heatwave": heatwave_score,
            "air_quality": aqi_score,
        }

        overall_score = cls.aggregate_hazard_scores(hazard_scores, weights=weights)
        overall_level = cls.calculate_risk_level(overall_score)

        return RiskResponse(
            location=target_location,
            overall_risk_level=overall_level,
            overall_risk_score=overall_score,
            flood_risk=flood_score,
            drought_risk=drought_score,
            heatwave_risk=heatwave_score,
            air_quality_risk=aqi_score,
            timestamp=datetime.now(timezone.utc),
        )


risk_service = RiskService()
