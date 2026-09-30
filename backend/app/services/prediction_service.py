"""Climate hazard prediction service module.

Delegates multi-hazard prediction inference to the pluggable ML Model Registry,
allowing Member 2 (AI/ML Prediction) to connect trained Random Forest, XGBoost,
and LSTM models seamlessly without changing API routes or schemas.
"""

from typing import Any, Dict, List, Optional
from app.predictions.model_interface import model_registry
from app.schemas.predictions import PredictionResponse


class PredictionService:
    """Service orchestrating multi-hazard prediction inference."""

    @staticmethod
    def get_supported_hazards() -> List[str]:
        """Return list of all registered hazard types."""
        return model_registry.get_supported_hazards()

    @staticmethod
    def get_prediction_by_hazard(
        hazard: str,
        location: Optional[str] = None,
        features: Optional[Dict[str, Any]] = None,
    ) -> Optional[PredictionResponse]:
        """Retrieve prediction for a specific hazard from the model registry.

        Args:
            hazard: Hazard identifier (e.g. flood, drought, heatwave, air_quality).
            location: Target geographic location.
            features: Environmental / climate feature dictionary for model inputs.

        Returns:
            PredictionResponse if supported, or None if unrecognized.
        """
        return model_registry.predict_hazard(
            hazard=hazard, location=location, features=features
        )

    @staticmethod
    def get_all_predictions(
        location: Optional[str] = None,
        features: Optional[Dict[str, Any]] = None,
    ) -> List[PredictionResponse]:
        """Retrieve predictions across all registered hazard models."""
        return model_registry.predict_all(location=location, features=features)


prediction_service = PredictionService()
