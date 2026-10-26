from datetime import date
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd

from scripts.build_real_dataset_v4 import (
	FEATURE_COLUMNS,
	ORIGINAL_DISTRICTS,
	_rank_reference,
	_training_monthly_means,
	_district_features,
	rank_maharashtra_districts,
	split_districts,
	split_verified_districts,
)


def test_qualifying_district_split_is_spatially_disjoint_and_keeps_original_five():
	ranked = rank_maharashtra_districts()
	training_codes, fresh_test_codes = split_districts(ranked)

	assert len(ranked) == 31
	assert ORIGINAL_DISTRICTS.issubset(training_codes)
	assert set(training_codes).isdisjoint(fresh_test_codes)
	assert len(training_codes) == 21
	assert len(fresh_test_codes) == 10
	assert split_districts(ranked) == (training_codes, fresh_test_codes)


def test_partial_verified_district_split_is_deterministic_and_disjoint():
	ranked = rank_maharashtra_districts()
	verified = set(ORIGINAL_DISTRICTS) | {466, 468, 470, 472, 473, 475, 476}
	training_codes, fresh_test_codes = split_verified_districts(ranked, verified)

	assert ORIGINAL_DISTRICTS.issubset(training_codes)
	assert set(training_codes).isdisjoint(fresh_test_codes)
	assert set(training_codes) | set(fresh_test_codes) == verified
	assert len(fresh_test_codes) == 2
	assert split_verified_districts(ranked, verified) == (training_codes, fresh_test_codes)


def test_v4_builder_cli_imports_as_script():
	root = Path(__file__).resolve().parents[1]
	result = subprocess.run(
		[sys.executable, "scripts/build_real_dataset_v4.py", "--help"],
		cwd=root,
		capture_output=True,
		text=True,
		check=False,
	)
	assert result.returncode == 0, result.stderr
	assert "--fetch" in result.stdout


def test_expanded_features_only_use_rainfall_before_observation_and_train_baselines():
	dates = pd.date_range("2000-05-02", "2020-06-10", freq="D")
	rainfall = pd.Series(0.0, index=dates)
	rainfall.loc["2020-06-09"] = 6.0
	rainfall.loc["2020-06-10"] = 999.0
	features = _district_features(
		rainfall,
		[pd.Timestamp("2020-06-10")],
		_training_monthly_means(rainfall),
		_rank_reference(rainfall),
	).iloc[0]

	assert set(FEATURE_COLUMNS) - {"district"} <= set(features.index)
	assert features["rainfall_1d_total_mm"] == 6.0
	assert features["rainfall_60d_total_mm"] == 6.0
	assert features["rainfall_90d_total_mm"] == 6.0
	assert 999.0 not in features.to_list()
	assert features["days_since_rain_gt20mm"] == 30
	assert np.isfinite(features["rainfall_rank_within_district_month"])


def test_training_baselines_do_not_read_future_calendar_years():
	dates = pd.date_range("2018-01-01", "2020-12-31", freq="D")
	rainfall = pd.Series(1.0, index=dates)
	rainfall.loc["2019-06-01":] = 1000.0
	means = _training_monthly_means(rainfall)
	reference = _rank_reference(rainfall)

	assert means.loc[6] == 1.0
	assert len(reference[6]) == int(((dates.year == 2018) & (dates.month == 6)).sum())