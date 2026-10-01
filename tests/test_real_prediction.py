from datetime import date

import pandas as pd
import pytest

from src.real_predict import (
	DEFAULT_REAL_MODEL_PATH,
	load_real_model,
	predict_real_risk,
)
from src.predict import load_model, predict_risk


def _complete_history(prediction_date: str) -> pd.DataFrame:
	end_date = pd.Timestamp(prediction_date) - pd.Timedelta(days=1)
	dates = pd.date_range("2000-05-02", end_date, freq="D")
	return pd.DataFrame({"date": dates, "mm": [0.0] * len(dates)})


def test_real_adapter_loads_v2_bundle_without_demo_metrics():
	bundle = load_real_model(DEFAULT_REAL_MODEL_PATH)
	assert bundle["metadata"]["label"] == "REAL DATA - ERA5 reanalysis rainfall"
	assert "metrics" not in bundle
	assert bundle["metadata"]["decision_threshold"] > 0


@pytest.mark.parametrize(
	("code", "district"),
	[(482, "Mumbai"), (484, "Nagpur"), (490, "Pune"), (497, "Thane"), (499, "Washim")],
)
def test_real_prediction_runs_for_each_supported_district(code, district):
	result = predict_real_risk(code, _complete_history("2020-06-01"), "2020-06-01")
	assert result["district"] == district
	assert result["district_lgd"] == code
	assert result["label"] == "REAL DATA - ERA5 reanalysis rainfall"
	assert result["risk_band_status"] == "provisional"
	assert isinstance(result["predicted_flag"], bool)
	assert 0 <= result["probability"] <= 1
	assert result["predicted_flag"] == (result["probability"] >= result["threshold"])
	assert result["model_version"] == "real_flood_v2"


def test_prediction_day_rainfall_is_ignored():
	date_without_future = _complete_history("2020-06-01")
	date_with_prediction_day = pd.concat(
		[
			date_without_future,
			pd.DataFrame([{"date": "2020-06-01", "mm": 9999.0}]),
		],
		ignore_index=True,
	)
	without_future = predict_real_risk(482, date_without_future, "2020-06-01")
	with_future = predict_real_risk(482, date_with_prediction_day, "2020-06-01")
	assert with_future["probability"] == pytest.approx(without_future["probability"])


def test_insufficient_rainfall_history_has_clear_error():
	short_history = pd.DataFrame({"date": pd.date_range("2020-05-01", periods=29), "mm": [0.0] * 29})
	with pytest.raises(ValueError, match="Insufficient preceding rainfall history"):
		predict_real_risk(482, short_history, "2020-06-01")


def test_demo_prediction_contract_and_notice_are_unchanged():
	bundle = load_model()
	row = {feature: 0.0 for feature in bundle["metadata"]["feature_columns"]}
	result = predict_risk(row)
	assert result["data_notice"] == "DEMO ONLY — NOT REAL CLIMATE PERFORMANCE"
	assert result["risk_category"] in {"LOW", "MEDIUM", "HIGH"}