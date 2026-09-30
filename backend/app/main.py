"""ClimateSense AI Backend Application Entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ClimateSense AI Backend provides climate intelligence, environmental risk analysis, and early-warning prediction services.",
    debug=settings.DEBUG,
)

# Configure CORS for local development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint providing basic service metadata and links."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Climate intelligence and environmental risk prediction API.",
        "docs_url": "/docs",
        "health_check": f"{settings.API_V1_STR}/health",
    }
