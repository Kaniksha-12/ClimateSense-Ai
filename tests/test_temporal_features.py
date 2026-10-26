import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from src.temporal_features import (
	FoldAwareRainfallAnomaly,
	forward_chaining_oof_probabilities,
	forward_chaining_year_splits,
)


def _features(rainfall: list[float], months: list[int]) -> pd.DataFrame:
	return pd.DataFrame(
		{
			"rainfall_1d_total_mm": rainfall,
			"rainfall_anomaly_vs_training_monthly_mean_mm": np.zeros(len(rainfall)),
			"month": months,
		}
	)


def test_validation_rainfall_cannot_change_fitted_monthly_baseline():
	training = _features([2.0, 4.0, 10.0, 14.0], [6, 6, 7, 7])
	validation = _features([100.0, 200.0], [6, 7])

	transformer = FoldAwareRainfallAnomaly().fit(training)
	before = transformer.transform(validation)
	changed_validation = validation.assign(rainfall_1d_total_mm=[100_000.0, 200_000.0])
	after = transformer.transform(changed_validation)

	assert transformer.monthly_means_[6] == 3.0
	assert transformer.monthly_means_[7] == 12.0
	assert transformer.monthly_means_ == {
		6: 3.0,
		7: 12.0,
		**{month: 7.5 for month in (1, 2, 3, 4, 5, 8, 9, 10, 11, 12)},
	}
	assert before["rainfall_anomaly_vs_training_monthly_mean_mm"].tolist() == [97.0, 188.0]
	assert after["rainfall_anomaly_vs_training_monthly_mean_mm"].tolist() == [
		99_997.0,
		199_988.0,
	]


def test_missing_or_insufficient_month_uses_training_global_mean():
	training = _features([2.0, 6.0, 10.0], [6, 7, 7])
	validation = _features([8.0, 12.0], [6, 8])

	transformer = FoldAwareRainfallAnomaly(min_monthly_observations=2).fit(training)
	result = transformer.transform(validation)

	assert transformer.monthly_counts_[6] == 1
	assert transformer.monthly_counts_[8] == 0
	assert transformer.monthly_means_[6] == 6.0
	assert transformer.monthly_means_[8] == 6.0
	assert result["rainfall_anomaly_vs_training_monthly_mean_mm"].tolist() == [2.0, 6.0]


def test_anomaly_fit_requires_at_least_one_finite_training_rainfall():
	training = _features([np.nan, np.inf], [6, 7])

	with pytest.raises(ValueError, match="at least one finite training rainfall"):
		FoldAwareRainfallAnomaly().fit(training)


def test_forward_chaining_year_split_boundaries_are_reproducible():
	groups = np.repeat(np.arange(2000, 2015), 2)
	labels = np.tile(np.array([0, 1]), 15)

	splits = forward_chaining_year_splits(
		groups,
		labels,
		n_splits=5,
		min_train_years=4,
	)
	repeated = forward_chaining_year_splits(
		groups,
		labels,
		n_splits=5,
		min_train_years=4,
	)

	assert [(groups[train].max(), groups[valid].min(), groups[valid].max()) for train, valid in splits] == [
		(2003, 2004, 2006),
		(2006, 2007, 2008),
		(2008, 2009, 2010),
		(2010, 2011, 2012),
		(2012, 2013, 2014),
	]
	assert all(np.array_equal(left, right) for first, second in zip(splits, repeated) for left, right in zip(first, second))
	assert set(np.concatenate([valid for _, valid in splits])) == set(np.flatnonzero(groups >= 2004))
	assert all(groups[train].max() < groups[valid].min() for train, valid in splits)


def test_forward_chaining_oof_excludes_initial_warmup_rows():
	groups = np.repeat(np.arange(2000, 2008), 2)
	labels = np.tile(np.array([0, 1]), 8)
	features = pd.DataFrame({"rainfall": np.arange(len(groups), dtype=float)})
	splits = forward_chaining_year_splits(
		groups,
		labels,
		n_splits=3,
		min_train_years=2,
	)

	oof_labels, probabilities = forward_chaining_oof_probabilities(
		DummyClassifier(strategy="prior"),
		features,
		labels,
		splits,
	)

	expected_indices = np.concatenate([valid for _, valid in splits])
	assert np.array_equal(oof_labels, labels[expected_indices])
	assert probabilities.shape == (len(expected_indices),)
	assert len(oof_labels) == np.count_nonzero(groups >= 2002)
