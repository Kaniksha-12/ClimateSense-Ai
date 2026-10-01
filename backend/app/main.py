from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routes import alerts, conditions, gis, predictions, risks
from app.config import get_cors_origins
from app.db.database import SessionLocal, initialize_database
from app.services.prediction_service import seed_demo_prediction


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    with SessionLocal() as session:
        seed_demo_prediction(session)
    yield


app = FastAPI(
    title="ClimateSense AI API",
    description="Integration-ready dashboard API with explicitly labeled demonstration data.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(conditions.router, prefix="/api")
app.include_router(gis.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(risks.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")


@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request data",
            "errors": jsonable_encoder(exc.errors()),
        },
    )
