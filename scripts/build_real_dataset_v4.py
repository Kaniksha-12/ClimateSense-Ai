"""Build an expanded-district IFI / ERA5 dataset with a frozen spatial holdout."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from scripts.build_real_dataset_v2 import IFI_PATH, MONSOON_MONTHS, RAINFALL_END, RAINFALL_START
from src.fetch_features import (
	DEFAULT_BOUNDARY_PATH,
	DISTRICT_NAMES,
	ERA5_CACHE_DIR,
	ERA5DailyLimitError,
	fetch_era5_district,
	load_selected_boundaries,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data/processed/real_flood_dataset_v4.csv"
THREE_POINT_CACHE_DIR = ERA5_CACHE_DIR / "three_point"
EXPANDED_RAINFALL_PATH = THREE_POINT_CACHE_DIR / "district_daily_rainfall_expanded_v4.csv"
EXPANDED_MANIFEST_PATH = THREE_POINT_CACHE_DIR / "expanded_district_manifest_v4.json"
TRAIN_START_YEAR = 2000
TRAIN_END_YEAR = 2018
TEST_START_YEAR = 2019
TEST_END_YEAR = 2023
ORIGINAL_DISTRICTS = {482, 484, 490, 497, 499}
SPATIAL_SPLIT_SEED = 42
FETCH_PROGRESS_PATH = ROOT / "data/real/era5/fetch_progress.log"
logger = logging.getLogger(__name__)

V2_FEATURE_COLUMNS = [
	"rainfall_1d_total_mm",
	"rainfall_1d_max_daily_mm",
	"rainfall_3d_total_mm",
	"rainfall_3d_max_daily_mm",
	"rainfall_7d_total_mm",
	"rainfall_7d_max_daily_mm",
	"rainfall_14d_total_mm",
	"rainfall_14d_max_daily_mm",
	"rainfall_30d_total_mm",
	"rainfall_30d_max_daily_mm",
	"days_since_rain_gt20mm",
	"rainfall_anomaly_vs_training_monthly_mean_mm",
	"month",
	"district",
]
ADDED_FEATURE_COLUMNS = [
	"rainfall_60d_total_mm",
	"rainfall_90d_total_mm",
	"rainfall_3d_to_30d_intensity_ratio",
	"rainfall_rank_within_district_month",
	"previous_day_rainfall_change_mm",
]
FEATURE_COLUMNS = V2_FEATURE_COLUMNS + ADDED_FEATURE_COLUMNS


def rank_maharashtra_districts(
	ifi_path: str | Path = IFI_PATH,
	boundary_path: str | Path = DEFAULT_BOUNDARY_PATH,
) -> list[dict[str, Any]]:
	"""Count unique, matched IFI event associations by LGD for 2000-2023 monsoons."""
	boundaries = pd.read_parquet(boundary_path, columns=["dist_lgd", "dtname", "stname"])
	maharashtra = boundaries[
		boundaries["stname"].astype(str).str.strip().str.casefold().eq("maharashtra")
	]
	name_by_code = {
		int(row.dist_lgd): str(row.dtname).strip()
		for row in maharashtra.itertuples(index=False)
	}
	events = pd.read_csv(ifi_path, dtype={"District_LGD_Codes": "string"})
	starts = pd.to_datetime(events["Start Date"], format="%d-%m-%Y %H:%M", errors="coerce")
	associations: dict[int, set[str]] = defaultdict(set)
	for position, (_, row) in enumerate(events.iterrows()):
		if str(row["State"]).strip() != "Maharashtra" or pd.isna(starts.iloc[position]):
			continue
		start = starts.iloc[position]
		if not (2000 <= start.year <= 2023 and start.month in MONSOON_MONTHS):
			continue
		districts = [] if pd.isna(row["Districts"]) else [token.strip() for token in str(row["Districts"]).split(",")]
		codes = [] if pd.isna(row["District_LGD_Codes"]) else [token.strip() for token in str(row["District_LGD_Codes"]).split(",")]
		if len(districts) != len(codes):
			continue
		for district, code_text in zip(districts, codes):
			if not code_text.isdigit():
				continue
			code = int(code_text)
			if code in name_by_code and district.casefold() == name_by_code[code].casefold():
				uei = str(row["UEI"]).strip()
				associations[code].add(uei if uei and uei.casefold() != "nan" else f"row-{position}")
	return [
		{"lgd_code": code, "district": name_by_code[code], "event_count": len(associations[code])}
		for code in sorted(name_by_code, key=lambda value: (-len(associations[value]), name_by_code[value], value))
		if len(associations[code]) >= 10
	]


def split_districts(
	ranked_districts: list[dict[str, Any]],
	seed: int = SPATIAL_SPLIT_SEED,
) -> tuple[list[int], list[int]]:
	"""Keep the original five in training and assign 60/40 of the rest by seeded draw."""
	qualifying = {int(row["lgd_code"]) for row in ranked_districts}
	missing_original = ORIGINAL_DISTRICTS - qualifying
	if missing_original:
		raise ValueError(f"Original model districts do not meet the event minimum: {sorted(missing_original)}")
	remaining = sorted(qualifying - ORIGINAL_DISTRICTS)
	if len(remaining) < 2:
		raise ValueError("At least two additional qualifying districts are required for a spatial holdout.")
	shuffled = np.random.default_rng(seed).permutation(remaining).tolist()
	training_additional_count = min(len(remaining) - 1, max(1, int(round(0.6 * len(remaining)))))
	training_codes = sorted(ORIGINAL_DISTRICTS | set(shuffled[:training_additional_count]))
	test_codes = sorted(set(shuffled[training_additional_count:]))
	return training_codes, test_codes


def split_verified_districts(
	ranked_districts: list[dict[str, Any]],
	verified_codes: set[int],
	seed: int = SPATIAL_SPLIT_SEED,
) -> tuple[list[int], list[int]]:
	"""Keep original verified districts in training and hold out ~1/3 of verified additions."""
	verified = set(map(int, verified_codes))
	if not ORIGINAL_DISTRICTS.issubset(verified):
		raise ValueError("All original five districts must remain verified training districts.")
	eligible = {int(row["lgd_code"]) for row in ranked_districts}
	if verified - eligible:
		raise ValueError(f"Verified codes are not in the eligible district ranking: {sorted(verified - eligible)}")
	additional = sorted(verified - ORIGINAL_DISTRICTS)
	if len(additional) < 2:
		return sorted(verified), []
	shuffled = np.random.default_rng(seed).permutation(additional).tolist()
	test_count = max(1, int(round(len(additional) / 3)))
	test_codes = sorted(shuffled[:test_count])
	training_codes = sorted(ORIGINAL_DISTRICTS | (set(additional) - set(test_codes)))
	return training_codes, test_codes


def _event_labels(
	ifi_path: str | Path,
	selected_codes: set[int],
	district_names: dict[int, str],
) -> tuple[dict[tuple[int, date], set[str]], dict[int, set[date]], dict[str, int]]:
	events = pd.read_csv(ifi_path, dtype={"District_LGD_Codes": "string"})
	starts = pd.to_datetime(events["Start Date"], format="%d-%m-%Y %H:%M", errors="coerce")
	ends = pd.to_datetime(events["End Date"], format="%d-%m-%Y %H:%M", errors="coerce")
	positive: dict[tuple[int, date], set[str]] = defaultdict(set)
	blocked = {code: set() for code in selected_codes}
	drops: Counter[str] = Counter()
	for position, (_, row) in enumerate(events.iterrows()):
		if str(row["State"]).strip() != "Maharashtra":
			drops["not_single_state_maharashtra"] += 1
			continue
		if pd.isna(starts.iloc[position]):
			drops["missing_or_invalid_start_date"] += 1
			continue
		districts = [] if pd.isna(row["Districts"]) else [token.strip() for token in str(row["Districts"]).split(",")]
		codes = [] if pd.isna(row["District_LGD_Codes"]) else [token.strip() for token in str(row["District_LGD_Codes"]).split(",")]
		if len(districts) != len(codes):
			drops["district_lgd_token_count_mismatch"] += 1
			continue
		start_day = starts.iloc[position].date()
		end_day = ends.iloc[position].date() if pd.notna(ends.iloc[position]) else start_day
		if end_day < start_day:
			drops["end_before_start"] += 1
			continue
		for district, code_text in zip(districts, codes):
			if not code_text.isdigit() or int(code_text) not in selected_codes:
				continue
			code = int(code_text)
			if district.casefold() != district_names[code].casefold():
				drops["selected_district_lgd_name_mismatch"] += 1
				continue
			uei = str(row["UEI"]).strip()
			if TRAIN_START_YEAR <= start_day.year <= TEST_END_YEAR and start_day.month in MONSOON_MONTHS:
				positive[(code, start_day)].add(uei)
			block_start = max(start_day - timedelta(days=3), date(TRAIN_START_YEAR, 1, 1))
			block_end = min(end_day + timedelta(days=3), date(TEST_END_YEAR, 12, 31))
			blocked[code].update(day.date() for day in pd.date_range(block_start, block_end, freq="D"))
	drops["ifi_event_rows_total"] = int(len(events))
	drops["selected_positive_district_start_dates"] = int(len(positive))
	return dict(positive), blocked, dict(drops)


def fetch_expanded_rainfall(
	ranked_districts: list[dict[str, Any]],
	boundary_path: str | Path = DEFAULT_BOUNDARY_PATH,
	cache_dir: str | Path = THREE_POINT_CACHE_DIR,
) -> Path:
	"""Fetch new district-years in event priority order and retain validated partial caches."""
	cache = Path(cache_dir)
	cache.mkdir(parents=True, exist_ok=True)
	combined_path = cache / EXPANDED_RAINFALL_PATH.name
	manifest_path = cache / EXPANDED_MANIFEST_PATH.name
	if combined_path.exists() or manifest_path.exists():
		raise FileExistsError(f"Refusing to overwrite expanded ERA5 output: {combined_path} or {manifest_path}")
	training_codes, fresh_test_codes = split_districts(ranked_districts)
	all_codes = sorted(training_codes + fresh_test_codes)
	new_codes = [int(row["lgd_code"]) for row in ranked_districts if int(row["lgd_code"]) not in ORIGINAL_DISTRICTS]
	old_path = cache / "district_daily_rainfall.csv"
	old = pd.read_csv(old_path, parse_dates=["date"])
	old_codes = set(old["lgd_code"].astype(int))
	if old_codes != ORIGINAL_DISTRICTS:
		raise ValueError(f"The original cached rainfall CSV must contain only the v2 districts; found {sorted(old_codes)}")
	boundaries = load_selected_boundaries(boundary_path, new_codes)
	name_by_code = {int(row["lgd_code"]): str(row["district"]) for row in ranked_districts}
	expected_dates = pd.date_range(RAINFALL_START, RAINFALL_END, freq="D")
	years = range(RAINFALL_START.year, RAINFALL_END.year + 1)
	verified_codes = set(ORIGINAL_DISTRICTS)
	series: dict[int, pd.Series] = {}
	metadata: dict[str, Any] = {"districts": {}, "source": "Open-Meteo Historical Weather API, models=era5"}
	FETCH_PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)

	def progress(message: str) -> None:
		line = f"{datetime.now(timezone.utc).isoformat()} {message}"
		with FETCH_PROGRESS_PATH.open("a", encoding="utf-8") as log:
			log.write(line + "\n")
		print(line, flush=True)

	def report_partial_stop(code: int, error: ERA5DailyLimitError) -> None:
		train_partial, test_partial = split_verified_districts(ranked_districts, verified_codes)
		progress(
			f"STOP daily-limit district={code} fully_verified_new={len(verified_codes - ORIGINAL_DISTRICTS)}/{len(new_codes)} "
			f"verified_codes={sorted(verified_codes)} error={error}"
		)
		progress(
			f"PARTIAL_SPLIT verified_training_codes={train_partial} verified_fresh_test_codes={test_partial}; "
			"do not train until this split is explicitly accepted"
		)

	frames = [old]
	for position, code in enumerate(new_codes, start=1):
		name, geometry = boundaries[code]
		progress(f"DISTRICT_START priority={position}/{len(new_codes)} code={code} name={name}")
		parts = []
		for year in years:
			start = max(RAINFALL_START, date(year, 1, 1))
			end = min(RAINFALL_END, date(year, 12, 31))
			cache_file = cache / f"era5_lgd_{code}_{year}.json"
			was_cached = cache_file.is_file()
			try:
				daily, year_metadata = fetch_era5_district(
					code, geometry, start, end, cache_dir=cache, force=False
				)
			except ERA5DailyLimitError as exc:
				report_partial_stop(code, exc)
				return None
			expected_year = pd.date_range(start, end, freq="D")
			if not daily.index.equals(expected_year) or daily.index.has_duplicates or not np.isfinite(daily.to_numpy()).all() or (daily.to_numpy() < 0).any():
				raise ValueError(f"ERA5 year for LGD {code}, {year} failed full daily validation.")
			if len(set(tuple(map(float, point)) for point in year_metadata["points"])) != 3:
				raise ValueError(f"ERA5 LGD {code}, {year} does not have 3 distinct requested cells.")
			parts.append(daily)
			progress(f"YEAR_OK code={code} year={year} source={'cache' if was_cached else 'api'} dates={len(daily)}")
		district_series = pd.concat(parts).sort_index()
		if not district_series.index.equals(expected_dates) or district_series.index.has_duplicates or not np.isfinite(district_series.to_numpy()).all() or (district_series.to_numpy() < 0).any():
			raise ValueError(f"ERA5 district {code} failed full {RAINFALL_START}..{RAINFALL_END} validation.")
		series[code] = district_series
		verified_codes.add(code)
		metadata["districts"][str(code)] = {"district": name, "date_count": len(district_series), "start_date": RAINFALL_START.isoformat(), "end_date": RAINFALL_END.isoformat(), "three_distinct_effective_cells_per_year": True}
		progress(f"DISTRICT_VERIFIED code={code} name={name} fully_done={len(verified_codes - ORIGINAL_DISTRICTS)}/{len(new_codes)}")

	for code, daily in series.items():
		frames.append(pd.DataFrame({
			"date": daily.index,
			"lgd_code": int(code),
			"district": name_by_code[int(code)],
			"precipitation_sum_mm": daily.to_numpy(),
		}))
	combined = pd.concat(frames, ignore_index=True)
	combined["lgd_code"] = combined["lgd_code"].astype(int)
	for code in all_codes:
		rows = combined.loc[combined["lgd_code"].eq(code)].sort_values("date")
		if len(rows) != len(expected_dates) or not pd.DatetimeIndex(rows["date"]).equals(expected_dates):
			raise ValueError(f"ERA5 code {code} is not complete from {RAINFALL_START} through {RAINFALL_END}.")
		values = pd.to_numeric(rows["precipitation_sum_mm"], errors="coerce").to_numpy(dtype=float)
		if not np.isfinite(values).all() or (values < 0).any():
			raise ValueError(f"ERA5 code {code} has missing, non-finite, or negative rainfall.")
	combined = combined.sort_values(["lgd_code", "date"]).reset_index(drop=True)
	combined.to_csv(combined_path, index=False)
	manifest = {
		"label": "REAL DATA - ERA5 reanalysis rainfall",
		"source": "Open-Meteo Historical Weather API, models=era5",
		"complete_daily_range": [RAINFALL_START.isoformat(), RAINFALL_END.isoformat()],
		"districts": ranked_districts,
		"training_district_lgd_codes": training_codes,
		"fresh_test_district_lgd_codes": fresh_test_codes,
		"fetch_metadata": metadata,
		"rainfall_csv": str(combined_path),
	}
	manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
	return combined_path


def _training_monthly_means(rainfall: pd.Series) -> pd.Series:
	years = rainfall.index.year
	training = rainfall.loc[(years >= TRAIN_START_YEAR) & (years <= TRAIN_END_YEAR)]
	return training.groupby(training.index.month).mean()


def _rank_reference(rainfall: pd.Series) -> dict[int, np.ndarray]:
	years = rainfall.index.year
	training = rainfall.loc[(years >= TRAIN_START_YEAR) & (years <= TRAIN_END_YEAR)]
	return {
		month: np.sort(training.loc[training.index.month == month].to_numpy(dtype=float))
		for month in range(1, 13)
	}


def _district_features(
	rainfall: pd.Series,
	observation_dates: list[pd.Timestamp],
	monthly_means: pd.Series,
	rank_reference: dict[int, np.ndarray],
) -> pd.DataFrame:
	from scripts.build_real_dataset_v2 import _observation_features

	features = _observation_features(rainfall, observation_dates, monthly_means)
	previous_dates = pd.DatetimeIndex(features["date"] - pd.Timedelta(days=1))
	for days in (60, 90):
		values = []
		for previous_day in previous_dates:
			window = rainfall.loc[previous_day - pd.Timedelta(days=days - 1):previous_day]
			values.append(float(window.sum()) if len(window) == days and window.notna().all() else np.nan)
		features[f"rainfall_{days}d_total_mm"] = values
	three_day = features["rainfall_3d_total_mm"].to_numpy(dtype=float)
	thirty_day = features["rainfall_30d_total_mm"].to_numpy(dtype=float)
	features["rainfall_3d_to_30d_intensity_ratio"] = np.divide(
		10.0 * three_day,
		thirty_day,
		out=np.zeros(len(features), dtype=float),
		where=thirty_day > 0,
	)
	features["days_since_rain_gt20mm"] = features["days_since_rain_gt20mm"].fillna(30).clip(upper=30)
	previous_values = rainfall.reindex(previous_dates).to_numpy(dtype=float)
	prior_values = rainfall.reindex(previous_dates - pd.Timedelta(days=1)).to_numpy(dtype=float)
	features["previous_day_rainfall_change_mm"] = previous_values - prior_values
	ranks = []
	for timestamp, value in zip(previous_dates, previous_values):
		reference = rank_reference[timestamp.month]
		ranks.append(float(np.searchsorted(reference, value, side="right") / len(reference)) if len(reference) and np.isfinite(value) else np.nan)
	features["rainfall_rank_within_district_month"] = ranks
	return features


def build_real_dataset_v4(
	ifi_path: str | Path = IFI_PATH,
	rainfall_path: str | Path = EXPANDED_RAINFALL_PATH,
	output_path: str | Path = OUTPUT_PATH,
	boundary_path: str | Path = DEFAULT_BOUNDARY_PATH,
) -> dict[str, Any]:
	"""Build v4 using all qualifying districts and leave fresh-test districts out of training."""
	output = Path(output_path)
	if output.exists():
		raise FileExistsError(f"Refusing to overwrite existing output: {output}")
	ranked = rank_maharashtra_districts(ifi_path, boundary_path)
	training_codes, fresh_test_codes = split_districts(ranked)
	all_codes = set(training_codes) | set(fresh_test_codes)
	name_by_code = {int(row["lgd_code"]): str(row["district"]) for row in ranked}
	positive, blocked, dropped = _event_labels(ifi_path, all_codes, name_by_code)
	observations: dict[tuple[int, date], dict[str, Any]] = {}
	for (code, event_day), ueis in positive.items():
		observations[(code, event_day)] = {
			"date": event_day, "district": name_by_code[code], "lgd_code": code,
			"flood_risk": 1, "event_ueis": "|".join(sorted(ueis)),
		}
	for code in sorted(all_codes):
		for timestamp in pd.date_range(date(TRAIN_START_YEAR, 6, 1), date(TEST_END_YEAR, 9, 30), freq="D"):
			day = timestamp.date()
			if day.month in MONSOON_MONTHS and day not in blocked[code] and (code, day) not in observations:
				observations[(code, day)] = {
					"date": day, "district": name_by_code[code], "lgd_code": code,
					"flood_risk": 0, "event_ueis": "",
				}
	frame = pd.DataFrame(observations.values())
	frame["date"] = pd.to_datetime(frame["date"])
	frame["year"] = frame["date"].dt.year.astype("int16")
	frame["month"] = frame["date"].dt.month.astype("int8")
	if frame.duplicated(["lgd_code", "date"]).any():
		raise ValueError("Expanded dataset contains duplicate district-days.")
	rain = pd.read_csv(rainfall_path, parse_dates=["date"])
	required = {"date", "lgd_code", "district", "precipitation_sum_mm"}
	if required - set(rain.columns):
		raise ValueError(f"Expanded rainfall file is missing columns: {sorted(required - set(rain.columns))}")
	rain["lgd_code"] = rain["lgd_code"].astype(int)
	rain["precipitation_sum_mm"] = pd.to_numeric(rain["precipitation_sum_mm"], errors="coerce")
	expected_dates = pd.date_range(RAINFALL_START, RAINFALL_END, freq="D")
	feature_frames = []
	feature_reference: dict[str, Any] = {}
	for code in sorted(all_codes):
		group = rain.loc[rain["lgd_code"].eq(code)]
		series = group.set_index("date")["precipitation_sum_mm"].sort_index()
		if not pd.DatetimeIndex(series.index).equals(expected_dates) or series.isna().any() or not np.isfinite(series.to_numpy()).all():
			raise ValueError(f"Rainfall for LGD {code} is incomplete or contains missing values.")
		monthly_means = _training_monthly_means(series)
		rank_reference = _rank_reference(series)
		mask = frame["lgd_code"].eq(code)
		features = _district_features(series, frame.loc[mask, "date"].tolist(), monthly_means, rank_reference)
		features["lgd_code"] = code
		feature_frames.append(features)
		feature_reference[str(code)] = {
			"district": name_by_code[code],
			"training_monthly_means_mm": {str(int(month)): float(value) for month, value in monthly_means.items()},
			"rank_sample_count_by_month": {str(month): int(len(values)) for month, values in rank_reference.items()},
			"rank_reference_values_by_month": {str(month): [float(value) for value in values] for month, values in rank_reference.items()},
		}
	all_features = pd.concat(feature_frames, ignore_index=True)
	frame = frame.merge(all_features, on=["date", "month", "lgd_code"], how="left", validate="one_to_one")
	if frame[FEATURE_COLUMNS].isna().all(axis=None):
		raise ValueError("All expanded model features are missing.")
	for column in FEATURE_COLUMNS:
		if column != "days_since_rain_gt20mm" and column != "rainfall_60d_total_mm" and column != "rainfall_90d_total_mm" and frame[column].isna().any():
			raise ValueError(f"Feature {column} unexpectedly contains missing values.")
	frame["partition"] = np.where(frame["lgd_code"].isin(training_codes), "training_district", "fresh_test_district")
	frame = frame.sort_values(["date", "lgd_code"]).reset_index(drop=True)
	train_rows = frame[frame["partition"].eq("training_district") & frame["year"].between(TRAIN_START_YEAR, TRAIN_END_YEAR)]
	test_rows = frame[frame["partition"].eq("fresh_test_district") & frame["year"].between(TEST_START_YEAR, TEST_END_YEAR)]
	if train_rows["flood_risk"].nunique() != 2 or test_rows["flood_risk"].nunique() != 2:
		raise ValueError("Both classes are required in training and fresh-test partitions.")
	result = {
		"label": "REAL DATA - ERA5 reanalysis rainfall",
		"dataset": str(output),
		"rows": int(len(frame)),
		"event_count_rank_2000_2023": ranked,
		"training_district_lgd_codes": training_codes,
		"fresh_test_district_lgd_codes": fresh_test_codes,
		"training_districts": [row for row in ranked if row["lgd_code"] in training_codes],
		"fresh_test_districts": [row for row in ranked if row["lgd_code"] in fresh_test_codes],
		"training_years": [TRAIN_START_YEAR, TRAIN_END_YEAR],
		"original_district_second_look_years": [TEST_START_YEAR, TEST_END_YEAR],
		"fresh_test_years": [TEST_START_YEAR, TEST_END_YEAR],
		"training_class_counts": {str(k): int(v) for k, v in train_rows.flood_risk.value_counts().sort_index().items()},
		"fresh_test_class_counts": {str(k): int(v) for k, v in test_rows.flood_risk.value_counts().sort_index().items()},
		"training_district_rows": int(len(train_rows)),
		"fresh_test_rows": int(len(test_rows)),
		"dropped_events": dropped,
		"feature_columns": FEATURE_COLUMNS,
		"v2_feature_columns_retained": V2_FEATURE_COLUMNS,
		"added_feature_columns": ADDED_FEATURE_COLUMNS,
		"feature_baseline_years": [TRAIN_START_YEAR, TRAIN_END_YEAR],
		"negative_rule": "June-September district-days outside all matched IFI event intervals padded by three days before and after.",
		"prediction_features_end": "day before prediction day",
		"event_count_eligibility_uses_test_period": True,
		"test_notice": "Eligibility (>=10 events) and district counts use the requested 2000-2023 inventory; model fitting and selection exclude all fresh-test districts and all years after 2018.",
		"feature_reference": feature_reference,
		"test_district_row_overlap_with_training": int(frame.loc[frame.partition.eq("fresh_test_district"), "lgd_code"].isin(training_codes).sum()),
	}
	output.parent.mkdir(parents=True, exist_ok=True)
	frame.to_csv(output, index=False)
	return result


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--fetch", action="store_true", help="Fetch new district ERA5 rainfall into a new cache CSV first")
	parser.add_argument("--rainfall", default=str(EXPANDED_RAINFALL_PATH))
	parser.add_argument("--output", default=str(OUTPUT_PATH))
	parser.add_argument("--ifi", default=str(IFI_PATH))
	parser.add_argument("--boundary", default=str(DEFAULT_BOUNDARY_PATH))
	args = parser.parse_args()
	try:
		ranked = rank_maharashtra_districts(args.ifi, args.boundary)
		if args.fetch:
			rainfall_result = fetch_expanded_rainfall(ranked, args.boundary)
			if rainfall_result is None:
				parser.exit(3, f"ERA5 daily limit stopped fetch; see {FETCH_PROGRESS_PATH}. Verified districts are logged; await split approval before training.\n")
		result = build_real_dataset_v4(args.ifi, args.rainfall, args.output, args.boundary)
	except (FileNotFoundError, FileExistsError, ValueError) as exc:
		parser.exit(2, f"ERROR: {exc}\n")
	print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
	main()