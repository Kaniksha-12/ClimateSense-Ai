from fastapi import APIRouter

from app.models import GISResponse
from app.services.gis_service import get_gis_output

router = APIRouter(tags=["gis"])


@router.get("/gis", response_model=GISResponse)
def gis_output() -> GISResponse:
    return get_gis_output()
