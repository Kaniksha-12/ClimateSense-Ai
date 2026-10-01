from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import AlertCollection
from app.db.database import get_db
from app.services.alert_service import get_alerts

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=AlertCollection)
def alerts(session: Session = Depends(get_db)) -> dict:
    return get_alerts(session)
