"""Load a trained artifact and return API-ready risk predictions."""

import argparse
import json
import logging
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.config import (
	DEFAULT_DEMO_DATASET,
	DEFAULT_HIGH_RISK_THRESHOLD,
	DEFAULT_LOW_RISK_THRESHOLD,
	DEFAULT_MODEL_PATH,
	DEFAULT_REPORTS_DIR,
)
from src.data_analyzer import load_csv

logger = logging.getLogger(__name__)

CANONICAL_CLIMATE_FEATURES = ["rainfall", "temperature", "humidity", "pressure", "wind_speed"]
FEATURE_ALIASES = {
	"rainfall": ["rainfall", "rainfall_mm", "precipitation", "precipitation_mm", "rain", "precip"],
	"temperature": ["temperature", "temperature_c", "temp", "air_temperature", "temperature_celsius"],
	"humidity": ["humidity", "relative_humidity", "relative_humidity_pct", "rh", "humidity_pct", "moisture"],
	"pressure": ["pressure", "surface_pressure", "surface_pressure_kpa", "air_pressure", "barometric_pressure"],
	"wind_speed": ["wind_speed", "wind_speed_m_s", "windspeed", "wind_speed_ms", "wind_velocity"],
}


def risk_category(
	probability: float,
	low_threshold: float = DEFAULT_LOW_RISK_THRESHOLD,
	high_threshold: float = DEFAULT_HIGH_RISK_THRESHOLD,
) -> str:
	"""Map prototype risk probabilities to LOW/MEDIUM/HIGH categories."""
	if not 0 <= low_threshold < high_threshold <= 1:
		raise ValueError("Risk thresholds must satisfy 0 <= low < high <= 1.")
	if not 0 <= probability <= 1:
		raise ValueError("Risk probability must be between 0 and 1.")
	if probability < low_threshold:
		return "LOW"
	if probability < high_threshold:
		return "MEDIUM"
	return "HIGH"


def _normalize_column_name(name: str) -> str:
	return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def detect_climate_columns(frame: pd.DataFrame) -> dict[str, str]:
	"""Map a CSV's climate-column variants to the canonical feature names used by the model."""
	if not isinstance(frame, pd.DataFrame):
		raise TypeError("Expected a pandas DataFrame.")
	mapping: dict[str, str] = {}
	for column in frame.columns:
		normalized = _normalize_column_name(column)
		if not normalized:
			continue
		best_canonical: str | None = None
		best_score: tuple[int, int, int] | None = None
		for canonical, aliases in FEATURE_ALIASES.items():
			for alias in aliases:
				alias_norm = _normalize_column_name(alias)
				if normalized == alias_norm:
					score = 0
				elif normalized.startswith(f"{alias_norm}_") or normalized.endswith(f"_{alias_norm}"):
					score = 1
				elif alias_norm in normalized:
					score = 2
				else:
					continue
				candidate = (score, normalized.count("_"), len(normalized))
				if best_score is None or candidate < best_score:
					best_score = candidate
					best_canonical = canonical
		if best_canonical is not None:
			mapping[str(column)] = best_canonical
	return mapping


def resolve_primary_climate_columns(frame: pd.DataFrame) -> dict[str, str]:
	"""Choose the most direct source column for each canonical climate feature."""
	resolved: dict[str, str] = {}
	for original_name, canonical in detect_climate_columns(frame).items():
		current = resolved.get(canonical)
		candidate_score = (
			len(_normalize_column_name(original_name)),
			_normalize_column_name(original_name).count("_"),
		)
		if current is None:
			resolved[canonical] = original_name
		else:
			current_score = (
				len(_normalize_column_name(current)),
				_normalize_column_name(current).count("_"),
			)
			if candidate_score < current_score:
				resolved[canonical] = original_name
	return resolved


def prepare_uploaded_climate_frame(frame: pd.DataFrame) -> pd.DataFrame:
	"""Rename recognized climate equivalents to canonical feature names and validate them."""
	mapped = frame.copy()
	for canonical, original_name in resolve_primary_climate_columns(mapped).items():
		if original_name != canonical and canonical not in mapped.columns:
			mapped = mapped.rename(columns={original_name: canonical})
	for feature in CANONICAL_CLIMATE_FEATURES:
		if feature in mapped.columns:
			mapped[feature] = pd.to_numeric(mapped[feature], errors="coerce")
			mapped[feature] = mapped[feature].replace([np.inf, -np.inf], np.nan)
	missing = [feature for feature in CANONICAL_CLIMATE_FEATURES if feature not in mapped.columns]
	if missing:
		raise ValueError(
			"Missing required climate features: "
			+ ", ".join(missing)
			+ ". Supported equivalents include rainfall, precipitation, temperature, humidity, pressure, and wind_speed variants."
		)
	return mapped


