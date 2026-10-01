"""Build the labeled Maharashtra IFI-Impacts / ERA5 district-day table."""

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

from src.fetch_features import (  # noqa: E402
	DEFAULT_END_DATE,
	DEFAULT_START_DATE,
	DISTRICT_NAMES,
	DEFAULT_BOUNDARY_PATH,
	ERA5_CACHE_DIR,
	build_rainfall_features,
	fetch_era5_district,
	load_selected_boundaries,
)

IFI_PATH = ROOT / "data/real/ifi/India_Flood_Inventory_v3.csv"
OUTPUT_PATH = ROOT / "data/processed/real_flood_dataset.csv"
TRAIN_END_YEAR = 2018
TEST_START_YEAR = 2019
STUDY_START_YEAR = 2000
STUDY_END_YEAR = 2023
MONSOON_MONTHS = (6, 7, 8, 9)
NEGATIVE_SEED = 42


def _split_field(value: Any) -> list[str]:
	if pd.isna(value):
		return []
	return [part.strip() for part in str(value).split(",")]


def _prepare_event_labels(
	events: pd.DataFrame,
	district_names: dict[int, str] = DISTRICT_NAMES,
) -> tuple[dict[tuple[int, date], set[str]], dict[int, set[date]], dict[str, int]]:
	"""Return positive start dates, padded event windows, and explicit drop counts."""
	starts = pd.to_datetime(events["Start Date"], format="%d-%m-%Y %H:%M", errors="coerce")
	ends = pd.to_datetime(events["End Date"], format="%d-%m-%Y %H:%M", errors="coerce")
	positive_ids: dict[tuple[int, date], set[str]] = defaultdict(set)
	blocked_days: dict[int, set[date]] = {code: set() for code in district_names}
	drops: Counter[str] = Counter()
	selected_codes = {str(code) for code in district_names}
	district_event_associations = 0

	for row_index, row in events.iterrows():
		districts = _split_field(row.get("Districts"))
		lgd_codes = _split_field(row.get("District_LGD_Codes"))
		if not selected_codes.intersection(lgd_codes):
			drops["event_rows_without_selected_lgd_code"] += 1
			continue
		if len(districts) != len(lgd_codes):
			drops["selected_event_rows_with_misaligned_name_code_lists"] += 1
			continue
		for district, code_text in zip(districts, lgd_codes):
			if code_text not in selected_codes:
				continue
			code = int(code_text)
			district_event_associations += 1
			if district.casefold() != district_names[code].casefold():
				drops["selected_name_lgd_code_mismatches"] += 1
				continue
			start = starts.iloc[row_index]
			if pd.isna(start):
				drops["selected_events_missing_start_date"] += 1
				continue
			start_day = start.date()
			end = ends.iloc[row_index]
			if pd.isna(end):
				end_day = start_day
				drops["selected_events_missing_end_used_start_only_for_exclusion"] += 1
			else:
				end_day = end.date()
			if end_day < start_day:
				drops["selected_events_with_end_before_start"] += 1
				continue

			block_start = max(start_day - timedelta(days=3), date(STUDY_START_YEAR, 1, 1))
			block_end = min(end_day + timedelta(days=3), date(STUDY_END_YEAR, 12, 31))
			if block_start <= block_end:
				blocked_days[code].update(
					day.date() for day in pd.date_range(block_start, block_end, freq="D")
				)

			if not (
				STUDY_START_YEAR <= start_day.year <= STUDY_END_YEAR
				and start_day.month in MONSOON_MONTHS
			):
				drops["selected_events_outside_study_years_or_monsoon_start"] += 1
				continue
			key = (code, start_day)
			if positive_ids[key]:
				drops["duplicate_district_start_date_event_associations"] += 1
			positive_ids[key].add(str(row["UEI"]))

	drops["ifi_event_rows_total"] = int(len(events))
	drops["selected_district_event_associations_seen"] = district_event_associations
	drops["unique_positive_district_start_dates"] = len(positive_ids)
	return positive_ids, blocked_days, dict(drops)


