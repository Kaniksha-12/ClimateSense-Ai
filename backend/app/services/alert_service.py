from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AlertRecord, PredictionRecord


def create_alert_for_prediction(
    session: Session,
    prediction: PredictionRecord,
) -> AlertRecord | None:
    if prediction.risk_level != "HIGH":
        return None

    existing = session.scalar(
        select(AlertRecord).where(
            AlertRecord.location == prediction.location,
            AlertRecord.risk_type == prediction.risk_type,
            AlertRecord.risk_level == prediction.risk_level,
            AlertRecord.active.is_(True),
        )
    )
    if existing is not None:
        return existing

    risk_label = prediction.risk_type.replace("_", " ")
    alert = AlertRecord(
        location=prediction.location,
        risk_type=prediction.risk_type,
        risk_level=prediction.risk_level,
        message=f"High {risk_label} risk detected in {prediction.location}.",
        severity=prediction.risk_level,
        is_demo=prediction.is_demo,
    )
    session.add(alert)
    session.flush()
    return alert


def get_alerts(session: Session) -> dict:
    alerts = session.scalars(
        select(AlertRecord)
        .where(AlertRecord.active.is_(True))
        .order_by(AlertRecord.created_at.desc(), AlertRecord.id.desc())
    ).all()

    items = [
        {
            "id": f"alert-{alert.id:03d}",
            "location": alert.location,
            "risk_type": alert.risk_type,
            "risk_level": alert.risk_level,
            "message": alert.message,
            "severity": alert.severity,
        }
        for alert in alerts
    ]
    demo = any(alert.is_demo for alert in alerts)
    if not alerts:
        source = "No active alerts."
    elif demo:
        source = "Includes seeded sample alerts; alerts are not real-time monitoring."
    else:
        source = "Alerts from persisted prediction submissions; not live monitoring."

    return {"demo": demo, "source": source, "items": items}