def load_model(model_path: str | Path = DEFAULT_MODEL_PATH) -> dict[str, Any]:
	"""Load and validate a ClimateSense model bundle."""
	path = Path(model_path)
	if not path.is_file():
		if path == Path(DEFAULT_MODEL_PATH):
			from src.train import train_model

			train_model(
				load_csv(DEFAULT_DEMO_DATASET),
				"flood_risk",
				model_path=path,
				reports_dir=DEFAULT_REPORTS_DIR,
				data_notice="DEMO ONLY — NOT REAL CLIMATE PERFORMANCE",
			)
		if not path.is_file():
			raise FileNotFoundError(f"Saved model was not found: {path}")
	try:
		bundle = joblib.load(path)
	except (OSError, ValueError, EOFError) as exc:
		raise ValueError(f"Could not load saved model '{path}': {exc}") from exc
	if not isinstance(bundle, dict) or not {"pipeline", "metadata", "metrics"}.issubset(bundle):
		raise ValueError(f"Model file '{path}' is not a compatible ClimateSense model bundle.")
	return bundle


def predict_risk(
	input_data: Mapping[str, Any] | pd.DataFrame,
	model_path: str | Path = DEFAULT_MODEL_PATH,
	location: str | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
	"""Predict risk from observation(s), returning a GIS/API-ready result."""
	bundle = load_model(model_path)
	metadata = bundle["metadata"]
	is_frame = isinstance(input_data, pd.DataFrame)
	if is_frame:
		observations = input_data.copy()
	elif isinstance(input_data, Mapping):
		observations = pd.DataFrame([dict(input_data)])
	else:
		raise TypeError("input_data must be a mapping of feature values or a pandas DataFrame.")
	if observations.empty:
		raise ValueError("At least one climate observation is required.")
	row_locations: list[str | None] = []
	for _, row in observations.iterrows():
		candidate = location if location is not None else row.get("location")
		row_locations.append(None if pd.isna(candidate) else str(candidate))
	expected = metadata["feature_columns"]
	missing_features = [column for column in expected if column not in observations.columns]
	if missing_features:
		raise ValueError(
			"The uploaded dataset is missing required model features: "
			+ ", ".join(missing_features)
			+ ". Use climate-compatible columns or map them to the expected feature names."
		)
	features = observations.reindex(columns=expected)
	probabilities = bundle["pipeline"].predict_proba(features)
	predictions = bundle["pipeline"].predict(features)
	class_names = metadata["classes"]
	positive_index = int(metadata["positive_class_index"])
	elevated_indices = [int(index) for index in metadata["elevated_class_indices"]]
	results: list[dict[str, Any]] = []
	for row_index, predicted in enumerate(predictions):
		row_probabilities = probabilities[row_index]
		score = min(1.0, max(0.0, float(sum(row_probabilities[index] for index in elevated_indices))))
		predicted_index = int(predicted)
		feature_values = {
			str(column): None if pd.isna(value) else (value.item() if hasattr(value, "item") else value)
			for column, value in features.iloc[row_index].items()
		}
		result = {
			"location": row_locations[row_index],
			"risk_type": metadata["risk_type"],
			"risk_category": risk_category(
				score,
				float(metadata["low_risk_threshold"]),
				float(metadata["high_risk_threshold"]),
			),
			"risk_score": score,
			"probability": score,
			"model": metadata["model_name"].removeprefix("Tuned "),
			"data_notice": metadata.get("data_notice"),
			"predicted_class": class_names[predicted_index],
			"features": feature_values,
		}
		if len(class_names) == 2:
			result["positive_class_probability"] = float(row_probabilities[positive_index])
		results.append(result)
	return results if is_frame and len(results) != 1 else results[0]


def analyze_uploaded_dataset(file_path: str | Path, model_path: str | Path = DEFAULT_MODEL_PATH) -> dict[str, Any]:
	"""Validate, map, and score a climate CSV uploaded by the user."""
	path = Path(file_path)
	frame = load_csv(path)
	canonical = prepare_uploaded_climate_frame(frame)
	model_bundle = load_model(model_path)
	feature_columns = [str(column) for column in model_bundle["metadata"]["feature_columns"]]
	prediction_input = canonical[feature_columns].copy() if all(column in canonical.columns for column in feature_columns) else canonical
	prediction_input = prediction_input.reindex(columns=feature_columns)
	predictions = predict_risk(prediction_input, model_path)
	rows = predictions if isinstance(predictions, list) else [predictions]
	result_frame = frame.copy()
	for index, row_prediction in enumerate(rows):
		result_frame.loc[index, "predicted_class"] = row_prediction["predicted_class"]
		result_frame.loc[index, "prediction_probability"] = row_prediction.get("positive_class_probability", row_prediction.get("probability", 0.0))
		result_frame.loc[index, "risk_level"] = row_prediction["risk_category"]
	output_dir = Path(DEFAULT_REPORTS_DIR)
	output_dir.mkdir(parents=True, exist_ok=True)
	output_path = output_dir / "uploaded_dataset_analysis.csv"
	result_frame.to_csv(output_path, index=False)
	class_counts: dict[str, int] = {}
	for entry in rows:
		label = str(entry["predicted_class"])
		class_counts[label] = class_counts.get(label, 0) + 1
	probability_values = [float(entry.get("positive_class_probability", entry.get("probability", 0.0))) for entry in rows]
	low_count = sum(1 for entry in rows if entry["risk_category"] == "LOW")
	medium_count = sum(1 for entry in rows if entry["risk_category"] == "MEDIUM")
	high_count = sum(1 for entry in rows if entry["risk_category"] == "HIGH")
	stats: dict[str, dict[str, float]] = {}
	for feature in CANONICAL_CLIMATE_FEATURES:
		series = pd.to_numeric(canonical[feature], errors="coerce")
		stats[feature] = {
			"min": float(series.min()) if series.notna().any() else float("nan"),
			"max": float(series.max()) if series.notna().any() else float("nan"),
			"average": float(series.mean()) if series.notna().any() else float("nan"),
		}
	analysis = {
		"filename": path.name,
		"rows": int(len(frame)),
		"columns_count": int(frame.shape[1]),
		"rows_successfully_analyzed": int((canonical[CANONICAL_CLIMATE_FEATURES].notna().all(axis=1)).sum()),
		"invalid_rows": int((canonical[CANONICAL_CLIMATE_FEATURES].isna().any(axis=1)).sum()),
		"detected_climate_features": resolve_primary_climate_columns(frame),
		"missing_required_features": [],
		"climate_statistics": stats,
		"prediction_summary": {
			"total_predictions": int(len(rows)),
			"predicted_class_distribution": class_counts,
			"prediction_probabilities": probability_values,
			"low_risk_count": low_count,
			"medium_risk_count": medium_count,
			"high_risk_count": high_count,
		},
		"output_csv": str(output_path),
		"model": str(model_path),
		"data_notice": model_bundle["metadata"].get("data_notice"),
	}
	return analysis


def predict_from_csv(file_path: str | Path, model_path: str | Path = DEFAULT_MODEL_PATH) -> list[dict[str, Any]]:
	"""Convenience wrapper for uploaded climate CSV inference."""
	path = Path(file_path)
	frame = load_csv(path)
	prepared = prepare_uploaded_climate_frame(frame)
	required_columns = [str(column) for column in load_model(model_path)["metadata"]["feature_columns"]]
	prediction_input = prepared.reindex(columns=required_columns)
	predictions = predict_risk(prediction_input, model_path)
	return predictions if isinstance(predictions, list) else [predictions]


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--model", default=str(DEFAULT_MODEL_PATH), help="Saved model joblib path")
	parser.add_argument("--input", required=True, help="CSV with one or more climate observations")
	parser.add_argument("--location", help="Optional location applied to all input rows")
	args = parser.parse_args()
	logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
	try:
		predictions = predict_risk(load_csv(args.input), args.model, args.location)
		print(json.dumps(predictions, indent=2, default=str))
	except (FileNotFoundError, ValueError, TypeError) as exc:
		logger.error("Prediction failed: %s", exc)
		raise SystemExit(2) from exc


if __name__ == "__main__":
	main()
