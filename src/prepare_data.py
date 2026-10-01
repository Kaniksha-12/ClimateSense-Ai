from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.cleaning import clean_dataset
from src.config import DEFAULT_PROCESSED_DATASET, DEFAULT_RAW_DATASET, DEFAULT_REPORT_PATH, DEFAULT_SCHEMA_PATH
from src.data_collection import download_nasa_power_data
from src.features import generate_features
from src.reporting import generate_quality_report
from src.validation import validate_dataset


def run_pipeline(
    latitude: float = 28.6139,
    longitude: float = 77.2090,
    location: str = "Delhi",
    start_date: str = "20240101",
    end_date: str = "20241231",
    raw_path: str | Path | None = None,
    processed_path: str | Path | None = None,
    metadata_dir: str | Path | None = None,
    report_path: str | Path | None = None,
) -> pd.DataFrame:
    raw_path = Path(raw_path) if raw_path is not None else DEFAULT_RAW_DATASET
    processed_path = Path(processed_path) if processed_path is not None else DEFAULT_PROCESSED_DATASET
    metadata_dir = Path(metadata_dir) if metadata_dir is not None else Path("data/metadata")
    report_path = Path(report_path) if report_path is not None else DEFAULT_REPORT_PATH

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if not raw_path.exists():
        raw_df = download_nasa_power_data(
            latitude=latitude,
            longitude=longitude,
            location=location,
            start_date=start_date,
            end_date=end_date,
            output_path=raw_path,
        )
    else:
        raw_df = pd.read_csv(raw_path)
        if (
            ("temperature_c" in raw_df.columns and (raw_df["temperature_c"] < -80).any())
            or ("surface_pressure_kpa" in raw_df.columns and (raw_df["surface_pressure_kpa"] < 1).any())
        ):
            raw_df = download_nasa_power_data(
                latitude=latitude,
                longitude=longitude,
                location=location,
                start_date=start_date,
                end_date=end_date,
                output_path=raw_path,
            )

    raw_df = validate_dataset(raw_df)
    cleaned_df = clean_dataset(raw_df)
    processed_df = generate_features(cleaned_df)

    processed_path.parent.mkdir(parents=True, exist_ok=True)
    processed_df.to_csv(processed_path, index=False)

    schema = {
        "features": [
            "rainfall_mm",
            "temperature_c",
            "relative_humidity_pct",
            "wind_speed_m_s",
            "surface_pressure_kpa",
            "previous_day_rainfall_mm",
            "rain_3day_mm",
            "rain_7day_mm",
            "rainfall_anomaly_mm",
        ],
        "target": None,
        "identifiers": ["date", "latitude", "longitude", "location"],
        "date_range": {
            "start": str(processed_df["date"].min()),
            "end": str(processed_df["date"].max()),
        },
        "geographic_coverage": {
            "latitude_min": float(processed_df["latitude"].min()),
            "latitude_max": float(processed_df["latitude"].max()),
            "longitude_min": float(processed_df["longitude"].min()),
            "longitude_max": float(processed_df["longitude"].max()),
        },
    }

    metadata_dir.mkdir(parents=True, exist_ok=True)
    schema_path = metadata_dir / "final_schema.json"
    schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")

    duplicates_removed = int(len(raw_df) - len(cleaned_df))
    generate_quality_report(
        processed_df,
        report_path,
        duplicates_removed=duplicates_removed,
        features_created=["previous_day_rainfall_mm", "rain_3day_mm", "rain_7day_mm", "rainfall_anomaly_mm"],
    )

    return processed_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ClimateSense AI preprocessing pipeline")
    parser.add_argument("--latitude", type=float, default=28.6139)
    parser.add_argument("--longitude", type=float, default=77.2090)
    parser.add_argument("--location", type=str, default="Delhi")
    parser.add_argument("--start-date", type=str, default="20240101")
    parser.add_argument("--end-date", type=str, default="20241231")
    parser.add_argument("--raw-path", type=str, default=str(DEFAULT_RAW_DATASET))
    parser.add_argument("--processed-path", type=str, default=str(DEFAULT_PROCESSED_DATASET))
    parser.add_argument("--metadata-dir", type=str, default="data/metadata")
    parser.add_argument("--report-path", type=str, default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()
    run_pipeline(
        latitude=args.latitude,
        longitude=args.longitude,
        location=args.location,
        start_date=args.start_date,
        end_date=args.end_date,
        raw_path=args.raw_path,
        processed_path=args.processed_path,
        metadata_dir=args.metadata_dir,
        report_path=args.report_path,
    )
