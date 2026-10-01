from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.models import PredictionAccepted, PredictionCollection, PredictionSubmission
from app.db.database import get_db
from app.services.prediction_service import get_predictions, submit_predictions

router = APIRouter(tags=["predictions"])


@router.get("/predictions", response_model=PredictionCollection)
def predictions(session: Session = Depends(get_db)) -> dict:
    return get_predictions(session)


@router.post(
    "/predictions",
    response_model=PredictionAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_prediction_records(
    payload: PredictionSubmission,
    session: Session = Depends(get_db),
) -> dict:
    return submit_predictions(session, payload)
