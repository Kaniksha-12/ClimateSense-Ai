from __future__ import annotations

import pandas as pd

from src.validation import NUMERIC_CLIMATE_COLUMNS, validate_dataset


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(column).strip().lower().replace(" ", "_") for column in df.columns]
    rename_map = {
        "precipitation": "rainfall_mm",
        "rainfall": "rainfall_mm",
        "temperature": "temperature_c",
        "temp": "temperature_c",
        "humidity": "relative_humidity_pct",
        "relative_humidity": "relative_humidity_pct",
        "wind": "wind_speed_m_s",
        "pressure": "surface_pressure_kpa",
        "surface_pressure": "surface_pressure_kpa",
        "lat": "latitude",
        "lon": "longitude",
    }
    df = df.rename(columns=rename_map)
    return df


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize a raw climate dataset."""
    if df is None or df.empty:
        raise ValueError("Dataset is empty or missing.")

    df = normalize_columns(df)

    if "date" not in df.columns:
        raise ValueError("A 'date' column is required for the climate dataset.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()

    if "location" not in df.columns:
        df["location"] = "unknown"
    df["location"] = df["location"].astype(str).str.strip()

    for column in ["latitude", "longitude"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.drop_duplicates(subset=["date", "latitude", "longitude", "location"], keep="first").copy()
    df = df.sort_values("date").reset_index(drop=True)

    for column in NUMERIC_CLIMATE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
            median_value = df[column].median()
            if pd.notna(median_value):
                df[column] = df[column].fillna(median_value)
            else:
                df[column] = df[column].fillna(0)

    df["latitude"] = df["latitude"].fillna(df["latitude"].median())
    df["longitude"] = df["longitude"].fillna(df["longitude"].median())

    validate_dataset(df)
    return df
