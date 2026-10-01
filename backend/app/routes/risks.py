from fastapi import APIRouter

from app.models import RiskCollection
from app.services.demo_data import get_risks

router = APIRouter(tags=["risks"])


@router.get("/risks", response_model=RiskCollection)
def risks() -> dict:
    return get_risks()
