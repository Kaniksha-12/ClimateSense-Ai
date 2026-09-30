"""Health check endpoint unit tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_status_and_payload():
    """Verify that the /api/v1/health endpoint returns 200 OK and valid JSON."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert isinstance(data, dict)
    assert data["status"] == "ok"
    assert data["service"] == "ClimateSense AI Backend"
    assert data["version"] == "0.1.0"


def test_root_endpoint():
    """Verify that the root endpoint is accessible and returns service metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ClimateSense AI Backend"
    assert data["health_check"] == "/api/v1/health"
