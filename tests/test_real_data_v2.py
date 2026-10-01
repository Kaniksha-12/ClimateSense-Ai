from datetime import date, timedelta

import pandas as pd

from scripts.build_real_dataset_v2 import (
	_observation_features,
	build_negative_dates,
	prepare_event_labels,
)
from src.real_training_v2 import FEATURE_COLUMNS, TARGET, _assert_no_leakage


def test_event_labels_require_single_state_and_aligned_district_codes():
	events = pd.DataFrame(
		[
			{
				"UEI": "valid",
				"State": "Maharashtra",
				"Districts": "Mumbai",
				"District_LGD_Codes": "482",
				"Start Date": "10-06-2020 12:00",
				"End Date": "11-06-2020 12:00",
				"Severity": None,
			},
			{
				"UEI": "multi-state",
				"State": "Maharashtra, Gujarat",
				"Districts": "Mumbai",
				"District_LGD_Codes": "482",
				"Start Date": "20-06-2020 12:00",
				"End Date": "20-06-2020 12:00",
				"Severity": "High",
			},
			{
				"UEI": "misaligned",
				"State": "Maharashtra",
				"Districts": "Mumbai, Pune",
				"District_LGD_Codes": "482",
				"Start Date": "25-06-2020 12:00",
				"End Date": "25-06-2020 12:00",
				"Severity": "Low",
			},
		],
	)

	positives, blocked, dropped = prepare_event_labels(events)

	assert positives == {(482, date(2020, 6, 10)): {"valid"}}
	assert blocked[482] == {date(2020, 6, 10) + timedelta(days=offset) for offset in range(-3, 5)}
	assert dropped["not_single_state_maharashtra"] == 1
	assert dropped["district_lgd_token_count_mismatch"] == 1
	assert dropped["unique_positive_district_start_dates"] == 1


def test_negative_days_exclude_event_and_three_day_padding():
	blocked = {482: {date(2020, 6, 10) + timedelta(days=offset) for offset in range(-3, 5)}}
	negatives = set(build_negative_dates(blocked, start_year=2020, end_year=2020))

	assert all((482, date(2020, 6, 10) + timedelta(days=offset)) not in negatives for offset in range(-3, 5))
	assert (482, date(2020, 6, 6)) in negatives
	assert (482, date(2020, 6, 15)) in negatives
	assert all(day.month in {6, 7, 8, 9} for _, day in negatives)


def test_rainfall_features_end_on_previous_day_only():
	dates = pd.date_range("2020-05-02", "2020-06-10", freq="D")
	rainfall = pd.Series(0.0, index=dates)
	rainfall.loc["2020-06-09"] = 6.0
	rainfall.loc["2020-06-10"] = 999.0
	means = pd.Series({5: 1.0, 6: 2.0})

	features = _observation_features(
		rainfall,
		[pd.Timestamp("2020-06-10")],
		means,
	).iloc[0]

	assert features["rainfall_1d_total_mm"] == 6.0
	assert features["rainfall_1d_max_daily_mm"] == 6.0
	assert features["rainfall_anomaly_vs_training_monthly_mean_mm"] == 4.0
	assert features["rainfall_30d_total_mm"] == 6.0
	assert 999.0 not in features.to_list()


def test_training_features_and_temporal_partitions_do_not_leak():
	protected = {TARGET, "event_ueis", "date", "year", "lgd_code"}
	assert protected.isdisjoint(FEATURE_COLUMNS)
	feature_values = {column: 0.0 for column in FEATURE_COLUMNS}
	feature_values["district"] = "Mumbai (LGD 482)"
	training = pd.DataFrame(
		[{**feature_values, "lgd_code": 482, "date": pd.Timestamp("2018-06-10"), "event_ueis": "event-train"}]
	)
	test = pd.DataFrame(
		[{**feature_values, "lgd_code": 482, "date": pd.Timestamp("2019-06-10"), "event_ueis": "event-test"}]
	)

	assert _assert_no_leakage(pd.concat([training, test]), training, test) == {
		"row_overlap": 0,
		"event_overlap": 0,
	}