def _sample_negative_dates(
	positive_ids: dict[tuple[int, date], set[str]],
	blocked_days: dict[int, set[date]],
	seed: int = NEGATIVE_SEED,
) -> tuple[list[tuple[int, date]], dict[str, int]]:
	"""Sample one negative per positive within the same district/year/month."""
	positive_counts = Counter((code, day.year, day.month) for code, day in positive_ids)
	candidate_days: dict[tuple[int, int, int], list[date]] = defaultdict(list)
	for code in DISTRICT_NAMES:
		for timestamp in pd.date_range(
			date(STUDY_START_YEAR, 6, 1), date(STUDY_END_YEAR, 9, 30), freq="D"
		):
			day = timestamp.date()
			if day.month in MONSOON_MONTHS and day not in blocked_days[code]:
				candidate_days[(code, day.year, day.month)].append(day)

	rng = np.random.default_rng(seed)
	selected: list[tuple[int, date]] = []
	shortage_groups = 0
	shortage_rows = 0
	for key, positives_in_group in sorted(positive_counts.items()):
		candidates = candidate_days.get(key, [])
		count = min(positives_in_group, len(candidates))
		if count < positives_in_group:
			shortage_groups += 1
			shortage_rows += positives_in_group - count
		if count:
			indices = rng.choice(len(candidates), size=count, replace=False)
			selected.extend((key[0], candidates[int(index)]) for index in sorted(indices))
	return selected, {
		"negative_sampling_ratio_target": 1.0,
		"negative_sampling_strata": "LGD district x calendar year x monsoon month",
		"negative_shortage_strata": shortage_groups,
		"unmatched_negative_rows_due_to_stratum_shortage": shortage_rows,
		"negative_sampled": len(selected),
	}


