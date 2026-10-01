"""Backend inference for the real-data ERA5 flood model."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from scripts.build_real_dataset_v2 import _observation_features
from src.fetch_features import DISTRICT_NAMES

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REAL_MODEL_PATH = ROOT_DIR / "models/real_flood_v2.pkl"
RAINFALL_HISTORY_START = pd.Timestamp("2000-05-02")
REAL_DATA_LABEL = "REAL DATA - ERA5 reanalysis rainfall"
PROVISIONAL_BANDS = True

# District/month means calculated from ERA5 rainfall in the 2000-2018 training period.
TRAINING_MONTHLY_MEANS = {
	482: [0.004599761051, 0.045341207349, 0.042353643967, 0.018827160494, 0.760204081633, 14.868479532164, 21.394736842105, 17.073684210526, 10.416725146199, 2.291511035654, 0.451228070175, 0.063214487832],
	484: [0.412604540024, 0.296325459318, 0.534468339307, 0.369753086420, 0.344160997732, 6.618304093567, 12.655008488964, 11.198471986418, 5.843040935673, 1.375382003396, 0.344736842105, 0.071420486701],
	490: [0.030406212664, 0.071719160105, 0.174133811231, 0.162407407407, 0.443367346939, 4.543918128655, 4.398641765705, 3.801245048104, 3.811871345029, 1.783418222977, 0.661403508772, 0.081607243916],
	497: [0.002986857826, 0.038517060367, 0.042891278375, 0.050370370370, 0.668877551020, 12.578771929825, 19.539671760045, 16.403338992643, 9.748362573099, 2.322297679683, 0.543274853801, 0.063044708546],
	499: [0.183691756272, 0.224081364829, 0.502508960573, 0.324012345679, 0.300736961451, 5.665497076023, 9.426202603282, 8.143350311262, 5.835789473684, 1.623542727787, 0.377251461988, 0.069779286927],
}


def load_real_model(model_path: str | Path = DEFAULT_REAL_MODEL_PATH) -> dict[str, Any]:
	"""Load a real v2/v3 bundle without requiring the demo bundle's metrics schema."""
	path = Path(model_path)
	if not path.is_file():
		raise FileNotFoundError(f"Real flood model was not found: {path}")
	try:
		bundle = joblib.load(path)
	except (OSError, ValueError, EOFError) as exc:
		raise ValueError(f"Could not load real flood model '{path}': {exc}") from exc
	if not isinstance(bundle, dict):
		raise ValueError(f"Real flood model '{path}' is not a compatible model bundle.")
	metadata = bundle.get("metadata")
	required_metadata = {"feature_columns", "decision_threshold", "label", "selected_model"}
	if (
		"pipeline" not in bundle
		or not isinstance(metadata, dict)
		or not required_metadata.issubset(metadata)
		or not isinstance(metadata["feature_columns"], list)
	):
		raise ValueError(
			f"Real flood model '{path}' must contain pipeline and metadata fields "
			f"{sorted(required_metadata)}."
		)
	return bundle


def _rainfall_series(rainfall_history: list[dict[str, Any]] | pd.DataFrame) -> pd.Series:
	if isinstance(rainfall_history, pd.DataFrame):
		frame = rainfall_history.copy()
	else:
		try:
			frame = pd.DataFrame(rainfall_history)
		except (TypeError, ValueError) as exc:
			raise ValueError("rainfall_history must be a list of {date, mm} rows or a DataFrame.") from exc
	if not {"date", "mm"}.issubset(frame.columns):
		raise ValueError("rainfall_history must contain 'date' and 'mm' columns.")
	parsed_dates = pd.to_datetime(frame["date"], errors="coerce", utc=True)
	if parsed_dates.isna().any():
		raise ValueError("rainfall_history contains an invalid date.")
	frame["date"] = parsed_dates.dt.tz_convert(None).dt.normalize()
	if frame["date"].duplicated().any():
		raise ValueError("rainfall_history contains duplicate daily dates.")
	frame["mm"] = pd.to_numeric(frame["mm"], errors="coerce")
	if frame["mm"].isna().any() or not np.isfinite(frame["mm"].to_numpy(dtype=float)).all():
		raise ValueError("rainfall_history contains missing or non-finite rainfall values.")
	if (frame["mm"] < 0).any():
		raise ValueError("rainfall_history contains negative rainfall values.")
	return frame.set_index("date")["mm"].sort_index().rename("district_rainfall_mm")


