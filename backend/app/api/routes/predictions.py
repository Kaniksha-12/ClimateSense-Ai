"""Climate hazard prediction API routes."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Path, Query, status
from app.schemas.predictions import PredictionResponse
from app.services.prediction_service import prediction_service

router = APIRouter()


@router.get(
    "/predictions",
    response_model=List[PredictionResponse],
    summary="Get All Hazard Predictions",
    description="Retrieve all climate hazard predictions across monitored categories (flood, drought, heatwave, air_quality).",
)
async def get_all_predictions(
    location: Optional[str] = Query(
        default=None,
        description="Optional location filter for prediction results",
    ),
) -> List[PredictionResponse]:
    """Return all baseline hazard predictions."""
    return prediction_service.get_all_predictions(location=location)


@router.get(
    "/predictions/{hazard}",
    response_model=PredictionResponse,
    summary="Get Prediction by Hazard",
    description="Retrieve specific climate hazard prediction by name (e.g. flood, drought, heatwave, air_quality).",
)
async def get_prediction_by_hazard(
    hazard: str = Path(
        ...,
        description="Target hazard identifier (e.g. flood, drought, heatwave, air_quality)",
    ),
    location: Optional[str] = Query(
        default=None,
        description="Optional location filter for prediction results",
    ),
) -> PredictionResponse:
    """Return prediction for a designated hazard type."""
    prediction = prediction_service.get_prediction_by_hazard(hazard=hazard, location=location)
    if not prediction:
        supported = prediction_service.get_supported_hazards()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hazard '{hazard}' not found. Supported hazards: {', '.join(supported)}.",
        )
    return prediction
