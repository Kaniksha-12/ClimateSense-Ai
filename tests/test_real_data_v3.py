from datetime import date

import pandas as pd

from scripts.build_real_dataset_v3 import _add_lead_labels, _rainfall_features
from src.real_training_v3 import (
	CORE_FEATURE_COLUMNS,
	EXTENDED_FEATURE_COLUMNS,
	_select_validation_threshold,
)


def test_next_two_day_label_marks_event_day_and_two_prior_days():
	event_start = date(2020, 6, 10)
	ueis = {(482, event_start): {"UEI-2020"}}

	same_day, next_two_days = _add_lead_labels(ueis)

	assert same_day == {(482, event_start): {"UEI-2020"}}
	assert next_two_days == {
		(482, date(2020, 6, 8)): {"UEI-2020"},
		(482, date(2020, 6, 9)): {"UEI-2020"},
		(482, date(2020, 6, 10)): {"UEI-2020"},
	}


def test_v3_60_90_day_and_ratio_features_exclude_prediction_day():
	dates = pd.date_range("2020-05-02", "2020-08-10", freq="D")
	rainfall = pd.Series(0.0, index=dates)
	rainfall.loc["2020-08-09"] = 6.0
	rainfall.loc["2020-08-10"] = 999.0
	monthly_means = pd.Series({month: 0.0 for month in range(1, 13)})

	features = _rainfall_features(
		rainfall,
		[pd.Timestamp("2020-08-10")],
		monthly_means,
	).iloc[0]

	assert features["rainfall_1d_total_mm"] == 6.0
	assert features["rainfall_30d_total_mm"] == 6.0
	assert features["rainfall_60d_total_mm"] == 6.0
	assert features["rainfall_90d_total_mm"] == 6.0
	assert features["rainfall_3d_to_30d_intensity_ratio"] == 10.0
	assert 999.0 not in features.to_list()


def test_v3_feature_sets_exclude_labels_events_and_split_fields():
	protected = {"flood_risk", "same_day_flood_risk", "event_ueis", "date", "year", "lgd_code"}
	assert protected.isdisjoint(CORE_FEATURE_COLUMNS)
	assert protected.isdisjoint(EXTENDED_FEATURE_COLUMNS)
	assert "rainfall_60d_total_mm" in EXTENDED_FEATURE_COLUMNS
	assert "rainfall_90d_total_mm" in EXTENDED_FEATURE_COLUMNS
	assert "rainfall_3d_to_30d_intensity_ratio" in EXTENDED_FEATURE_COLUMNS


def test_v3_threshold_maximizes_validation_f2_with_precision_constraint():
	labels = pd.Series([0, 1, 0, 1]).to_numpy()
	probabilities = pd.Series([0.1, 0.4, 0.3, 0.8]).to_numpy()

	threshold, summary = _select_validation_threshold(labels, probabilities, probabilities)

	assert threshold == 0.4
	assert summary["precision"] == 1.0
	assert summary["recall"] == 1.0
	assert summary["f2"] == 1.0
	assert summary["precision_constraint_met"]