def predict_real_risk(
	district_lgd: int,
	rainfall_history: list[dict[str, Any]] | pd.DataFrame,
	prediction_date: str | date | pd.Timestamp,
	model_path: str | Path = DEFAULT_REAL_MODEL_PATH,
) -> dict[str, Any]:
	"""Predict flood risk from complete daily district rainfall history ending before prediction."""
	try:
		code = int(district_lgd)
	except (TypeError, ValueError) as exc:
		raise ValueError(f"Unknown district LGD code: {district_lgd!r}.") from exc
	if code not in DISTRICT_NAMES:
		raise ValueError(f"Unsupported district LGD code {code}; supported codes: {sorted(DISTRICT_NAMES)}.")
	parsed_prediction_date = pd.to_datetime(prediction_date, errors="coerce", utc=True)
	if pd.isna(parsed_prediction_date):
		raise ValueError("prediction_date must be a valid date.")
	prediction_day = parsed_prediction_date.tz_convert(None).normalize()
	last_required_day = prediction_day - pd.Timedelta(days=1)
	minimum_last_day = RAINFALL_HISTORY_START + pd.Timedelta(days=29)
	if last_required_day < minimum_last_day:
		raise ValueError(
			"At least 30 complete preceding rainfall days are required; the v2 history baseline "
			f"starts on {RAINFALL_HISTORY_START.date()}."
		)

	rainfall = _rainfall_series(rainfall_history)
	rainfall = rainfall.loc[rainfall.index < prediction_day]
	expected_dates = pd.date_range(RAINFALL_HISTORY_START, last_required_day, freq="D")
	if not rainfall.index.equals(expected_dates):
		missing = expected_dates.difference(rainfall.index)
		if len(missing):
			raise ValueError(
				"Insufficient preceding rainfall history: expected every daily value from "
				f"{RAINFALL_HISTORY_START.date()} through {last_required_day.date()}; "
				f"first missing day is {missing[0].date()}."
			)
		raise ValueError(
			"rainfall_history must include exactly one value for every day from "
			f"{RAINFALL_HISTORY_START.date()} through {last_required_day.date()}."
		)

	monthly_means = pd.Series(TRAINING_MONTHLY_MEANS[code], index=range(1, 13), dtype=float)
	features = _observation_features(rainfall, [prediction_day], monthly_means)
	features["district"] = f"{DISTRICT_NAMES[code]} (LGD {code})"
	bundle = load_real_model(model_path)
	metadata = bundle["metadata"]
	feature_columns = metadata["feature_columns"]
	missing_features = [column for column in feature_columns if column not in features.columns]
	if missing_features:
		raise ValueError(f"Real model requires unsupported features: {missing_features}.")
	model_input = features.reindex(columns=feature_columns)
	probability_columns = list(bundle["pipeline"].classes_)
	if probability_columns != [0, 1]:
		raise ValueError(f"Expected a binary real flood model with classes [0, 1], found {probability_columns}.")
	probability = float(bundle["pipeline"].predict_proba(model_input)[0, 1])
	threshold = float(metadata["decision_threshold"])
	if not 0 <= threshold <= 1:
		raise ValueError(f"Model decision threshold must be between 0 and 1; found {threshold}.")
	if probability >= threshold:
		risk_band = "High"
	elif probability >= 0.5 * threshold:
		risk_band = "Medium"
	else:
		risk_band = "Low"
	return {
		"district": DISTRICT_NAMES[code],
		"district_lgd": code,
		"prediction_date": prediction_day.date().isoformat(),
		"probability": probability,
		"predicted_flag": bool(probability >= threshold),
		"risk_band": risk_band,
		"risk_band_status": "provisional" if PROVISIONAL_BANDS else "training-year-derived",
		"threshold": threshold,
		"model": str(metadata["selected_model"]),
		"model_version": Path(model_path).stem,
		"label": REAL_DATA_LABEL,
	}