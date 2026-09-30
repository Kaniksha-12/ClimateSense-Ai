"""ClimateSense AI Core Configuration Module."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    APP_NAME: str = "ClimateSense AI Backend"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Integration Placeholders (Member 1 - Data Collection & Preprocessing)
    WEATHER_API_KEY: str = ""
    WEATHER_DATA_SOURCE: str = "development_baseline"
    AQI_API_KEY: str = ""
    AQI_DATA_SOURCE: str = "development_baseline"

    # Integration Placeholders (Member 2 - AI/ML Prediction Models)
    MODEL_DIR: str = "models"

    # Integration Placeholders (Member 3 - GIS & Risk Map Visualization)
    GIS_DATA_DIR: str = "datasets/gis"

    # Risk & Alert Thresholds
    ALERT_RISK_THRESHOLD: float = 0.50

    # CORS Allowed Development Origins
    CORS_ORIGINS: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

