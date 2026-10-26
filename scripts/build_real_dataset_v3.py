"""Build v3 real flood-risk rows with a two-day warning label."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.build_real_dataset_v2 import (
	IFI_PATH,
	RAINFALL_PATH,
	TRAIN_END_YEAR,
	TRAIN_START_YEAR,
	TEST_END_YEAR,
	TEST_START_YEAR,
	MONSOON_MONTHS,
	_load_rainfall,
	prepare_event_labels,
)
from src.fetch_features import DISTRICT_NAMES, build_rainfall_features

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data/processed/real_flood_dataset_v3.csv"
SOIL_MOISTURE_COVERAGE = {
	"source": "Open-Meteo Historical Weather API, model=era5_land",
	"variables": ["soil_moisture_0_to_7cm_mean", "soil_moisture_7_to_28cm_mean"],
	"verified": {
		"Nagpur": "Exact date axis and finite values were confirmed for the 0-7 cm variable; the 7-28 cm series was not independently audited.",
		"Pune": "Exact date axis and finite values were confirmed for the 0-7 cm variable; the 7-28 cm series was not independently audited.",
		"Mumbai": "Full-period request timed out; completeness not verified.",
		"Thane": "Full-period request returned HTTP 429; completeness not verified.",
		"Washim": "Full-period request returned HTTP 429; completeness not verified.",
	},
	"decision": "Excluded because exact complete coverage was not verified for all five districts.",
}
RIVER_DISCHARGE_COVERAGE = {
	"source": "Open-Meteo Flood API, daily river_discharge",
	"verified": {
		"Mumbai": "A requested point returned null discharge values; a full-period request also timed out.",
		"Nagpur": "All 8,551 dates were finite at all three requested points.",
		"Pune": "All 8,551 dates were finite at all three requested points.",
		"Thane": "All 8,551 dates were finite at all three requested points.",
		"Washim": "All 8,551 dates were finite at all three requested points.",
	},
	"decision": "Excluded because Mumbai coverage contains nulls and is not complete.",
}


def _add_lead_labels(
	positive_ids: dict[tuple[int, date], set[str]],
) -> tuple[dict[tuple[int, date], set[str]], dict[tuple[int, date], set[str]]]:
	"""Return same-day and t-to-t+2 positive event associations."""
	same_day = {key: set(ueis) for key, ueis in positive_ids.items()}
	next_two_days: dict[tuple[int, date], set[str]] = defaultdict(set)
	for (code, event_day), ueis in positive_ids.items():
		for lead_days in range(3):
			prediction_day = event_day - timedelta(days=lead_days)
			if TRAIN_START_YEAR <= prediction_day.year <= TEST_END_YEAR and prediction_day.month in MONSOON_MONTHS:
				next_two_days[(code, prediction_day)].update(ueis)
	return same_day, dict(next_two_days)


def _rainfall_features(
	rainfall: pd.Series,
	observation_dates: list[pd.Timestamp],
	training_monthly_means: pd.Series,
) -> pd.DataFrame:
	"""Build rainfall features ending strictly on the day before prediction."""
	features = build_rainfall_features(rainfall, observation_dates)
	previous_dates = pd.DatetimeIndex(features["date"] - pd.Timedelta(days=1))
	for days in (60, 90):
		totals: list[float] = []
		for previous_day in previous_dates:
			window = rainfall.loc[previous_day - pd.Timedelta(days=days - 1):previous_day]
			totals.append(float(window.sum()) if len(window) == days else np.nan)
		features[f"rainfall_{days}d_total_mm"] = totals
	features["rainfall_3d_to_30d_intensity_ratio"] = np.divide(
		10.0 * features["rainfall_3d_total_mm"].to_numpy(dtype=float),
		features["rainfall_30d_total_mm"].to_numpy(dtype=float),
		out=np.zeros(len(features), dtype=float),
		where=features["rainfall_30d_total_mm"].to_numpy(dtype=float) > 0,
	)
	daily_values = rainfall.reindex(previous_dates).to_numpy(dtype=float)
	monthly_means = training_monthly_means.reindex(previous_dates.month).to_numpy(dtype=float)
	features["rainfall_anomaly_vs_training_monthly_mean_mm"] = daily_values - monthly_means
	return features


def build_real_dataset_v3(
	ifi_path: str | Path = IFI_PATH,
	rainfall_path: str | Path = RAINFALL_PATH,
	output_path: str | Path = OUTPUT_PATH,
	overwrite: bool = False,
) -> dict[str, Any]:
	"""Build v3 rows without network access; preserve all prior-version files."""
	output = Path(output_path)
	if overwrite and output.resolve() != OUTPUT_PATH.resolve():
		raise ValueError("--force is only allowed for the designated v3 dataset output.")
	if output.exists() and not overwrite:
		raise FileExistsError(f"Refusing to overwrite existing output: {output}")
	events = pd.read_csv(ifi_path, dtype={"District_LGD_Codes": "string"})
	positive_ids, blocked_days, dropped_events = prepare_event_labels(events)
	same_day_ids, next_two_ids = _add_lead_labels(positive_ids)
	negative_dates: list[tuple[int, date]] = []
	for code, blocked in blocked_days.items():
		for timestamp in pd.date_range(date(TRAIN_START_YEAR, 6, 1), date(TEST_END_YEAR, 9, 30), freq="D"):
			day = timestamp.date()
			if day.month in MONSOON_MONTHS and day not in blocked:
				negative_dates.append((code, day))

	observations: dict[tuple[int, date], dict[str, Any]] = {}
	for key, ueis in next_two_ids.items():
		code, day = key
		observations[key] = {
			"date": day,
			"district": f"{DISTRICT_NAMES[code]} (LGD {code})",
			"lgd_code": code,
			"flood_risk": 1,
			"same_day_flood_risk": 1 if key in same_day_ids else np.nan,
			"event_ueis": "|".join(sorted(ueis)),
		}
	for code, day in negative_dates:
		key = (code, day)
		if key in observations:
			continue
		observations[key] = {
			"date": day,
			"district": f"{DISTRICT_NAMES[code]} (LGD {code})",
			"lgd_code": code,
			"flood_risk": 0,
			"same_day_flood_risk": 0,
			"event_ueis": "",
		}
	for key, ueis in same_day_ids.items():
		if key not in observations:
			code, day = key
			observations[key] = {
				"date": day,
				"district": f"{DISTRICT_NAMES[code]} (LGD {code})",
				"lgd_code": code,
				"flood_risk": 1,
				"same_day_flood_risk": 1,
				"event_ueis": "|".join(sorted(ueis)),
			}
	frame = pd.DataFrame(observations.values())
	frame["date"] = pd.to_datetime(frame["date"])
	frame["year"] = frame["date"].dt.year.astype("int16")
	frame["month"] = frame["date"].dt.month.astype("int8")
	if frame.duplicated(["lgd_code", "date"]).any():
		raise ValueError("V3 dataset contains duplicate district-day rows.")

	rainfall = _load_rainfall(rainfall_path)
	feature_frames = []
	for code in DISTRICT_NAMES:
		series = rainfall[code]
		training_rainfall = series.loc[
			(series.index.year >= TRAIN_START_YEAR) & (series.index.year <= TRAIN_END_YEAR)
		]
		monthly_means = training_rainfall.groupby(training_rainfall.index.month).mean()
		mask = frame["lgd_code"] == code
		features = _rainfall_features(series, frame.loc[mask, "date"].tolist(), monthly_means)
		features["lgd_code"] = code
		feature_frames.append(features)
	all_features = pd.concat(feature_frames, ignore_index=True)
	frame = frame.merge(all_features, on=["date", "month", "lgd_code"], how="left", validate="one_to_one")
	frame = frame.sort_values(["date", "lgd_code"]).reset_index(drop=True)
	if frame[[column for column in frame if column.startswith("rainfall_")]].isna().all(axis=None):
		raise ValueError("All v3 rainfall features are missing.")

	def counts(label: str, rows: pd.DataFrame) -> dict[str, int]:
		return {str(key): int(value) for key, value in rows[label].dropna().value_counts().sort_index().items()}

	legacy = frame[frame["same_day_flood_risk"].notna()]
	train = frame[frame["year"].between(TRAIN_START_YEAR, TRAIN_END_YEAR)]
	validation = frame[frame["year"].between(2015, TRAIN_END_YEAR)]
	test = frame[frame["year"].between(TEST_START_YEAR, TEST_END_YEAR)]
	result = {
		"label": "REAL DATA - ERA5 reanalysis rainfall",
		"dataset": str(output),
		"rows": int(len(frame)),
		"positive_definition": "At prediction day t, a selected-district IFI event starts on t, t+1, or t+2; inputs end at t-1.",
		"same_day_definition": "At prediction day t, a selected-district IFI event starts on t; same-day comparison excludes buffered pre-event lead days.",
		"negative_rule": "All June-September district-days outside event intervals expanded by three days before and after.",
		"severity_used_for_label": False,
		"class_balance": {
			"all_v3_next_0_to_2_days": counts("flood_risk", frame),
			"same_day_eligible_rows": counts("same_day_flood_risk", legacy),
		},
		"training_class_counts": {
			"next_0_to_2_days": counts("flood_risk", train),
			"same_day_eligible_rows": counts("same_day_flood_risk", train[train["same_day_flood_risk"].notna()]),
		},
		"validation_class_counts": {
			"next_0_to_2_days": counts("flood_risk", validation),
			"same_day_eligible_rows": counts("same_day_flood_risk", validation[validation["same_day_flood_risk"].notna()]),
		},
		"test_class_counts": {
			"next_0_to_2_days": counts("flood_risk", test),
			"same_day_eligible_rows": counts("same_day_flood_risk", test[test["same_day_flood_risk"].notna()]),
		},
		"training_rows": int(len(train)),
		"validation_rows": int(len(validation)),
		"test_rows": int(len(test)),
		"dropped_events": dropped_events,
		"feature_columns": [column for column in frame if column.startswith("rainfall_") or column.startswith("days_since_rain")],
		"optional_variable_coverage": {
			"soil_moisture": SOIL_MOISTURE_COVERAGE,
			"river_discharge": RIVER_DISCHARGE_COVERAGE,
		},
		"rainfall_source": "data/real/era5/three_point/district_daily_rainfall.csv",
		"maximum_missing_rainfall_features": {
			column: int(frame[column].isna().sum())
			for column in frame
			if column.startswith("rainfall_") or column.startswith("days_since_rain")
		},
	}
	output.parent.mkdir(parents=True, exist_ok=True)
	frame.to_csv(output, index=False)
	print(json.dumps(result, indent=2))
	return result


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--ifi", default=str(IFI_PATH))
	parser.add_argument("--rainfall", default=str(RAINFALL_PATH))
	parser.add_argument("--output", default=str(OUTPUT_PATH))
	parser.add_argument("--force", action="store_true", help="Overwrite the v3 output dataset only")
	args = parser.parse_args()
	try:
		build_real_dataset_v3(args.ifi, args.rainfall, args.output, overwrite=args.force)
	except (FileNotFoundError, FileExistsError, ValueError) as exc:
		parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
	main()