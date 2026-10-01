"""Prediction persistence adapter used by the stable prediction API contract."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PredictionRecord
from app.models import PredictionSubmission
from app.services.alert_service import create_alert_for_prediction
from app.services.demo_data import get_predictions as get_demo_predictions


def _prediction_item(record: PredictionRecord) -> dict:
    return {
        "location": record.location,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "risk_type": record.risk_type,
        "risk_score": record.risk_score,
        "risk_level": record.risk_level,
    }


def get_predictions(session: Session) -> dict:
    records = session.scalars(
        select(PredictionRecord).order_by(PredictionRecord.created_at.desc(), PredictionRecord.id.desc())
    ).all()
    if not records:
        return {"demo": False, "source": "No predictions available.", "items": []}

    is_demo = any(record.is_demo for record in records)
    source = (
        "Includes the seeded demo prediction; no ML model is connected."
        if is_demo
        else "Persisted prediction records supplied to the API; model provenance is not verified."
    )
    return {
        "demo": is_demo,
        "source": source,
        "items": [_prediction_item(record) for record in records],
    }


def submit_predictions(session: Session, payload: PredictionSubmission) -> dict:
    records = [
        PredictionRecord(
            location=item.location,
            latitude=item.latitude,
            longitude=item.longitude,
            risk_type=item.risk_type.value,
            risk_score=item.risk_score,
            risk_level=item.risk_level.value,
            is_demo=False,
        )
        for item in payload.items
    ]
    session.add_all(records)
    session.flush()

    for record in records:
        create_alert_for_prediction(session, record)

    session.commit()
    return {
        "accepted": True,
        "persisted": True,
        "message": "Prediction records were persisted.",
        "items": [_prediction_item(record) for record in records],
    }


def seed_demo_prediction(session: Session) -> None:
    if session.scalar(select(PredictionRecord.id).limit(1)) is not None:
        return

    demo = get_demo_predictions()["items"][0]
    record = PredictionRecord(**demo, is_demo=True)
    session.add(record)
    session.flush()
    create_alert_for_prediction(session, record)
    session.commit()
