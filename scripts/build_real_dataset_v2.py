"""Build a strict IFI-Impacts / three-point ERA5 district-day dataset."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from src.fetch_features import DISTRICT_NAMES, build_rainfall_features  # noqa: E402

IFI_PATH = ROOT / "data/real/ifi/India_Flood_Inventory_v3.csv"
RAINFALL_PATH = ROOT / "data/real/era5/three_point/district_daily_rainfall.csv"
OUTPUT_PATH = ROOT / "data/processed/real_flood_dataset_v2.csv"
TRAIN_START_YEAR = 2000
TRAIN_END_YEAR = 2018
TEST_START_YEAR = 2019
TEST_END_YEAR = 2023
MONSOON_MONTHS = (6, 7, 8, 9)
RAINFALL_START = date(2000, 5, 2)
RAINFALL_END = date(2023, 9, 29)


def _tokens(value: Any) -> list[str]:
	if pd.isna(value):
		return []
	return [token.strip() for token in str(value).split(",")]


def prepare_event_labels(
	events: pd.DataFrame,
	district_names: dict[int, str] = DISTRICT_NAMES,
) -> tuple[dict[tuple[int, date], set[str]], dict[int, set[date]], dict[str, int]]:
	"""Parse single-state, name/code-aligned events and block their full windows."""
	required = {"UEI", "Start Date", "End Date", "State", "Districts", "District_LGD_Codes"}
	missing = required - set(events.columns)
	if missing:
		raise ValueError(f"IFI inventory is missing required columns: {sorted(missing)}")
	starts = pd.to_datetime(events["Start Date"], format="%d-%m-%Y %H:%M", errors="coerce")
	ends = pd.to_datetime(events["End Date"], format="%d-%m-%Y %H:%M", errors="coerce")
	positive_ids: dict[tuple[int, date], set[str]] = defaultdict(set)
	blocked_days: dict[int, set[date]] = {code: set() for code in district_names}
	drops: Counter[str] = Counter()
	selected_codes = {str(code) for code in district_names}
	valid_associations = 0

	for position, (_, row) in enumerate(events.iterrows()):
		states = _tokens(row["State"])
		if states != ["Maharashtra"]:
			drops["not_single_state_maharashtra"] += 1
			continue
		districts = _tokens(row["Districts"])
		lgd_codes = _tokens(row["District_LGD_Codes"])
		if len(districts) != len(lgd_codes):
			drops["district_lgd_token_count_mismatch"] += 1
			continue
		start_value = starts.iloc[position]
		if pd.isna(start_value):
			drops["missing_or_invalid_start_date"] += 1
			continue
		start_day = start_value.date()
		end_value = ends.iloc[position]
		if pd.isna(end_value):
			end_day = start_day
			drops["missing_end_date_used_start_day_for_exclusion"] += 1
		else:
			end_day = end_value.date()
		if end_day < start_day:
			drops["end_before_start"] += 1
			continue

		for district, code_text in zip(districts, lgd_codes):
			if code_text not in selected_codes:
				continue
			code = int(code_text)
			if district.casefold() != district_names[code].casefold():
				drops["selected_district_lgd_name_mismatch"] += 1
				continue
			valid_associations += 1
			block_start = max(start_day - timedelta(days=3), date(TRAIN_START_YEAR, 1, 1))
			block_end = min(end_day + timedelta(days=3), date(TEST_END_YEAR, 12, 31))
			blocked_days[code].update(
				day.date() for day in pd.date_range(block_start, block_end, freq="D")
			)
			if TRAIN_START_YEAR <= start_day.year <= TEST_END_YEAR and start_day.month in MONSOON_MONTHS:
				positive_ids[(code, start_day)].add(str(row["UEI"]))

	drops["ifi_event_rows_total"] = int(len(events))
	drops["valid_selected_district_event_associations"] = valid_associations
	drops["unique_positive_district_start_dates"] = len(positive_ids)
	return dict(positive_ids), blocked_days, dict(drops)


def build_negative_dates(
	blocked_days: dict[int, set[date]],
	start_year: int = TRAIN_START_YEAR,
	end_year: int = TEST_END_YEAR,
) -> list[tuple[int, date]]:
	"""Return every monsoon district-day outside all padded event windows."""
	negative_dates: list[tuple[int, date]] = []
	for code, blocked in blocked_days.items():
		for timestamp in pd.date_range(date(start_year, 6, 1), date(end_year, 9, 30), freq="D"):
			day = timestamp.date()
			if day.month in MONSOON_MONTHS and day not in blocked:
				negative_dates.append((code, day))
	return negative_dates


def _load_rainfall(path: str | Path) -> dict[int, pd.Series]:
	frame = pd.read_csv(path, parse_dates=["date"])
	required = {"date", "lgd_code", "district", "precipitation_sum_mm"}
	if required - set(frame.columns):
		raise ValueError(f"ERA5 rainfall CSV is missing columns: {sorted(required - set(frame.columns))}")
	if frame.duplicated(["lgd_code", "date"]).any():
		raise ValueError("ERA5 rainfall CSV contains duplicate district-dates.")
	if set(frame["lgd_code"].astype(int)) != set(DISTRICT_NAMES):
		raise ValueError("ERA5 rainfall CSV does not contain exactly the five selected LGD codes.")
	frame["lgd_code"] = frame["lgd_code"].astype(int)
	frame["precipitation_sum_mm"] = pd.to_numeric(frame["precipitation_sum_mm"], errors="coerce")
	if frame["precipitation_sum_mm"].isna().any() or not np.isfinite(frame["precipitation_sum_mm"]).all():
		raise ValueError("ERA5 rainfall contains missing or non-finite values.")
	if (frame["precipitation_sum_mm"] < 0).any():
		raise ValueError("ERA5 rainfall contains negative values.")
	expected = pd.date_range(RAINFALL_START, RAINFALL_END, freq="D")
	series: dict[int, pd.Series] = {}
	for code, group in frame.groupby("lgd_code"):
		values = group.set_index("date")["precipitation_sum_mm"].sort_index()
		if not values.index.equals(expected):
			raise ValueError(f"ERA5 LGD {code} dates do not exactly cover {RAINFALL_START} through {RAINFALL_END}.")
		series[int(code)] = values.rename("district_rainfall_mm")
	return series


def _observation_features(
	rainfall: pd.Series,
	observation_dates: list[pd.Timestamp],
	training_monthly_means: pd.Series,
) -> pd.DataFrame:
	features = build_rainfall_features(rainfall, observation_dates)
	previous_dates = pd.DatetimeIndex(features["date"] - pd.Timedelta(days=1))
	daily_values = rainfall.reindex(previous_dates).to_numpy(dtype=float)
	month_means = training_monthly_means.reindex(previous_dates.month).to_numpy(dtype=float)
	features["rainfall_anomaly_vs_training_monthly_mean_mm"] = daily_values - month_means
	return features


def build_real_dataset_v2(
	ifi_path: str | Path = IFI_PATH,
	rainfall_path: str | Path = RAINFALL_PATH,
	output_path: str | Path = OUTPUT_PATH,
) -> dict[str, Any]:
	"""Build the v2 labeled table without requesting rainfall or overwriting outputs."""
	output = Path(output_path)
	if output.exists():
		raise FileExistsError(f"Refusing to overwrite existing output: {output}")
	if not Path(ifi_path).is_file():
		raise FileNotFoundError(f"IFI inventory not found: {ifi_path}")
	if not Path(rainfall_path).is_file():
		raise FileNotFoundError(f"ERA5 rainfall CSV not found: {rainfall_path}")
	events = pd.read_csv(ifi_path, dtype={"District_LGD_Codes": "string"})
	positive_ids, blocked_days, dropped_events = prepare_event_labels(events)
	negative_dates = build_negative_dates(blocked_days)
	if not positive_ids or not negative_dates:
		raise ValueError("Both valid positive events and eligible negative district-days are required.")

	observations = [
		{
			"date": event_day,
			"district": f"{DISTRICT_NAMES[code]} (LGD {code})",
			"lgd_code": code,
			"flood_risk": 1,
			"event_ueis": "|".join(sorted(ueis)),
		}
		for (code, event_day), ueis in positive_ids.items()
	]
	observations.extend(
		{
			"date": day,
			"district": f"{DISTRICT_NAMES[code]} (LGD {code})",
			"lgd_code": code,
			"flood_risk": 0,
			"event_ueis": "",
		}
		for code, day in negative_dates
	)
	frame = pd.DataFrame(observations)
	frame["date"] = pd.to_datetime(frame["date"])
	frame["year"] = frame["date"].dt.year.astype("int16")
	frame["month"] = frame["date"].dt.month.astype("int8")
	if frame.duplicated(["lgd_code", "date"]).any():
		raise ValueError("V2 data contains duplicate district-day rows.")

	rainfall = _load_rainfall(rainfall_path)
	feature_frames: list[pd.DataFrame] = []
	for code in DISTRICT_NAMES:
		series = rainfall[code]
		training_series = series.loc[
			(series.index.year >= TRAIN_START_YEAR) & (series.index.year <= TRAIN_END_YEAR)
		]
		monthly_means = training_series.groupby(training_series.index.month).mean()
		mask = frame["lgd_code"] == code
		features = _observation_features(
			series,
			frame.loc[mask, "date"].tolist(),
			monthly_means,
		)
		features["lgd_code"] = code
		feature_frames.append(features)
	all_features = pd.concat(feature_frames, ignore_index=True)
	frame = frame.merge(all_features, on=["date", "month", "lgd_code"], how="left", validate="one_to_one")
	frame = frame.sort_values(["date", "lgd_code"]).reset_index(drop=True)
	if frame.filter(regex=r"^rainfall_|^days_since_rain").isna().all(axis=None):
		raise ValueError("All rainfall features are missing.")
	if frame[[column for column in frame if column.startswith("rainfall_")]].isna().any(axis=None):
		raise ValueError("Rainfall window or anomaly features are unexpectedly missing.")

	class_counts = frame["flood_risk"].value_counts().sort_index()
	majority_label = int(class_counts.idxmax())
	train = frame[frame["year"].between(TRAIN_START_YEAR, TRAIN_END_YEAR)]
	test = frame[frame["year"].between(TEST_START_YEAR, TEST_END_YEAR)]
	result: dict[str, Any] = {
		"dataset": str(output),
		"rows": int(len(frame)),
		"class_counts": {str(label): int(count) for label, count in class_counts.items()},
		"class_balance": {str(label): float(count / len(frame)) for label, count in class_counts.items()},
		"majority_class": majority_label,
		"majority_class_baseline_accuracy": float(class_counts.max() / len(frame)),
		"training_years": [TRAIN_START_YEAR, TRAIN_END_YEAR],
		"test_years": [TEST_START_YEAR, TEST_END_YEAR],
		"training_rows": int(len(train)),
		"test_rows": int(len(test)),
		"training_class_counts": {str(label): int(count) for label, count in train["flood_risk"].value_counts().sort_index().items()},
		"test_class_counts": {str(label): int(count) for label, count in test["flood_risk"].value_counts().sort_index().items()},
		"dropped_events": dropped_events,
		"negative_count": int(class_counts.get(0, 0)),
		"negative_rule": "All June-September district-days outside each matched IFI event interval expanded by three days before/after.",
		"severity_used_for_label": False,
		"rainfall_source": "data/real/era5/three_point/district_daily_rainfall.csv",
		"rainfall_date_range": [RAINFALL_START.isoformat(), RAINFALL_END.isoformat()],
		"rainfall_feature_columns": [column for column in frame if column.startswith("rainfall_") or column.startswith("days_since_rain")],
		"anomaly_baseline": "Per-district daily monthly mean, computed from 2000-2018 rainfall only; anomaly uses the previous day's rainfall.",
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
	args = parser.parse_args()
	try:
		build_real_dataset_v2(args.ifi, args.rainfall, args.output)
	except (FileNotFoundError, FileExistsError, ValueError) as exc:
		parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
	main()