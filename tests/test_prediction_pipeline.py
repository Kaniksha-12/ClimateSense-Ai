"""Focused tests using synthetic data strictly as test fixtures."""

import numpy as np
import pandas as pd
import pytest

from src.data_analyzer import analyze_dataframe, load_csv
from src.feature_engineering import ClimateFeatureEngineer
from src.predict import load_model, predict_risk, risk_category
from src.preprocessing import build_preprocessor, validate_dataset
from src.train import train_model


@pytest.fixture
def synthetic_flood_test_data() -> pd.DataFrame:
    """Small deterministic TEST DATA; it does not represent real climate behavior."""
    rainfall = np.array([10, 20, 15, 80, 90, 110, 5, 25, 100, 120] * 8, dtype=float)
    humidity = np.array([40, 55, 60, 80, 90, 95, 35, 50, 88, 92] * 8, dtype=float)
    flood = ((rainfall > 70) & (humidity > 75)).astype(int)
    return pd.DataFrame(
        {
            "rainfall_mm": rainfall,
            "humidity": humidity,
            "station_type": ["urban", "rural"] * 40,
            "flood_risk": flood,
        }
    )


def test_csv_loading_and_dataset_summary(tmp_path, synthetic_flood_test_data):
    csv_path = tmp_path / "test_data.csv"
    synthetic_flood_test_data.to_csv(csv_path, index=False)
    loaded = load_csv(csv_path)
    summary = analyze_dataframe(loaded)
    assert summary["rows"] == 80
    assert "rainfall_mm" in summary["numerical_columns"]
    assert summary["duplicate_rows"] == 70


