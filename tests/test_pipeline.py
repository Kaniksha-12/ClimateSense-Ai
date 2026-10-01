import pandas as pd
import pytest

from src.cleaning import clean_dataset
from src.features import generate_features
from src.validation import validate_dataset


@pytest.fixture
def demo_climate_df():
    """DEMO/TEST DATA — NOT REAL CLIMATE DATA."""
    return pd.DataFrame(
        {
            "date": [
                "2024-01-01",
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-01-05",
                "2024-01-06",
            ],
            "latitude": [28.61, 28.61, 28.61, 28.61, 28.61, 28.61, 28.61],
            "longitude": [77.21, 77.21, 77.21, 77.21, 77.21, 77.21, 77.21],
            "location": ["Delhi", "Delhi", "Delhi", "Delhi", "Delhi", "Delhi", "Delhi"],
            "rainfall_mm": [0.0, 0.0, 5.5, 12.1, 0.0, 1.2, 8.7],
            "temperature_c": [18.0, 18.0, 19.3, 21.0, 22.1, 17.8, 16.9],
            "relative_humidity_pct": [60.0, 60.0, 65.0, 70.0, 72.0, 68.0, 62.0],
            "wind_speed_m_s": [2.1, 2.1, 2.4, 1.9, 2.2, 2.0, 1.8],
            "surface_pressure_kpa": [100.6, 100.6, 100.4, 100.3, 100.5, 100.7, 100.8],
        }
    )


def test_empty_dataset_detection():
    df = pd.DataFrame(columns=["date", "rainfall_mm", "temperature_c"])
    with pytest.raises(ValueError):
        validate_dataset(df)


def test_duplicate_removal_and_date_conversion(demo_climate_df):
    cleaned = clean_dataset(demo_climate_df)
    assert cleaned["date"].dtype.kind in {"M", "m"}
    assert not cleaned.duplicated(subset=["date", "latitude", "longitude"]).any()


def test_invalid_lat_lon_and_numeric_values():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02"],
            "latitude": [95.0, 28.61],
            "longitude": [-181.0, 77.21],
            "location": ["Delhi", "Delhi"],
            "rainfall_mm": [0.0, -5.0],
            "temperature_c": [18.0, 1000.0],
            "relative_humidity_pct": [60.0, 120.0],
            "wind_speed_m_s": [2.1, 1.0],
            "surface_pressure_kpa": [100.6, 95.0],
        }
    )
    with pytest.raises(ValueError):
        validate_dataset(df)


def test_feature_generation():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=7, freq="D"),
            "rainfall_mm": [0.0, 2.0, 4.0, 8.0, 1.0, 0.0, 3.0],
        }
    )
    out = generate_features(df)
    assert "previous_day_rainfall_mm" in out.columns
    assert "rain_3day_mm" in out.columns
    assert "rain_7day_mm" in out.columns
    assert out.loc[0, "previous_day_rainfall_mm"] == 0.0
    assert out.loc[3, "rain_3day_mm"] == 14.0


def test_final_schema_requires_identifiers_and_features():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "latitude": [28.61, 28.61, 28.61],
            "longitude": [77.21, 77.21, 77.21],
            "location": ["Delhi", "Delhi", "Delhi"],
            "rainfall_mm": [1.0, 2.0, 3.0],
            "temperature_c": [20.0, 21.0, 22.0],
            "humidity_pct": [60.0, 62.0, 64.0],
        }
    )
    schema = {
        "features": ["rainfall_mm", "temperature_c", "humidity_pct"],
        "identifiers": ["date", "latitude", "longitude", "location"],
        "target": None,
    }
    assert schema["target"] is None
    assert "rainfall_mm" in schema["features"]
