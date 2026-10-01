import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, inspect, select

from app.db.database import SessionLocal, engine, initialize_database
from app.db.models import AlertRecord, PredictionRecord
from app.config import DEFAULT_CORS_ORIGINS, get_cors_origins
from app.main import app
from app.services.prediction_service import seed_demo_prediction

PREDICTION = {
    "location": "Pune",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "risk_type": "flood",
    "risk_score": 0.82,
    "risk_level": "HIGH",
}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_database(client: TestClient) -> None:
    with SessionLocal() as session:
        session.execute(delete(AlertRecord))
        session.execute(delete(PredictionRecord))
        session.commit()
        seed_demo_prediction(session)


def test_database_initializes_prediction_and_alert_tables() -> None:
    initialize_database()

    assert {"predictions", "alerts"} <= set(inspect(engine).get_table_names())


def test_startup_demo_seed_is_idempotent() -> None:
    with SessionLocal() as session:
        seed_demo_prediction(session)
        seed_demo_prediction(session)
        prediction_count = session.scalar(select(func.count()).select_from(PredictionRecord))
        alert_count = session.scalar(select(func.count()).select_from(AlertRecord))

    assert prediction_count == 1
    assert alert_count == 1


def test_database_initialization_preserves_existing_prediction() -> None:
    with SessionLocal() as session:
        existing = PredictionRecord(
            location="Persistence check",
            latitude=0,
            longitude=0,
            risk_type="drought",
            risk_score=0.2,
            risk_level="LOW",
        )
        session.add(existing)
        session.commit()
        record_id = existing.id

    initialize_database()

    with SessionLocal() as session:
        preserved = session.get(PredictionRecord, record_id)

    assert preserved is not None
    assert preserved.location == "Persistence check"


def test_openapi_docs_and_schema_are_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200

    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert {
        "/api/health",
        "/api/conditions",
        "/api/predictions",
        "/api/risks",
        "/api/alerts",
        "/api/gis",
    } <= response.json()["paths"].keys()


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_gis_endpoint_remains_unavailable_without_geojson(client: TestClient) -> None:
    response = client.get("/api/gis")

    assert response.status_code == 200
    assert response.json() == {
        "status": "unavailable",
        "source": "gis",
        "message": "GIS output is not available yet.",
    }


