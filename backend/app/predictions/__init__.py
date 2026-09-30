"""ML inference and prediction pipelines package.

Member 2 Integration Anchor:
Connect trained Random Forest, XGBoost, or LSTM models using BaseClimateModel and model_registry.
"""

from app.predictions.model_interface import (
    BaseClimateModel,
    EnsembleAQIModel,
    LSTMTempHeatwaveModel,
    ModelPredictionResult,
    ModelRegistry,
    RandomForestDroughtModel,
    XGBoostFloodModel,
    model_registry,
)

__all__ = [
    "BaseClimateModel",
    "EnsembleAQIModel",
    "LSTMTempHeatwaveModel",
    "ModelPredictionResult",
    "ModelRegistry",
    "RandomForestDroughtModel",
    "XGBoostFloodModel",
    "model_registry",
]
