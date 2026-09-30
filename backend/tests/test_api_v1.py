"""Comprehensive unit tests for all ClimateSense AI v1 API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify GET /api/v1/health status and payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


def test_weather_endpoint():
    """Verify GET /api/v1/weather default and custom location responses."""
    response = client.get("/api/v1/weather")
    assert response.status_code == 200
    data = response.json()

    # Check all required fields from architecture specification
    required_fields = [
        "location",
        "latitude",
        "longitude",
        "temperature",
        "humidity",
        "rainfall",
        "wind_speed",
        "pressure",
        "timestamp",
    ]
    for field in required_fields:
        assert field in data, f"Missing field '{field}' in weather response"

    assert isinstance(data["temperature"], (int, float))
    assert isinstance(data["humidity"], (int, float))
    assert isinstance(data["rainfall"], (int, float))
    assert isinstance(data["wind_speed"], (int, float))
    assert isinstance(data["pressure"], (int, float))

    # Test query param
    loc_response = client.get("/api/v1/weather?location=Mumbai")
    assert loc_response.status_code == 200
    assert loc_response.json()["location"] == "Mumbai"


def test_aqi_endpoint():
    """Verify GET /api/v1/aqi default and custom location responses."""
    response = client.get("/api/v1/aqi")
    assert response.status_code == 200
    data = response.json()

    # Check all required fields from architecture specification
    required_fields = [
        "location",
        "latitude",
        "longitude",
        "aqi",
        "pm25",
        "pm10",
        "no2",
        "so2",
        "co",
        "o3",
        "timestamp",
    ]
    for field in required_fields:
        assert field in data, f"Missing field '{field}' in AQI response"

    assert isinstance(data["aqi"], int)
    assert isinstance(data["pm25"], (int, float))
    assert isinstance(data["pm10"], (int, float))

    # Test query param
    loc_response = client.get("/api/v1/aqi?location=Delhi")
    assert loc_response.status_code == 200
    assert loc_response.json()["location"] == "Delhi"


def test_predictions_endpoint():
    """Verify GET /api/v1/predictions returns a list of hazard predictions."""
    response = client.get("/api/v1/predictions")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) > 0

    required_fields = [
        "hazard",
        "location",
        "latitude",
        "longitude",
        "risk_level",
        "risk_score",
        "prediction",
        "model",
        "timestamp",
    ]
    for item in data:
        for field in required_fields:
            assert field in item, f"Missing field '{field}' in prediction item"


def test_prediction_by_hazard_valid():
    """Verify GET /api/v1/predictions/{hazard} for valid hazard keys."""
    for hazard in ["flood", "drought", "heatwave", "air_quality"]:
        response = client.get(f"/api/v1/predictions/{hazard}")
        assert response.status_code == 200
        data = response.json()
        assert data["hazard"] == hazard
        assert "risk_level" in data
        assert "risk_score" in data
        assert "prediction" in data
        assert "model" in data
        assert "timestamp" in data


def test_prediction_by_hazard_invalid():
    """Verify GET /api/v1/predictions/{hazard} handles invalid hazard with 404."""
    response = client.get("/api/v1/predictions/invalid_hazard_type")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "invalid_hazard_type" in data["detail"]


def test_risk_endpoint():
    """Verify GET /api/v1/risk returns composite risk assessment."""
    response = client.get("/api/v1/risk")
    assert response.status_code == 200
    data = response.json()

    required_fields = [
        "location",
        "overall_risk_level",
        "overall_risk_score",
        "flood_risk",
        "drought_risk",
        "heatwave_risk",
        "air_quality_risk",
        "timestamp",
    ]
    for field in required_fields:
        assert field in data, f"Missing field '{field}' in risk response"

    assert isinstance(data["overall_risk_score"], (int, float))
    assert isinstance(data["flood_risk"], (int, float))
    assert isinstance(data["drought_risk"], (int, float))
    assert isinstance(data["heatwave_risk"], (int, float))
    assert isinstance(data["air_quality_risk"], (int, float))


def test_map_risk_endpoint():
    """Verify GET /api/v1/map/risk returns GeoJSON-compatible FeatureCollection."""
    response = client.get("/api/v1/map/risk")
    assert response.status_code == 200
    data = response.json()

    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert isinstance(data["features"], list)
    assert len(data["features"]) > 0

    first_feature = data["features"][0]
    assert first_feature["type"] == "Feature"
    assert "geometry" in first_feature
    assert "properties" in first_feature
    assert "type" in first_feature["geometry"]
    assert "coordinates" in first_feature["geometry"]


def test_alerts_endpoint():
    """Verify GET /api/v1/alerts returns active climate alerts."""
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) > 0

    required_fields = [
        "id",
        "hazard",
        "severity",
        "title",
        "message",
        "location",
        "timestamp",
        "active",
    ]
    for alert in data:
        for field in required_fields:
            assert field in alert, f"Missing field '{field}' in alert item"
        assert isinstance(alert["active"], bool)


def test_openapi_tags():
    """Verify OpenAPI schema includes all required tags and documentation."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    expected_tags = {
        "Health",
        "Weather",
        "Air Quality",
        "Predictions",
        "Risk Assessment",
        "GIS / Map",
        "Alerts",
    }

    schema_tags = set()
    for path, methods in schema.get("paths", {}).items():
        for method, spec in methods.items():
            for tag in spec.get("tags", []):
                schema_tags.add(tag)

    for tag in expected_tags:
        assert tag in schema_tags, f"Expected tag '{tag}' not found in OpenAPI schema"
