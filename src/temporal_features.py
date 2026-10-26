"""Fold-scoped rainfall climatology and chronological validation helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin, clone

RAIN_1D_COLUMN = "rainfall_1d_total_mm"
MONTH_COLUMN = "month"
ANOMALY_COLUMN = "rainfall_anomaly_vs_training_monthly_mean_mm"


class FoldAwareRainfallAnomaly(BaseEstimator, TransformerMixin):
	"""Replace stored anomaly values using statistics fitted on the current fit rows."""

	def __init__(self, min_monthly_observations: int = 2):
		self.min_monthly_observations = min_monthly_observations

	def fit(self, X: pd.DataFrame, y: Any = None) -> "FoldAwareRainfallAnomaly":
		if self.min_monthly_observations < 1:
			raise ValueError("min_monthly_observations must be at least one.")
		if not isinstance(X, pd.DataFrame):
			raise TypeError("FoldAwareRainfallAnomaly requires a pandas DataFrame.")
		missing = {RAIN_1D_COLUMN, MONTH_COLUMN, ANOMALY_COLUMN} - set(X.columns)
		if missing:
			raise ValueError(f"Rainfall anomaly input is missing columns: {sorted(missing)}.")

		rainfall = pd.to_numeric(X[RAIN_1D_COLUMN], errors="coerce").to_numpy(dtype=float)
		months = self._validated_months(X[MONTH_COLUMN])
		valid = np.isfinite(rainfall)
		if not valid.any():
			raise ValueError("Rainfall anomaly fit requires at least one finite training rainfall value.")

		self.global_mean_ = float(rainfall[valid].mean())
		self.monthly_counts_ = {
			month: int(np.count_nonzero(valid & (months == month)))
			for month in range(1, 13)
		}
		self.monthly_means_ = {
			month: (
				float(rainfall[valid & (months == month)].mean())
				if self.monthly_counts_[month] >= self.min_monthly_observations
				else self.global_mean_
			)
			for month in range(1, 13)
		}
		self.feature_names_in_ = np.asarray(X.columns, dtype=object)
		return self

	def transform(self, X: pd.DataFrame) -> pd.DataFrame:
		if not hasattr(self, "monthly_means_"):
			raise ValueError("FoldAwareRainfallAnomaly must be fitted before transform.")
		if not isinstance(X, pd.DataFrame):
			raise TypeError("FoldAwareRainfallAnomaly requires a pandas DataFrame.")
		missing = {RAIN_1D_COLUMN, MONTH_COLUMN, ANOMALY_COLUMN} - set(X.columns)
		if missing:
			raise ValueError(f"Rainfall anomaly input is missing columns: {sorted(missing)}.")

		rainfall = pd.to_numeric(X[RAIN_1D_COLUMN], errors="coerce").to_numpy(dtype=float)
		months = self._validated_months(X[MONTH_COLUMN])
		means = np.fromiter((self.monthly_means_[int(month)] for month in months), dtype=float)
		result = X.copy()
		result[ANOMALY_COLUMN] = rainfall - means
		return result

	@staticmethod
	def _validated_months(values: pd.Series) -> np.ndarray:
		numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
		if (
			not np.isfinite(numeric).all()
			or not np.equal(numeric, np.floor(numeric)).all()
			or np.any((numeric < 1) | (numeric > 12))
		):
			raise ValueError("Rainfall anomaly month values must be integers from 1 through 12.")
		return numeric.astype(np.int8)


def forward_chaining_year_splits(
	groups: np.ndarray,
	labels: np.ndarray,
	*,
	n_splits: int = 5,
	min_train_years: int = 4,
) -> list[tuple[np.ndarray, np.ndarray]]:
	"""Return deterministic expanding-window folds with disjoint, later-year validation blocks."""
	years = np.asarray(groups)
	target = np.asarray(labels)
	if years.ndim != 1 or target.ndim != 1 or len(years) != len(target):
		raise ValueError("Year groups and labels must be one-dimensional arrays of equal length.")
	if n_splits < 1 or min_train_years < 1:
		raise ValueError("n_splits and min_train_years must be positive.")
	if not np.isfinite(years).all() or not np.equal(years, np.floor(years)).all():
		raise ValueError("Year groups must contain finite integer years.")

	unique_years = np.sort(np.unique(years.astype(int)))
	if len(unique_years) <= min_train_years:
		raise ValueError("More distinct years than min_train_years are required for forward validation.")
	validation_years = unique_years[min_train_years:]
	blocks = [
		block
		for block in np.array_split(validation_years, min(n_splits, len(validation_years)))
		if len(block)
	]
	splits: list[tuple[np.ndarray, np.ndarray]] = []
	for block in blocks:
		train_indices = np.flatnonzero(years < int(block[0]))
		validation_indices = np.flatnonzero(np.isin(years, block))
		if not len(train_indices) or not len(validation_indices):
			raise ValueError("Forward validation produced an empty training or validation fold.")
		if len(np.unique(target[train_indices])) < 2 or len(np.unique(target[validation_indices])) < 2:
			raise ValueError(
				"Every forward training and validation fold must contain both classes."
			)
		splits.append((train_indices, validation_indices))
	return splits


def forward_chaining_oof_probabilities(
	estimator: Any,
	X: pd.DataFrame,
	labels: np.ndarray,
	splits: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray]:
	"""Return labels and probabilities only for rows scored in forward validation folds."""
	target = np.asarray(labels)
	observed: list[np.ndarray] = []
	probabilities: list[np.ndarray] = []
	for train_indices, validation_indices in splits:
		fitted = clone(estimator).fit(X.iloc[train_indices], target[train_indices])
		observed.append(target[validation_indices])
		probabilities.append(fitted.predict_proba(X.iloc[validation_indices])[:, 1])
	if not probabilities:
		raise ValueError("At least one forward validation fold is required for OOF probabilities.")
	return np.concatenate(observed), np.concatenate(probabilities)