def build_real_dataset(
	ifi_path: str | Path = IFI_PATH,
	boundary_path: str | Path = DEFAULT_BOUNDARY_PATH,
	cache_dir: str | Path = ERA5_CACHE_DIR / "archive",
	output_path: str | Path = OUTPUT_PATH,
	force: bool = False,
) -> dict[str, Any]:
	"""Build a strict IFI/ERA5 dataset; never substitute or interpolate missing data."""
	if not Path(ifi_path).is_file():
		raise FileNotFoundError(f"IFI-Impacts inventory not found: {ifi_path}")
	output = Path(output_path)
	if output.exists() and not force:
		raise FileExistsError(f"Refusing to overwrite existing real dataset: {output}; pass --force to replace it.")
	boundaries = load_selected_boundaries(boundary_path)
	district_names = {code: name for code, (name, _) in boundaries.items()}
	events = pd.read_csv(ifi_path, dtype={"District_LGD_Codes": "string", "State_Codes": "string"})
	positive_ids, blocked_days, dropped_events = _prepare_event_labels(events, district_names)
	negative_dates, negative_metadata = _sample_negative_dates(positive_ids, blocked_days)
	if not positive_ids:
		raise ValueError("No valid positive IFI district-start dates remain after filtering.")
	if not negative_dates:
		raise ValueError("No valid negative district-days remain after exclusion and matching.")

	rainfall: dict[int, pd.Series] = {}
	boundary_names = {code: (name, geometry) for code, (name, geometry) in boundaries.items()}
	for code, (district, geometry) in boundary_names.items():
		series, _ = fetch_era5_district(
			code,
			geometry,
			DEFAULT_START_DATE,
			DEFAULT_END_DATE,
			cache_dir=cache_dir,
		)
		if district != district_names[code]:
			raise ValueError(f"Boundary name mismatch for LGD {code}.")
		rainfall[code] = series

	observations: list[dict[str, Any]] = []
	for (code, event_date), ueis in sorted(positive_ids.items()):
		observations.append(
			{
				"date": event_date,
				"district": f"{district_names[code]} (LGD {code})",
				"lgd_code": code,
				"flood_risk": 1,
				"event_ueis": "|".join(sorted(ueis)),
			}
		)
	for code, day in negative_dates:
		observations.append(
			{
				"date": day,
				"district": f"{district_names[code]} (LGD {code})",
				"lgd_code": code,
				"flood_risk": 0,
				"event_ueis": "",
			}
		)
	frame = pd.DataFrame(observations).sort_values(["date", "lgd_code", "flood_risk"]).reset_index(drop=True)
	frame["date"] = pd.to_datetime(frame["date"])
	frame["year"] = frame["date"].dt.year.astype("int16")
	frame["month"] = frame["date"].dt.month.astype("int8")
	if frame.duplicated(["lgd_code", "date"]).any():
		raise ValueError("Dataset contains duplicate district-days after label generation.")

	feature_rows: list[pd.DataFrame] = []
	training_monthly_means: dict[int, dict[int, float]] = {}
	for code, district in district_names.items():
		series = rainfall[code]
		training_series = series.loc[
			(series.index.year >= STUDY_START_YEAR) & (series.index.year <= TRAIN_END_YEAR)
		]
		means = training_series.groupby(training_series.index.month).mean()
		training_monthly_means[code] = {int(month): float(value) for month, value in means.items()}
		mask = frame["lgd_code"] == code
		district_dates = frame.loc[mask, "date"]
		features = build_rainfall_features(series, district_dates)
		features["lgd_code"] = code
		features["rainfall_anomaly_vs_training_monthly_mean_mm"] = [
			float(row["rainfall_1d_total_mm"] - means[(pd.Timestamp(row["date"]) - pd.Timedelta(days=1)).month])
			if pd.notna(row["rainfall_1d_total_mm"])
			else np.nan
			for _, row in features.iterrows()
		]
		feature_rows.append(features)
	all_features = pd.concat(feature_rows, ignore_index=True)
	frame = frame.merge(all_features, on=["date", "lgd_code", "month"], how="left", validate="one_to_one")
	frame["district"] = frame["district"].astype("string")
	frame["event_ueis"] = frame["event_ueis"].astype("string")
	frame = frame.sort_values(["date", "lgd_code"]).reset_index(drop=True)
	if frame.filter(regex=r"^rainfall_|^days_since_rain|^rainfall_anomaly").isna().all(axis=None):
		raise ValueError("All rainfall features are missing; refusing to save an unlabeled-feature dataset.")

	class_counts = frame["flood_risk"].value_counts().sort_index().to_dict()
	majority_label = int(max(class_counts, key=class_counts.get))
	majority_accuracy = float(class_counts[majority_label] / len(frame))
	negative_metadata.update(
		{
			"negative_sampled": int(class_counts.get(0, 0)),
			"positive_count": int(class_counts.get(1, 0)),
			"class_balance": {
				str(label): {"count": int(count), "fraction": float(count / len(frame))}
				for label, count in class_counts.items()
			},
			"majority_class": majority_label,
			"majority_class_baseline_accuracy": majority_accuracy,
			"test_year_class_counts": {
				str(label): int(count)
				for label, count in frame.loc[frame["year"] >= TEST_START_YEAR, "flood_risk"].value_counts().sort_index().items()
			},
			"training_year_class_counts": {
				str(label): int(count)
				for label, count in frame.loc[frame["year"] <= TRAIN_END_YEAR, "flood_risk"].value_counts().sort_index().items()
			},
		}
	)
	output.parent.mkdir(parents=True, exist_ok=True)
	frame.to_csv(output, index=False)
	result = {
		"dataset": str(output),
		"observations": len(frame),
		"class_counts": {str(label): int(count) for label, count in class_counts.items()},
		"class_balance": negative_metadata["class_balance"],
		"majority_class": majority_label,
		"majority_class_baseline_accuracy": majority_accuracy,
		"training_years": [STUDY_START_YEAR, TRAIN_END_YEAR],
		"test_years": [TEST_START_YEAR, STUDY_END_YEAR],
		"training_year_class_counts": negative_metadata["training_year_class_counts"],
		"test_year_class_counts": negative_metadata["test_year_class_counts"],
		"negative_sampling": negative_metadata,
		"dropped_event_counts": dropped_events,
		"rainfall_feature_columns": [
			column
			for column in frame.columns
			if column.startswith("rainfall_") or column.startswith("days_since_rain")
		],
		"anomaly_monthly_means_training_years_only": True,
		"positive_definition": "One district-day at each valid IFI-Impacts event Start Date in June-September 2000-2023; exact aligned District_LGD_Codes; binary target only.",
		"negative_definition": "Sampled non-event district-days matched within district x year x monsoon month, excluding every mapped event interval expanded by three days on both sides.",
	}
	print(json.dumps(result, indent=2))
	return result


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--ifi", default=str(IFI_PATH))
	parser.add_argument("--boundary", default=str(DEFAULT_BOUNDARY_PATH))
	parser.add_argument("--cache-dir", default=str(ERA5_CACHE_DIR / "archive"))
	parser.add_argument("--output", default=str(OUTPUT_PATH))
	parser.add_argument("--force", action="store_true")
	args = parser.parse_args()
	try:
		build_real_dataset(
			args.ifi,
			args.boundary,
			args.cache_dir,
			args.output,
			force=args.force,
		)
	except (FileNotFoundError, FileExistsError, ValueError) as exc:
		parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
	main()