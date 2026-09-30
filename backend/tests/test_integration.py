"""Unit tests for Backend Integration Layer interfaces (Step 2).

Tests:
- Data Provider Interface (Member 1 integration)
- ML Model Registry & BaseClimateModel Interface (Member 2 integration)
- GIS Provider Interface (Member 3 integration)
- Risk Aggregation Service
- Alert Generation Service
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest
from app.gis.gis_provider import (
    BaseGISProvider,
    DevTestGISProvider,
    SpatialRiskRecord,
    get_gis_provider,
    set_gis_provider,
)
from app.predictions.model_interface import (
    BaseClimateModel,
    ModelPredictionResult,
    model_registry,
)
from app.schemas.aqi import AQIResponse
from app.schemas.predictions import PredictionResponse
from app.schemas.weather import WeatherResponse
from app.services.alert_service import alert_service
from app.services.aqi_service import aqi_service
from app.services.data_provider import (
    BaseDataProvider,
    DevTestDataProvider,
    get_data_provider,
    set_data_provider,
)
from app.services.map_service import map_service
from app.services.prediction_service import prediction_service
from app.services.risk_service import risk_service
from app.services.weather_service import weather_service


def test_data_provider_interface_and_swapping():
    """Verify that custom BaseDataProvider can be plugged into weather & aqi services."""
    default_provider = get_data_provider()
    assert isinstance(default_provider, DevTestDataProvider)

    # Test baseline provider output
    baseline_weather = weather_service.get_current_weather()
    assert baseline_weather.temperature == 29.5
    baseline_aqi = aqi_service.get_current_aqi()
    assert baseline_aqi.aqi == 165

    # Mock custom provider representing Member 1 live/cleaned pipeline
    class Member1MockPipeline(BaseDataProvider):
        def get_weather(self, location: Optional[str] = None) -> WeatherResponse:
            return WeatherResponse(
                location=location or "Member 1 Weather Station",
                latitude=19.0760,
                longitude=72.8777,
                temperature=32.4,
                humidity=75.0,
                rainfall=50.0,
                wind_speed=25.0,
                pressure=1008.0,
                timestamp=datetime.now(timezone.utc),
            )

        def get_aqi(self, location: Optional[str] = None) -> AQIResponse:
            return AQIResponse(
                location=location or "Member 1 AQI Station",
                latitude=19.0760,
                longitude=72.8777,
                aqi=88,
                pm25=28.0,
                pm10=55.0,
                no2=18.0,
                so2=8.0,
                co=0.7,
                o3=22.0,
                timestamp=datetime.now(timezone.utc),
            )

    try:
        set_data_provider(Member1MockPipeline())
        active = get_data_provider()
        assert isinstance(active, Member1MockPipeline)

        # Weather and AQI services must now seamlessly return Member 1 data
        custom_weather = weather_service.get_current_weather()
        assert custom_weather.temperature == 32.4
        assert custom_weather.rainfall == 50.0

        custom_aqi = aqi_service.get_current_aqi()
        assert custom_aqi.aqi == 88
        assert custom_aqi.pm25 == 28.0
    finally:
        # Restore default provider
        set_data_provider(DevTestDataProvider())


def test_prediction_model_interface_and_registration():
    """Verify that custom BaseClimateModel can be plugged into ModelRegistry."""
    # Test existing registered models
    supported = prediction_service.get_supported_hazards()
    assert "flood" in supported
    assert "drought" in supported
    assert "heatwave" in supported
    assert "air_quality" in supported

    # Mock custom model representing Member 2 trained model
    class CustomCycloneModel(BaseClimateModel):
        @property
        def model_name(self) -> str:
            return "member2_random_forest_cyclone_v1"

        @property
        def supported_hazards(self) -> List[str]:
            return ["cyclone"]

        def predict(
            self,
            hazard: str,
            location: str,
            features: Optional[Dict[str, Any]] = None,
        ) -> ModelPredictionResult:
            wind = features.get("wind_speed", 45.0) if features else 45.0
            score = 0.85 if wind > 40 else 0.30
            return ModelPredictionResult(
                prediction="High storm surge risk detected by Member 2 model",
                risk_score=score,
                risk_level="Severe" if score >= 0.80 else "Low",
                model_name=self.model_name,
            )

    custom_model = CustomCycloneModel()
    model_registry.register_model(custom_model)

    # Verify model is now registered and callable via prediction service
    assert "cyclone" in prediction_service.get_supported_hazards()
    pred = prediction_service.get_prediction_by_hazard("cyclone", location="Coastal Bay")
    assert pred is not None
    assert pred.hazard == "cyclone"
    assert pred.model == "member2_random_forest_cyclone_v1"
    assert pred.risk_score == 0.85
    assert pred.risk_level == "Severe"

    # Test feature input ingestion
    pred_low_wind = prediction_service.get_prediction_by_hazard(
        "cyclone", location="Inland", features={"wind_speed": 20.0}
    )
    assert pred_low_wind.risk_score == 0.30


def test_gis_provider_interface():
    """Verify spatial risk record addition and GeoJSON generation."""
    gis_provider = get_gis_provider()
    initial_map = gis_provider.get_risk_map()
    initial_count = len(initial_map.features)
    assert initial_count > 0

    # Add new spatial record from Member 3
    new_record = SpatialRiskRecord(
        id="zone-member3-test",
        latitude=12.9716,
        longitude=77.5946,
        hazard="flood",
        risk_level="High",
        risk_score=76.5,
        properties={"zone_type": "Wetland catchment"},
    )
    gis_provider.add_spatial_feature(new_record)

    updated_map = map_service.get_risk_map()
    assert len(updated_map.features) == initial_count + 1

    added_feature = next(f for f in updated_map.features if f.id == "zone-member3-test")
    assert added_feature.properties["dominant_hazard"] == "flood"
    assert added_feature.properties["overall_risk_score"] == 76.5
    assert added_feature.geometry.coordinates == [77.5946, 12.9716]


def test_risk_aggregation_logic():
    """Verify multi-hazard risk aggregation and tier categorization."""
    # Test risk level categorization
    assert risk_service.calculate_risk_level(85.0) == "Critical"
    assert risk_service.calculate_risk_level(70.0) == "High"
    assert risk_service.calculate_risk_level(50.0) == "Moderate"
    assert risk_service.calculate_risk_level(30.0) == "Low"

    # Test score aggregation calculation
    scores = {
        "flood": 80.0,
        "drought": 20.0,
        "heatwave": 50.0,
        "air_quality": 70.0,
    }
    weights = {
        "flood": 0.35,
        "drought": 0.20,
        "heatwave": 0.20,
        "air_quality": 0.25,
    }
    # Expected: 80*0.35 + 20*0.20 + 50*0.20 + 70*0.25 = 28 + 4 + 10 + 17.5 = 59.5
    agg_score = risk_service.aggregate_hazard_scores(scores, weights=weights)
    assert agg_score == 59.5

    # Test full service synthesis
    risk_assessment = risk_service.get_risk_assessment()
    assert risk_assessment.location is not None
    assert isinstance(risk_assessment.overall_risk_score, float)
    assert risk_assessment.overall_risk_level in ["Critical", "High", "Moderate", "Low"]
    assert risk_assessment.flood_risk > 0


def test_alert_generation_from_predictions():
    """Verify that alert service generates alerts based on prediction risk score thresholds."""
    high_risk_pred = PredictionResponse(
        hazard="flood",
        location="Riverside",
        latitude=28.6,
        longitude=77.2,
        risk_level="Severe",
        risk_score=0.88,
        prediction="Rapid river swell expected",
        model="test_model",
        timestamp=datetime.now(timezone.utc),
    )
    low_risk_pred = PredictionResponse(
        hazard="drought",
        location="Farmland",
        latitude=28.6,
        longitude=77.2,
        risk_level="Low",
        risk_score=0.15,
        prediction="No drought risk",
        model="test_model",
        timestamp=datetime.now(timezone.utc),
    )

    # High risk should trigger alert
    alert = alert_service.generate_alert_from_prediction(high_risk_pred, threshold=0.50)
    assert alert is not None
    assert alert.hazard == "flood"
    assert alert.severity == "Severe"
    assert alert.active is True
    assert "Riverside" in alert.location

    # Low risk should not trigger alert
    suppressed_alert = alert_service.generate_alert_from_prediction(low_risk_pred, threshold=0.50)
    assert suppressed_alert is None

    # Test active alerts listing
    active_alerts = alert_service.get_active_alerts()
    assert len(active_alerts) > 0
    assert all(a.active is True for a in active_alerts)
