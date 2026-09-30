"""Machine learning model integration interface.

Defines the abstract interface and model registry for AI/ML hazard predictions.
Member 2 (AI/ML Prediction) can plug in trained models (Random Forest, XGBoost, LSTM)
without altering API controllers or response schemas.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.schemas.predictions import PredictionResponse


class ModelPredictionResult:
    """Standardized output container for model predictions."""

    def __init__(
        self,
        prediction: str,
        risk_score: float,
        risk_level: str,
        model_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.prediction = prediction
        self.risk_score = risk_score
        self.risk_level = risk_level
        self.model_name = model_name
        self.metadata = metadata or {}


class BaseClimateModel(ABC):
    """Abstract base class for all climate hazard prediction models."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name or identifier of the ML model."""
        pass

    @property
    @abstractmethod
    def supported_hazards(self) -> List[str]:
        """List of hazard identifiers supported by this model."""
        pass

    @abstractmethod
    def predict(
        self,
        hazard: str,
        location: str,
        features: Optional[Dict[str, Any]] = None,
    ) -> ModelPredictionResult:
        """Execute inference on environmental/climate features.

        Args:
            hazard: Target hazard identifier (e.g. flood, drought, heatwave, air_quality).
            location: Geographical location name or coordinates.
            features: Dictionary of environmental features (temperature, rainfall, humidity, etc.).

        Returns:
            ModelPredictionResult with prediction statement, risk score, risk level, and model name.
        """
        pass


class XGBoostFloodModel(BaseClimateModel):
    """XGBoost integration wrapper for flood hazard prediction (Member 2 placeholder)."""

    @property
    def model_name(self) -> str:
        return "xgboost_flood_baseline (dev/test)"

    @property
    def supported_hazards(self) -> List[str]:
        return ["flood"]

    def predict(
        self,
        hazard: str,
        location: str,
        features: Optional[Dict[str, Any]] = None,
    ) -> ModelPredictionResult:
        rainfall = features.get("rainfall", 14.2) if features else 14.2
        risk_score = 0.78 if rainfall > 10 else 0.40
        return ModelPredictionResult(
            prediction="Elevated flood risk due to forecasted antecedent precipitation (Dev/Test Baseline)",
            risk_score=risk_score,
            risk_level="High" if risk_score >= 0.70 else "Moderate",
            model_name=self.model_name,
        )


class RandomForestDroughtModel(BaseClimateModel):
    """Random Forest integration wrapper for drought prediction (Member 2 placeholder)."""

    @property
    def model_name(self) -> str:
        return "random_forest_drought_baseline (dev/test)"

    @property
    def supported_hazards(self) -> List[str]:
        return ["drought"]

    def predict(
        self,
        hazard: str,
        location: str,
        features: Optional[Dict[str, Any]] = None,
    ) -> ModelPredictionResult:
        return ModelPredictionResult(
            prediction="Normal soil moisture levels indicate minimal drought risk (Dev/Test Baseline)",
            risk_score=0.22,
            risk_level="Low",
            model_name=self.model_name,
        )


class LSTMTempHeatwaveModel(BaseClimateModel):
    """LSTM sequence model integration wrapper for heatwave prediction (Member 2 placeholder)."""

    @property
    def model_name(self) -> str:
        return "lstm_temperature_baseline (dev/test)"

    @property
    def supported_hazards(self) -> List[str]:
        return ["heatwave"]

    def predict(
        self,
        hazard: str,
        location: str,
        features: Optional[Dict[str, Any]] = None,
    ) -> ModelPredictionResult:
        return ModelPredictionResult(
            prediction="Moderate thermal anomaly detected in weekly trend (Dev/Test Baseline)",
            risk_score=0.54,
            risk_level="Moderate",
            model_name=self.model_name,
        )


class EnsembleAQIModel(BaseClimateModel):
    """Ensemble model integration wrapper for air quality prediction (Member 2 placeholder)."""

    @property
    def model_name(self) -> str:
        return "ensemble_aqi_baseline (dev/test)"

    @property
    def supported_hazards(self) -> List[str]:
        return ["air_quality"]

    def predict(
        self,
        hazard: str,
        location: str,
        features: Optional[Dict[str, Any]] = None,
    ) -> ModelPredictionResult:
        return ModelPredictionResult(
            prediction="Particulate accumulation expected under low boundary layer conditions (Dev/Test Baseline)",
            risk_score=0.72,
            risk_level="High",
            model_name=self.model_name,
        )


class ModelRegistry:
    """Registry coordinating hazard prediction models."""

    def __init__(self):
        self._models: Dict[str, BaseClimateModel] = {}
        # Register default baseline model wrappers
        self.register_model(XGBoostFloodModel())
        self.register_model(RandomForestDroughtModel())
        self.register_model(LSTMTempHeatwaveModel())
        self.register_model(EnsembleAQIModel())

    def register_model(self, model: BaseClimateModel) -> None:
        """Register or replace an ML model for its supported hazards."""
        for hazard in model.supported_hazards:
            self._models[hazard.strip().lower()] = model

    def get_supported_hazards(self) -> List[str]:
        """Return list of all registered hazard types."""
        return sorted(list(self._models.keys()))

    def predict_hazard(
        self,
        hazard: str,
        location: Optional[str] = None,
        features: Optional[Dict[str, Any]] = None,
    ) -> Optional[PredictionResponse]:
        """Run prediction for a specific hazard."""
        hazard_key = hazard.strip().lower()
        model = self._models.get(hazard_key)
        if not model:
            return None

        loc = location or "Default Region (Dev/Test)"
        result = model.predict(hazard=hazard_key, location=loc, features=features)

        return PredictionResponse(
            hazard=hazard_key,
            location=loc,
            latitude=28.6139,
            longitude=77.2090,
            risk_level=result.risk_level,
            risk_score=result.risk_score,
            prediction=result.prediction,
            model=result.model_name,
            timestamp=datetime.now(timezone.utc),
        )

    def predict_all(
        self,
        location: Optional[str] = None,
        features: Optional[Dict[str, Any]] = None,
    ) -> List[PredictionResponse]:
        """Run predictions across all registered hazards."""
        predictions: List[PredictionResponse] = []
        for hazard in self.get_supported_hazards():
            pred = self.predict_hazard(hazard=hazard, location=location, features=features)
            if pred:
                predictions.append(pred)
        return predictions


# Global default model registry instance
model_registry = ModelRegistry()