def test_csv_missing_and_empty_errors(tmp_path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        load_csv(tmp_path / "missing.csv")
    empty_path = tmp_path / "empty.csv"
    empty_path.write_text("rainfall_mm,flood_risk\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no rows"):
        load_csv(empty_path)


def test_generated_demo_csv_is_marked_and_has_expected_schema():
    from pathlib import Path

    demo_dir = Path(__file__).resolve().parents[1] / "data" / "demo"
    training_path = demo_dir / "synthetic_flood_demo.csv"
    final_test_path = demo_dir / "synthetic_flood_final_test.csv"
    unseen_path = demo_dir / "unseen_observations.csv"
    data_notice = "DEMO ONLY — NOT REAL CLIMATE PERFORMANCE"
    assert training_path.read_text(encoding="utf-8").splitlines()[0] == f"# {data_notice}"
    assert unseen_path.read_text(encoding="utf-8").splitlines()[0] == f"# {data_notice}"
    assert final_test_path.read_text(encoding="utf-8").splitlines()[0] == f"# {data_notice}"
    training_data = load_csv(training_path)
    final_test_data = load_csv(final_test_path)
    unseen_data = load_csv(unseen_path)
    assert training_data.shape == (240, 6)
    assert final_test_data.shape == (120, 6)
    assert unseen_data.shape == (12, 5)
    assert list(training_data.columns[:-1]) == [
        "rainfall", "temperature", "humidity", "pressure", "wind_speed"
    ]
    assert training_data["flood_risk"].nunique() == 2


def test_target_validation_and_duplicate_handling():
    frame = pd.DataFrame({"rainfall": [1, 1, 2, 3], "flood_risk": [0, 0, 1, 1]})
    clean = validate_dataset(frame, "flood_risk")
    assert len(clean) == 3
    with pytest.raises(ValueError, match="valid labeled target is required"):
        validate_dataset(frame, "not_a_label")
    with pytest.raises(ValueError, match="at least two labeled classes"):
        validate_dataset(pd.DataFrame({"rain": [1, 2], "flood_risk": [1, 1]}), "flood_risk")


def test_missing_and_invalid_numeric_values_are_preprocessed():
    features = pd.DataFrame(
        {"rainfall": [10.0, np.nan, np.inf, 40.0], "station": ["a", None, "b", "a"]}
    )
    clean = validate_dataset(features)
    engineered = ClimateFeatureEngineer().fit_transform(clean)
    processed = build_preprocessor(engineered).fit_transform(engineered)
    values = processed.toarray() if hasattr(processed, "toarray") else processed
    assert np.isfinite(values).all()


def test_climate_features_only_use_available_columns():
    source = pd.DataFrame({"rainfall_mm": [10.0, 20.0], "date": ["2024-01-01", "2024-02-01"]})
    engineer = ClimateFeatureEngineer().fit(source)
    transformed = engineer.transform(source)
    assert "precipitation_total" not in transformed
    assert "date_month" in transformed
    assert "temperature" not in transformed
    invalid_date = engineer.transform(pd.DataFrame({"rainfall_mm": [30.0], "date": [None]}))
    assert list(invalid_date.columns) == list(transformed.columns)
    assert pd.isna(invalid_date.loc[0, "date_month"])
    interval_rain = pd.DataFrame({"rainfall_hour_1": [10.0], "rainfall_hour_2": [15.0]})
    interval_features = ClimateFeatureEngineer().fit_transform(interval_rain)
    assert interval_features.loc[0, "precipitation_total"] == 25.0


def test_risk_category_thresholds():
    assert risk_category(0.2) == "LOW"
    assert risk_category(0.5) == "MEDIUM"
    assert risk_category(0.8) == "HIGH"
    with pytest.raises(ValueError, match="between 0 and 1"):
        risk_category(1.2)


def test_train_load_predict_round_trip(tmp_path, synthetic_flood_test_data):
    data_notice = "DEMO ONLY — NOT REAL CLIMATE PERFORMANCE"
    model_path = tmp_path / "models" / "test_model.joblib"
    result = train_model(
        synthetic_flood_test_data,
        "flood_risk",
        model_path=model_path,
        reports_dir=tmp_path / "reports",
        random_state=7,
        data_notice=data_notice,
    )
    assert set(result["evaluations"]) == {
        "Baseline RandomForest",
        "Baseline XGBoost",
        "Tuned RandomForest",
        "Tuned XGBoost",
        "Best Model",
    }
    assert "Tuned " in result["best_model"]
    assert "cross_validation" in result
    bundle = load_model(model_path)
    assert bundle["metadata"]["model_name"] == result["best_model"]
    assert bundle["metadata"]["data_notice"] == data_notice
    prediction = predict_risk(
        {"rainfall_mm": 110, "humidity": 95, "station_type": "urban", "location": "TEST"},
        model_path,
    )
    assert prediction["risk_type"] == "flood"
    assert prediction["risk_category"] in {"LOW", "MEDIUM", "HIGH"}
    assert 0 <= prediction["risk_score"] <= 1
    assert prediction["location"] == "TEST"
    assert prediction["model"] in {"RandomForest", "XGBoost"}
    assert prediction["data_notice"] == data_notice
    import json

    report = json.loads((tmp_path / "reports" / "evaluation.json").read_text(encoding="utf-8"))
    assert report["data_notice"] == data_notice
    assert (tmp_path / "reports" / "evaluation.json").is_file()
    assert (tmp_path / "reports" / "figures" / "class_distribution.png").is_file()
    assert (tmp_path / "reports" / "figures" / "confusion_matrix.png").is_file()
    assert (tmp_path / "reports" / "figures" / "feature_importance.png").is_file()


def test_unseen_demo_predictions_use_loaded_csv_features(tmp_path):
    from pathlib import Path

    demo_dir = Path(__file__).resolve().parents[1] / "data" / "demo"
    training_data = load_csv(demo_dir / "synthetic_flood_demo.csv")
    unseen_data = load_csv(demo_dir / "unseen_observations.csv")
    model_path = tmp_path / "demo_model.joblib"
    train_model(
        training_data,
        "flood_risk",
        model_path=model_path,
        reports_dir=tmp_path / "demo_reports",
        data_notice="DEMO ONLY — NOT REAL CLIMATE PERFORMANCE",
    )
    predictions = predict_risk(unseen_data, model_path)
    assert isinstance(predictions, list)
    assert len(predictions) == len(unseen_data) == 12
    assert predictions[0]["features"]["rainfall"] == pytest.approx(unseen_data.iloc[0]["rainfall"])
    assert all(prediction["data_notice"] == "DEMO ONLY — NOT REAL CLIMATE PERFORMANCE" for prediction in predictions)


def test_ordinal_flood_labels_score_medium_and_high_together(tmp_path):
    rainfall = np.linspace(1, 100, 90)
    data = pd.DataFrame(
        {
            "rainfall_mm": rainfall,
            "humidity": np.linspace(35, 95, len(rainfall)),
            "flood_risk": np.where(rainfall < 35, "Low", np.where(rainfall < 70, "Medium", "High")),
        }
    )
    model_path = tmp_path / "ordinal_model.joblib"
    train_model(data, "flood_risk", model_path=model_path, reports_dir=tmp_path / "ordinal_reports")
    bundle = load_model(model_path)
    row = pd.DataFrame([{"rainfall_mm": 85, "humidity": 85}])
    prediction = predict_risk(row, model_path)
    expected_score = sum(
        bundle["pipeline"].predict_proba(row)[0][index]
        for index in bundle["metadata"]["elevated_class_indices"]
    )
    assert prediction["risk_type"] == "flood"
    assert prediction["predicted_class"] in {"Low", "Medium", "High"}
    assert prediction["risk_score"] == pytest.approx(expected_score)


def test_bad_model_path_and_incompatible_bundle(tmp_path):
    import joblib

    with pytest.raises(FileNotFoundError, match="not found"):
        load_model(tmp_path / "missing.joblib")
    bad_bundle = tmp_path / "bad.joblib"
    joblib.dump({"not_a_model": True}, bad_bundle)
    with pytest.raises(ValueError, match="not a compatible"):
        load_model(bad_bundle)