def test_frontend_cors_allows_prediction_submission(client: TestClient) -> None:
    response = client.options(
        "/api/predictions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_cors_configuration_has_local_defaults_and_explicit_override(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert get_cors_origins() == list(DEFAULT_CORS_ORIGINS)

    monkeypatch.setenv("CORS_ORIGINS", "https://dashboard.example, https://preview.example/")
    assert get_cors_origins() == ["https://dashboard.example", "https://preview.example"]


def test_cors_configuration_rejects_wildcard(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValueError, match="wildcard origins are not allowed"):
        get_cors_origins()


def test_conditions_contract_is_labeled_demo(client: TestClient) -> None:
    response = client.get("/api/conditions")
    data = response.json()

    assert response.status_code == 200
    assert {
        "location",
        "temperature",
        "humidity",
        "rainfall",
        "air_quality",
        "updated_at",
        "demo",
    } <= data.keys()
    assert data["demo"] is True
    assert "not live" in data["source"].lower()


def test_predictions_retrieve_seeded_demo_from_database(client: TestClient) -> None:
    response = client.get("/api/predictions")
    data = response.json()

    assert response.status_code == 200
    assert data["demo"] is True
    assert data["items"] == [PREDICTION]
    assert set(data["items"][0]) == set(PREDICTION)


def test_prediction_submission_is_persisted_and_retrievable(client: TestClient) -> None:
    payload = {
        **PREDICTION,
        "location": "Nagpur",
        "risk_type": "heatwave",
        "risk_score": 0.61,
        "risk_level": "MEDIUM",
    }
    response = client.post("/api/predictions", json={"items": [payload]})

    assert response.status_code == 202
    assert response.json()["accepted"] is True
    assert response.json()["persisted"] is True
    assert response.json()["items"] == [payload]
    assert payload in client.get("/api/predictions").json()["items"]

    with SessionLocal() as session:
        record = session.scalar(select(PredictionRecord).where(PredictionRecord.location == "Nagpur"))

    assert record is not None
    assert record.created_at is not None
    assert record.is_demo is False


def test_high_prediction_creates_persisted_alert(client: TestClient) -> None:
    payload = {
        **PREDICTION,
        "location": "Delhi",
        "risk_type": "heatwave",
        "risk_level": "HIGH",
    }
    response = client.post("/api/predictions", json={"items": [payload]})
    alerts = client.get("/api/alerts").json()

    assert response.status_code == 202
    matching = [alert for alert in alerts["items"] if alert["location"] == "Delhi"]
    assert len(matching) == 1
    assert matching[0]["risk_type"] == "heatwave"
    assert matching[0]["risk_level"] == "HIGH"
    assert matching[0]["severity"] == "HIGH"
    assert matching[0]["message"] == "High heatwave risk detected in Delhi."

    with SessionLocal() as session:
        stored_alert = session.scalar(select(AlertRecord).where(AlertRecord.location == "Delhi"))

    assert stored_alert is not None
    assert stored_alert.created_at is not None
    assert stored_alert.active is True
    assert stored_alert.is_demo is False


@pytest.mark.parametrize("risk_level", ["LOW", "MEDIUM"])
def test_low_and_medium_predictions_do_not_create_alerts(
    client: TestClient,
    risk_level: str,
) -> None:
    payload = {
        **PREDICTION,
        "location": f"Test {risk_level.title()}",
        "risk_level": risk_level,
    }
    response = client.post("/api/predictions", json={"items": [payload]})
    alerts = client.get("/api/alerts").json()["items"]

    assert response.status_code == 202
    assert not any(alert["location"] == payload["location"] for alert in alerts)


def test_repeated_high_prediction_does_not_duplicate_active_alert(client: TestClient) -> None:
    response = client.post("/api/predictions", json={"items": [PREDICTION]})
    alerts = client.get("/api/alerts").json()["items"]
    matching = [
        alert for alert in alerts
        if alert["location"] == "Pune" and alert["risk_type"] == "flood" and alert["risk_level"] == "HIGH"
    ]

    assert response.status_code == 202
    assert len(matching) == 1

    with SessionLocal() as session:
        prediction_count = session.scalar(select(func.count()).select_from(PredictionRecord))
        alert_count = session.scalar(select(func.count()).select_from(AlertRecord))

    assert prediction_count == 2
    assert alert_count == 1


def test_alert_retrieval_keeps_frontend_contract(client: TestClient) -> None:
    response = client.get("/api/alerts")
    data = response.json()

    assert response.status_code == 200
    assert data["demo"] is True
    assert {"id", "location", "risk_type", "risk_level", "message", "severity"} == set(data["items"][0])
    assert "sample" in data["source"].lower()


def test_alert_api_returns_empty_state_when_no_active_alerts(client: TestClient) -> None:
    with SessionLocal() as session:
        session.execute(delete(AlertRecord))
        session.commit()

    response = client.get("/api/alerts")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["demo"] is False


def test_risks_use_supported_types_and_levels(client: TestClient) -> None:
    response = client.get("/api/risks")
    data = response.json()
    supported_types = {"flood", "drought", "heatwave", "air_quality"}
    supported_levels = {"LOW", "MEDIUM", "HIGH"}

    assert response.status_code == 200
    assert data["demo"] is True
    assert {risk["risk_type"] for risk in data["items"]} == supported_types
    assert all(risk["risk_level"] in supported_levels for risk in data["items"])
    assert all(0 <= risk["risk_score"] <= 1 for risk in data["items"])


@pytest.mark.parametrize(
    "changes",
    [
        {"risk_score": 1.01},
        {"risk_score": -0.01},
        {"risk_level": "EXTREME"},
        {"latitude": 91},
        {"longitude": -181},
        {"risk_type": "wildfire"},
        {"location": None},
    ],
)
def test_invalid_prediction_is_rejected_without_persistence(
    client: TestClient,
    changes: dict,
) -> None:
    payload = {**PREDICTION, **changes}

    response = client.post("/api/predictions", json={"items": [payload]})

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid request data"
    assert response.json()["errors"]
    assert payload not in client.get("/api/predictions").json()["items"]


def test_missing_prediction_fields_are_rejected(client: TestClient) -> None:
    response = client.post("/api/predictions", json={"items": [{"location": "Pune"}]})

    assert response.status_code == 422
    assert response.json()["errors"]
