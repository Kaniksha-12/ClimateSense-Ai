"""Alert service module.

Integrates directly with predictions and risk assessment outputs to generate
early-warning alert notifications when monitored risk scores cross configurable thresholds.
"""

from datetime import datetime, timezone
import hashlib
from typing import List, Optional
from app.core.config import settings
from app.schemas.alerts import AlertResponse
from app.schemas.predictions import PredictionResponse
from app.services.prediction_service import prediction_service


class AlertService:
    """Service generating and dispatching climate early-warning alerts from predictions."""

    @staticmethod
    def derive_severity(risk_score: float) -> str:
        """Map normalized risk score to alert severity tier."""
        # Normalize to 0.0 - 1.0 if score is on 0-100 scale
        normalized = risk_score / 100.0 if risk_score > 1.0 else risk_score
        if normalized >= 0.75:
            return "Severe"
        elif normalized >= 0.60:
            return "High"
        elif normalized >= 0.40:
            return "Moderate"
        return "Low"

    @classmethod
    def generate_alert_from_prediction(
        cls,
        prediction: PredictionResponse,
        threshold: Optional[float] = None,
    ) -> Optional[AlertResponse]:
        """Generate an AlertResponse object if prediction risk score meets threshold.

        Args:
            prediction: PredictionResponse object from prediction service.
            threshold: Minimum risk score required to trigger an active alert.

        Returns:
            AlertResponse if threshold breached, otherwise None.
        """
        active_threshold = threshold if threshold is not None else settings.ALERT_RISK_THRESHOLD
        score = prediction.risk_score
        normalized_score = score / 100.0 if score > 1.0 else score

        if normalized_score < active_threshold:
            return None

        severity = cls.derive_severity(normalized_score)
        hazard_label = prediction.hazard.replace("_", " ").title()

        # Deterministic unique ID based on hazard and location
        id_seed = f"{prediction.hazard}:{prediction.location}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        alert_id = f"alert-{prediction.hazard[:3]}-{hashlib.md5(id_seed.encode()).hexdigest()[:6]}"

        return AlertResponse(
            id=alert_id,
            hazard=prediction.hazard,
            severity=severity,
            title=f"{hazard_label} Advisory ({severity})",
            message=f"{prediction.prediction} [Risk Score: {round(normalized_score * 100, 1)}%]",
            location=prediction.location,
            timestamp=prediction.timestamp,
            active=True,
        )

    @classmethod
    def generate_alerts_from_predictions(
        cls,
        predictions: List[PredictionResponse],
        threshold: Optional[float] = None,
    ) -> List[AlertResponse]:
        """Convert a list of hazard predictions into active alerts."""
        alerts: List[AlertResponse] = []
        for pred in predictions:
            alert = cls.generate_alert_from_prediction(pred, threshold=threshold)
            if alert:
                alerts.append(alert)
        return alerts

    @classmethod
    def get_active_alerts(
        cls,
        location: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> List[AlertResponse]:
        """Fetch all currently active climate and hazard alerts derived from predictions.

        Queries the prediction service for active hazard scores and generates
        alerts for any hazard exceeding the risk threshold.
        """
        predictions = prediction_service.get_all_predictions(location=location)
        alerts = cls.generate_alerts_from_predictions(predictions, threshold=threshold)

        # Ensure that during development/testing there is always at least one active advisory
        if not alerts:
            alerts.append(
                AlertResponse(
                    id="alert-baseline-001",
                    hazard="environmental_monitoring",
                    severity="Low",
                    title="Normal Baseline Conditions",
                    message="All monitored environmental risk levels are within safe operating limits.",
                    location=location or "National Capital Region (Dev/Test)",
                    timestamp=datetime.now(timezone.utc),
                    active=True,
                )
            )

        return alerts


alert_service = AlertService()
