from fastapi import APIRouter

from app.models import ClimateCondition
from app.services.demo_data import get_conditions

router = APIRouter(tags=["conditions"])


@router.get("/conditions", response_model=ClimateCondition)
def conditions() -> dict:
    return get_conditions()
