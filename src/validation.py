from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["date", "latitude", "longitude", "location"]
NUMERIC_CLIMATE_COLUMNS = [
    "rainfall_mm",
    "temperature_c",
    "relative_humidity_pct",
    "wind_speed_m_s",
    "surface_pressure_kpa",
]


def validate_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Validate input climate data before further processing."""
    if df is None or df.empty:
        raise ValueError("Dataset is empty or missing.")

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Dataset missing required columns: {missing_columns}")

    if df["date"].isna().any():
        raise ValueError("Dataset contains null date values.")

    parsed_dates = pd.to_datetime(df["date"], errors="coerce")
    if parsed_dates.isna().any():
        raise ValueError("Dataset contains malformed dates.")

    if df["latitude"].isna().any() or df["longitude"].isna().any():
        raise ValueError("Dataset contains missing latitude or longitude values.")

    if ((df["latitude"] < -90) | (df["latitude"] > 90)).any():
        raise ValueError("Latitude values are outside the valid range [-90, 90].")
    if ((df["longitude"] < -180) | (df["longitude"] > 180)).any():
        raise ValueError("Longitude values are outside the valid range [-180, 180].")

    for column in NUMERIC_CLIMATE_COLUMNS:
        if column in df.columns:
            numeric_values = pd.to_numeric(df[column], errors="coerce")
            if numeric_values.isna().any():
                raise ValueError(f"Column '{column}' contains missing numeric values.")
            if column == "rainfall_mm" and (numeric_values < 0).any():
                raise ValueError("Rainfall values cannot be negative.")
            if column == "temperature_c" and ((numeric_values < -80) | (numeric_values > 60)).any():
                raise ValueError("Temperature values are outside realistic bounds for daily climate records.")
            if column == "relative_humidity_pct" and ((numeric_values < 0) | (numeric_values > 100)).any():
                raise ValueError("Relative humidity values must be within 0 and 100 percent.")
            if column == "wind_speed_m_s" and (numeric_values < 0).any():
                raise ValueError("Wind speed values cannot be negative.")
            if column == "surface_pressure_kpa" and ((numeric_values < 70) | (numeric_values > 110)).any():
                raise ValueError("Surface pressure values are outside valid atmospheric bounds.")

    return df.copy()
