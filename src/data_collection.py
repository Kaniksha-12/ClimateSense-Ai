from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests


PARAMETER_MAP = {
    "PRECTOTCORR": "rainfall_mm",
    "T2M": "temperature_c",
    "RH2M": "relative_humidity_pct",
    "WS2M": "wind_speed_m_s",
    "PS": "surface_pressure_kpa",
}


def download_nasa_power_data(
    latitude: float,
    longitude: float,
    location: str,
    start_date: str,
    end_date: str,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Download daily NASA POWER climate data for a point location in India."""
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point?"
        f"latitude={latitude}&longitude={longitude}&"
        f"community=RE&parameters=PRECTOTCORR,T2M,RH2M,WS2M,PS&"
        f"start={start_date}&end={end_date}&format=JSON"
    )
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    payload = response.json()

    parameter_block = payload["properties"]["parameter"]
    dates = sorted(next(iter(parameter_block.values())).keys())
    rows = []
    for date_key in dates:
        row = {"date": date_key}
        for parameter_name, transformed_name in PARAMETER_MAP.items():
            value = parameter_block.get(parameter_name, {}).get(date_key)
            row[transformed_name] = value
        rows.append(row)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df["latitude"] = latitude
    df["longitude"] = longitude
    df["location"] = location

    if "temperature_c" in df.columns:
        df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce")
    if "surface_pressure_kpa" in df.columns:
        df["surface_pressure_kpa"] = pd.to_numeric(df["surface_pressure_kpa"], errors="coerce")

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

    return df
