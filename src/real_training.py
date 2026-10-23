"""Train and evaluate calibrated classifiers on IFI-Impacts / ERA5 data."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
	accuracy_score,
	average_precision_score,
	balanced_accuracy_score,
	confusion_matrix,
	f1_score,
	precision_score,
	recall_score,
	roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, cross_validate
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src.config import MODELS_DIR, REPORTS_DIR
from src.label_contract import IFI_SAME_DAY_SPEC_ID, validate_ifi_association_rows
from src.preprocessing import build_preprocessor

logger = logging.getLogger(__name__)

DATASET_PATH = Path("data/processed/real_flood_dataset.csv")
MODEL_PATH = MODELS_DIR / "real_flood_v1.pkl"
JSON_REPORT_PATH = REPORTS_DIR / "real_data_evaluation.json"
MARKDOWN_REPORT_PATH = REPORTS_DIR / "real_data_evaluation.md"
TARGET = "label_value"
TARGET_SPEC_ID = IFI_SAME_DAY_SPEC_ID
FEATURE_COLUMNS = [
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
SCORING = {
	"accuracy": "accuracy",
	"balanced_accuracy": "balanced_accuracy",
	"precision": "precision",
	"recall": "recall",
	"f1": "f1",
	"roc_auc": "roc_auc",
	"pr_auc": "average_precision",
}


class EarlyStoppingXGBClassifier(ClassifierMixin, BaseEstimator):
	"""XGBoost classifier with a chronological tail used only for early stopping."""

	def __init__(
		self,
		n_estimators: int = 240,
		max_depth: int = 3,
		learning_rate: float = 0.05,
		min_child_weight: float = 1.0,
		subsample: float = 0.9,
		colsample_bytree: float = 0.9,
		reg_alpha: float = 0.0,
		reg_lambda: float = 1.0,
		early_stopping_rounds: int = 25,
		validation_fraction: float = 0.15,
		random_state: int = 42,
		n_jobs: int = 2,
		use_early_stopping: bool = True,
	):
		self.n_estimators = n_estimators
		self.max_depth = max_depth
		self.learning_rate = learning_rate
		self.min_child_weight = min_child_weight
		self.subsample = subsample
		self.colsample_bytree = colsample_bytree
		self.reg_alpha = reg_alpha
		self.reg_lambda = reg_lambda
		self.early_stopping_rounds = early_stopping_rounds
		self.validation_fraction = validation_fraction
		self.random_state = random_state
		self.n_jobs = n_jobs
		self.use_early_stopping = use_early_stopping

	def fit(self, X: Any, y: Any) -> "EarlyStoppingXGBClassifier":
		features = np.asarray(X)
		labels = np.asarray(y, dtype=np.int8)
		self.classes_ = np.unique(labels)
		self.n_features_in_ = int(features.shape[1])
		if len(self.classes_) != 2:
			raise ValueError("EarlyStoppingXGBClassifier requires both binary classes.")
		validation_count = max(2, int(np.ceil(len(labels) * self.validation_fraction)))
		fit_count = len(labels) - validation_count
		can_early_stop = (
			self.use_early_stopping
			and fit_count >= 10
			and len(np.unique(labels[:fit_count])) == 2
			and len(np.unique(labels[fit_count:])) == 2
		)
		fit_labels = labels[:fit_count] if can_early_stop else labels
		positive_count = int((fit_labels == 1).sum())
		negative_count = int((fit_labels == 0).sum())
		parameters: dict[str, Any] = {
			"n_estimators": int(self.n_estimators),
			"max_depth": int(self.max_depth),
			"learning_rate": float(self.learning_rate),
			"min_child_weight": float(self.min_child_weight),
			"subsample": float(self.subsample),
			"colsample_bytree": float(self.colsample_bytree),
			"reg_alpha": float(self.reg_alpha),
			"reg_lambda": float(self.reg_lambda),
			"random_state": int(self.random_state),
			"n_jobs": int(self.n_jobs),
			"tree_method": "hist",
			"objective": "binary:logistic",
			"eval_metric": "aucpr",
			"scale_pos_weight": negative_count / max(positive_count, 1),
		}
		if can_early_stop:
			parameters["early_stopping_rounds"] = int(self.early_stopping_rounds)
		self.model_ = XGBClassifier(**parameters)
		if can_early_stop:
			self.model_.fit(
				features[:fit_count],
				labels[:fit_count],
				eval_set=[(features[fit_count:], labels[fit_count:])],
				verbose=False,
			)
		else:
			self.model_.fit(features, labels, verbose=False)
		self.best_iteration_ = int(
			getattr(self.model_, "best_iteration", self.n_estimators - 1)
		)
		self.early_stopping_used_ = bool(can_early_stop)
		return self

	def predict_proba(self, X: Any) -> np.ndarray:
		return self.model_.predict_proba(X)

	def predict(self, X: Any) -> np.ndarray:
		return self.model_.predict(X)

	@property
	def feature_importances_(self) -> np.ndarray:
		return self.model_.feature_importances_


def _make_pipeline(classifier: Any, training_features: pd.DataFrame) -> Pipeline:
	return Pipeline(
		[
			("preprocessor", build_preprocessor(training_features)),
			("classifier", classifier),
		]
	)


def _group_year_splits(
	features: pd.DataFrame,
	labels: np.ndarray,
	groups: np.ndarray,
	n_splits: int,
	repeats: int = 1,
) -> list[tuple[np.ndarray, np.ndarray]]:
	"""Make expanding-window folds with whole years held out in chronological blocks."""
	unique_years = np.sort(np.unique(groups))
	if len(unique_years) < 3:
		raise ValueError("At least three training years are required for grouped validation.")
	base_warmup = min(max(2, len(unique_years) // 4), len(unique_years) - 2)
	splits: list[tuple[np.ndarray, np.ndarray]] = []
	for repeat in range(repeats):
		warmup = min(base_warmup + repeat, len(unique_years) - 2)
		validation_years = unique_years[warmup:]
		fold_count = min(n_splits, len(validation_years))
		for year_block in np.array_split(validation_years, fold_count):
			if len(year_block) == 0:
				continue
			train_indices = np.flatnonzero(groups < int(year_block[0]))
			validation_indices = np.flatnonzero(np.isin(groups, year_block))
			if (
				len(train_indices)
				and len(validation_indices)
				and len(np.unique(labels[train_indices])) == 2
				and len(np.unique(labels[validation_indices])) == 2
			):
				splits.append((train_indices, validation_indices))
	if len(splits) < 2:
		raise ValueError("Not enough two-class expanding-window year folds for validation.")
	return splits


def _forward_year_splits(frame: pd.DataFrame, minimum_warmup_years: int = 4, folds: int = 5) -> list[tuple[np.ndarray, np.ndarray]]:
	years = np.sort(frame["year"].unique())
	if len(years) <= minimum_warmup_years:
		raise ValueError("Not enough years for forward-chaining OOF threshold selection.")
	validation_years = years[minimum_warmup_years:]
	blocks = [block for block in np.array_split(validation_years, min(folds, len(validation_years))) if len(block)]
	splits = []
	for block in blocks:
		train_indices = np.flatnonzero(frame["year"].to_numpy() < int(block[0]))
		validation_indices = np.flatnonzero(frame["year"].isin(block).to_numpy())
		if len(train_indices) and len(validation_indices):
			splits.append((train_indices, validation_indices))
	return splits


def _inner_calibration_splits(frame: pd.DataFrame) -> list[tuple[np.ndarray, np.ndarray]]:
	groups = frame["year"].to_numpy()
	features = frame[FEATURE_COLUMNS]
	labels = frame[TARGET].to_numpy(dtype=np.int8)
	return _group_year_splits(features, labels, groups, n_splits=min(3, len(np.unique(groups))))


def _freeze_classifier_early_stopping(classifier: Any) -> Any:
	"""Freeze XGBoost tree counts and disable inner holdout for the final refit."""
	frozen = clone(classifier)
	if isinstance(classifier, EarlyStoppingXGBClassifier):
		n_estimators = min(
			int(classifier.n_estimators),
			int(getattr(classifier, "best_iteration_", classifier.n_estimators - 1)) + 1,
		)
		frozen.set_params(n_estimators=max(n_estimators, 1), use_early_stopping=False)
	elif isinstance(classifier, VotingClassifier):
		frozen.set_params(
			estimators=[
				(name, _freeze_classifier_early_stopping(component))
				for name, component in classifier.estimators
			]
		)
	return frozen


def _freeze_xgboost_early_stopping(estimator: Pipeline) -> Pipeline:
	"""Use CV-selected tree counts and refit XGBoost on all training rows."""
	frozen = clone(estimator)
	frozen.set_params(classifier=_freeze_classifier_early_stopping(estimator.named_steps["classifier"]))
	return frozen


def _select_threshold(
	labels: np.ndarray,
	probabilities: np.ndarray,
	recall_target: float = 0.8,
	minimum_precision: float = 0.5,
) -> tuple[float, dict[str, Any]]:
	thresholds = np.unique(np.concatenate(([0.0], probabilities, [1.0])))
	rows = []
	for threshold in thresholds:
		predictions = (probabilities >= threshold).astype(np.int8)
		precision = float(precision_score(labels, predictions, zero_division=0))
		recall = float(recall_score(labels, predictions, zero_division=0))
		f1 = float(f1_score(labels, predictions, zero_division=0))
		rows.append((float(threshold), precision, recall, f1))
	feasible = [row for row in rows if row[2] >= recall_target and row[1] >= minimum_precision]
	policy = "recall_target_and_minimum_precision"
	if not feasible:
		feasible = [row for row in rows if row[2] >= recall_target]
		policy = "recall_target_only_no_precision_feasible"
	if not feasible:
		feasible = rows
		policy = "maximum_available_recall"
	selected = max(feasible, key=lambda row: (row[3], row[1], row[2], -row[0]))
	return selected[0], {
		"threshold": selected[0],
		"oof_precision": selected[1],
		"oof_recall": selected[2],
		"oof_f1": selected[3],
		"recall_target": recall_target,
		"minimum_precision": minimum_precision,
		"selection_policy": policy,
	}


def _score_predictions(labels: np.ndarray, predictions: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
	return {
		"accuracy": float(accuracy_score(labels, predictions)),
		"balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
		"precision": float(precision_score(labels, predictions, zero_division=0)),
		"recall": float(recall_score(labels, predictions, zero_division=0)),
		"f1": float(f1_score(labels, predictions, zero_division=0)),
		"roc_auc": float(roc_auc_score(labels, probabilities)),
		"pr_auc": float(average_precision_score(labels, probabilities)),
		"confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
	}


def _bootstrap_intervals(
	labels: np.ndarray,
	predictions: np.ndarray,
	probabilities: np.ndarray,
	baseline_predictions: np.ndarray,
	baseline_probabilities: np.ndarray,
	iterations: int = 2000,
	seed: int = 2026,
) -> dict[str, Any]:
	rng = np.random.default_rng(seed)
	metric_names = ("accuracy", "balanced_accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc")
	model_samples: dict[str, list[float]] = {name: [] for name in metric_names}
	baseline_samples: dict[str, list[float]] = {name: [] for name in metric_names}
	differences: dict[str, list[float]] = {name: [] for name in metric_names}
	for _ in range(iterations):
		indices = rng.integers(0, len(labels), size=len(labels))
		sampled_labels = labels[indices]
		if len(np.unique(sampled_labels)) < 2:
			continue
		model_metrics = _score_predictions(sampled_labels, predictions[indices], probabilities[indices])
		baseline_metrics = _score_predictions(
			sampled_labels,
			baseline_predictions[indices],
			baseline_probabilities[indices],
		)
		for name in metric_names:
			model_samples[name].append(float(model_metrics[name]))
			baseline_samples[name].append(float(baseline_metrics[name]))
			differences[name].append(float(model_metrics[name] - baseline_metrics[name]))
	intervals = lambda values: [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]
	return {
		"method": "paired nonparametric bootstrap over held-out test rows; resamples with one class are skipped",
		"requested_iterations": iterations,
		"valid_iterations": len(model_samples["accuracy"]),
		"confidence_level": 0.95,
		"model_metrics": {name: intervals(values) for name, values in model_samples.items()},
		"majority_baseline_metrics": {name: intervals(values) for name, values in baseline_samples.items()},
		"paired_model_minus_majority_difference": {
			name: intervals(values) for name, values in differences.items()
		},
	}


def _selected_cv_metrics(search: RandomizedSearchCV, scoring: dict[str, str]) -> dict[str, Any]:
	best_index = int(search.best_index_)
	fold_count = len([key for key in search.cv_results_ if key.startswith("split") and key.endswith("_test_pr_auc")])
	result: dict[str, Any] = {}
	for metric in scoring:
		values = np.asarray(
			[search.cv_results_[f"split{fold}_test_{metric}"][best_index] for fold in range(fold_count)],
			dtype=float,
		)
		result[metric] = {
			"mean": float(np.nanmean(values)),
			"std": float(np.nanstd(values, ddof=1)),
			"fold_scores": [float(value) for value in values],
		}
	return result


def _make_search_spaces(seed: int) -> dict[str, tuple[Any, dict[str, list[Any]]]]:
	logistic = LogisticRegression(
		solver="liblinear",
		max_iter=2000,
		random_state=seed,
	)
	random_forest = RandomForestClassifier(
		random_state=seed,
		n_jobs=2,
	)
	xgboost = EarlyStoppingXGBClassifier(random_state=seed, n_jobs=2)
	return {
		"LogisticRegression": (
			logistic,
			{
				"classifier__C": [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0],
				"classifier__class_weight": ["balanced", None],
				"classifier__tol": [1e-3, 1e-4],
			},
		),
		"RandomForest": (
			random_forest,
			{
				"classifier__n_estimators": [150, 250, 400],
				"classifier__max_depth": [None, 4, 8, 12],
				"classifier__min_samples_split": [2, 5, 10],
				"classifier__min_samples_leaf": [1, 2, 4, 8],
				"classifier__max_features": ["sqrt", 0.7],
				"classifier__class_weight": ["balanced", "balanced_subsample"],
			},
		),
		"XGBoost": (
			xgboost,
			{
				"classifier__n_estimators": [100, 160, 240, 320],
				"classifier__max_depth": [2, 3, 4],
				"classifier__learning_rate": [0.025, 0.05, 0.08],
				"classifier__min_child_weight": [1.0, 3.0, 5.0],
				"classifier__subsample": [0.7, 0.9, 1.0],
				"classifier__colsample_bytree": [0.7, 0.9, 1.0],
				"classifier__reg_alpha": [0.0, 0.1, 0.5],
				"classifier__reg_lambda": [0.5, 1.0, 3.0, 5.0],
			},
		),
	}


def _pipeline_importance(pipeline: Pipeline) -> list[dict[str, Any]]:
	feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
	classifier = pipeline.named_steps["classifier"]
	values: np.ndarray | None = None
	if hasattr(classifier, "feature_importances_"):
		values = np.asarray(classifier.feature_importances_, dtype=float)
	elif hasattr(classifier, "coef_"):
		values = np.abs(np.asarray(classifier.coef_, dtype=float)).reshape(-1)
	elif isinstance(classifier, VotingClassifier):
		component_importances = []
		for fitted in classifier.named_estimators_.values():
			if hasattr(fitted, "feature_importances_"):
				component_importances.append(np.asarray(fitted.feature_importances_, dtype=float))
			elif hasattr(fitted, "coef_"):
				component_importances.append(np.abs(np.asarray(fitted.coef_, dtype=float)).reshape(-1))
		if component_importances:
			values = np.mean(component_importances, axis=0)
	if values is None or len(values) != len(feature_names):
		return []
	order = np.argsort(values)[::-1]
	return [
		{"feature": str(feature_names[index]), "importance": float(values[index])}
		for index in order[:20]
	]


def _markdown_report(report: dict[str, Any]) -> str:
	lines = [
		"# REAL DATA (ERA5 rainfall)",
		"",
		"> IFI event-association target only; an inventory non-match is not evidence of no flooding. ERA5 is reanalysis, not observed station rainfall.",
		"",
		"## Data and split",
		"",
		f"- Dataset rows: {report['dataset']['rows']} ({report['dataset']['positive_count']} positive, {report['dataset']['negative_count']} negative).",
		f"- Train: {report['split']['train_years'][0]}–{report['split']['train_years'][1]} ({report['split']['training_rows']} rows); test: {report['split']['test_years'][0]}–{report['split']['test_years'][1]} ({report['split']['test_rows']} rows).",
		f"- Test classes: {report['split']['test_class_counts']}.",
		f"- Threshold: {report['threshold_selection']['threshold']:.4f}, selected from forward-year OOF training predictions ({report['threshold_selection']['selection_policy']}).",
		"- No test-year observations were used for tuning, calibration, threshold selection, or model choice.",
		"",
		"## Final test comparison",
		"",
		"All confusion matrices use `[[TN, FP], [FN, TP]]`. CV entries are mean ± standard deviation across repeated year-grouped folds within 2000–2018.",
		"",
		"| Model | Accuracy | Balanced accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Confusion matrix | CV PR-AUC mean ± std |",
		"|---|---:|---:|---:|---:|---:|---:|---:|---|---:|",
	]
	for name, values in report["comparisons"].items():
		metrics = values["test_metrics"]
		cv = values.get("cv_metrics", {}).get("pr_auc", {})
		cv_value = f"{cv['mean']:.3f} ± {cv['std']:.3f}" if cv else "—"
		matrix = str(metrics["confusion_matrix"])
		lines.append(
			f"| {name} | {metrics['accuracy']:.3f} | {metrics['balanced_accuracy']:.3f} | "
			f"{metrics['precision']:.3f} | {metrics['recall']:.3f} | {metrics['f1']:.3f} | "
			f"{metrics['roc_auc']:.3f} | {metrics['pr_auc']:.3f} | `{matrix}` | {cv_value} |"
		)
	lines.extend(["", "## Bootstrap and verdict", ""])
	for name, values in report["comparisons"].items():
		ci = values["bootstrap_95_ci"]
		model_f1_ci = ci["model_metrics"]["f1"]
		if "paired_model_minus_majority_difference" not in ci:
			lines.append(f"- **{name}:** F1 95% CI {model_f1_ci[0]:.3f}–{model_f1_ci[1]:.3f}.")
			continue
		diff = ci["paired_model_minus_majority_difference"]["f1"]
		verdict = "F1 difference CI excludes zero" if diff[0] > 0 else "F1 improvement over majority is not established by the paired 95% CI"
		lines.append(
			f"- **{name}:** F1 95% CI {model_f1_ci[0]:.3f}–{model_f1_ci[1]:.3f}; "
			f"paired F1 difference vs majority baseline {diff[0]:.3f}–{diff[1]:.3f}; {verdict}."
		)
	lines.extend(["", "## Feature importance", ""])
	for item in report["feature_importance"]:
		lines.append(f"- `{item['feature']}`: {item['importance']:.5f}")
	lines.extend(["", "## Provenance and limitations", "", report["limitations"], ""])
	return "\n".join(lines)


def train_real_model(
	dataset_path: str | Path = DATASET_PATH,
	model_path: str | Path = MODEL_PATH,
	json_report_path: str | Path = JSON_REPORT_PATH,
	markdown_report_path: str | Path = MARKDOWN_REPORT_PATH,
	n_iter: int = 30,
	n_repeats: int = 2,
	bootstrap_iterations: int = 2000,
	force: bool = False,
) -> dict[str, Any]:
	"""Tune within train years, calibrate/threshold with OOF train predictions, test once."""
	if n_iter < 1 or n_repeats < 1:
		raise ValueError("n_iter and n_repeats must be positive.")
	for path in (Path(model_path), Path(json_report_path), Path(markdown_report_path)):
		if path.exists() and not force:
			raise FileExistsError(f"Refusing to overwrite existing output: {path}; pass --force to replace it.")
	frame = pd.read_csv(dataset_path, parse_dates=["date"])
	label_eligibility = validate_ifi_association_rows(
		frame.to_dict(orient="records"),
		target_spec_id=TARGET_SPEC_ID,
	)
	if TARGET not in frame:
		raise ValueError(f"Real dataset is missing the required target field {TARGET!r}.")
	frame[TARGET] = label_eligibility.label_values
	required = {"date", "year", TARGET, *FEATURE_COLUMNS}
	missing_columns = required - set(frame.columns)
	if missing_columns:
		raise ValueError(f"Real dataset is missing columns: {sorted(missing_columns)}")
	if set(frame[TARGET].dropna().unique()) != {0, 1}:
		raise ValueError("Eligible IFI association target must contain exactly binary classes 0 and 1.")
	if frame[FEATURE_COLUMNS].columns.intersection([TARGET, "flood_risk", "event_ueis", "date", "year"]).size:
		raise ValueError("Target, event IDs, and split time fields must not enter the feature matrix.")
	if frame.duplicated(["lgd_code", "date"]).any():
		raise ValueError("Real dataset contains duplicate district-days.")
	frame["__label_training_eligible"] = label_eligibility.training_eligible
	frame["__label_evaluation_eligible"] = label_eligibility.evaluation_eligible
	frame = frame.sort_values(["date", "lgd_code"]).reset_index(drop=True)
	training = frame.loc[
		frame["year"].between(2000, 2018) & frame["__label_training_eligible"]
	].reset_index(drop=True)
	test = frame.loc[
		frame["year"].between(2019, 2023) & frame["__label_evaluation_eligible"]
	].reset_index(drop=True)
	frame = frame.drop(columns=["__label_training_eligible", "__label_evaluation_eligible"])
	training = training.drop(columns=["__label_training_eligible", "__label_evaluation_eligible"])
	test = test.drop(columns=["__label_training_eligible", "__label_evaluation_eligible"])
	if training.empty or test.empty:
		raise ValueError("Required temporal train (2000–2018) and test (2019–2023) partitions must both be nonempty.")
	for partition_name, partition in (("training", training), ("test", test)):
		if set(partition[TARGET].unique()) != {0, 1}:
			raise ValueError(f"{partition_name} years do not contain both classes; do not silently alter the split.")

	X_train = training[FEATURE_COLUMNS].copy()
	y_train = training[TARGET].to_numpy(dtype=np.int8)
	train_groups = training["year"].to_numpy(dtype=int)
	cv_splits = _group_year_splits(X_train, y_train, train_groups, n_splits=5, repeats=n_repeats)
	spaces = _make_search_spaces(seed=42)
	searches: dict[str, RandomizedSearchCV] = {}
	best_estimators: dict[str, Pipeline] = {}
	cv_metrics: dict[str, dict[str, Any]] = {}
	for name, (classifier, distribution) in spaces.items():
		logger.info("Searching %s with %d iterations and %d grouped folds", name, n_iter, len(cv_splits))
		search = RandomizedSearchCV(
			estimator=_make_pipeline(classifier, X_train),
			param_distributions=distribution,
			n_iter=n_iter,
			scoring=SCORING,
			refit="pr_auc",
			cv=cv_splits,
			random_state=42,
			n_jobs=1,
			return_train_score=False,
			error_score="raise",
		)
		search.fit(X_train, y_train)
		searches[name] = search
		best_estimators[name] = search.best_estimator_
		cv_metrics[name] = _selected_cv_metrics(search, SCORING)
		logger.info("%s best mean CV PR-AUC %.4f", name, cv_metrics[name]["pr_auc"]["mean"])

	soft_voting = VotingClassifier(
		estimators=[
			(name, estimator.named_steps["classifier"])
			for name, estimator in best_estimators.items()
		],
		voting="soft",
		weights=[1, 1, 1],
		n_jobs=1,
	)
	soft_pipeline = _make_pipeline(soft_voting, X_train)
	ensemble_folds = cross_validate(
		soft_pipeline,
		X_train,
		y_train,
		cv=cv_splits,
		scoring=SCORING,
		n_jobs=1,
		error_score="raise",
	)
	cv_metrics["SoftVotingEnsemble"] = {
		metric: {
			"mean": float(np.nanmean(ensemble_folds[f"test_{metric}"])),
			"std": float(np.nanstd(ensemble_folds[f"test_{metric}"], ddof=1)),
			"fold_scores": [float(value) for value in ensemble_folds[f"test_{metric}"]],
		}
		for metric in SCORING
	}
	best_name = max(
		cv_metrics,
		key=lambda name: (
			cv_metrics[name]["pr_auc"]["mean"],
			cv_metrics[name]["roc_auc"]["mean"],
			cv_metrics[name]["recall"]["mean"],
		),
	)
	selected = soft_pipeline if best_name == "SoftVotingEnsemble" else best_estimators[best_name]
	selected_full_fit = _freeze_xgboost_early_stopping(selected)

	threshold_oof_labels: list[int] = []
	threshold_oof_probabilities: list[float] = []
	threshold_splits = _forward_year_splits(training)
	for outer_train, outer_validation in threshold_splits:
		outer_training = training.iloc[outer_train].reset_index(drop=True)
		outer_features = outer_training[FEATURE_COLUMNS]
		outer_labels = outer_training[TARGET].to_numpy(dtype=np.int8)
		outer_groups = outer_training["year"].to_numpy(dtype=int)
		inner_splits = _group_year_splits(
			outer_features,
			outer_labels,
			outer_groups,
			n_splits=min(3, len(np.unique(outer_groups))),
			repeats=1,
		)
		calibrated_oof = CalibratedClassifierCV(
			estimator=clone(selected_full_fit),
			method="sigmoid",
			cv=inner_splits,
			ensemble=False,
			n_jobs=1,
		)
		calibrated_oof.fit(outer_features, outer_labels)
		validation_features = training.iloc[outer_validation][FEATURE_COLUMNS]
		probabilities = calibrated_oof.predict_proba(validation_features)[:, 1]
		threshold_oof_labels.extend(training.iloc[outer_validation][TARGET].astype(int).tolist())
		threshold_oof_probabilities.extend(probabilities.astype(float).tolist())
	threshold, threshold_metadata = _select_threshold(
		np.asarray(threshold_oof_labels, dtype=np.int8),
		np.asarray(threshold_oof_probabilities, dtype=float),
	)
	threshold_metadata["oof_training_rows"] = len(threshold_oof_labels)
	threshold_metadata["oof_years"] = [
		int(training.iloc[validation]["year"].min())
		for _, validation in threshold_splits
	]

	calibration_splits = _inner_calibration_splits(training)
	final_model = CalibratedClassifierCV(
		estimator=selected_full_fit,
		method="sigmoid",
		cv=calibration_splits,
		ensemble=False,
		n_jobs=1,
	)
	final_model.fit(X_train, y_train)

	X_test = test[FEATURE_COLUMNS].copy()
	y_test = test[TARGET].to_numpy(dtype=np.int8)
	test_probabilities = final_model.predict_proba(X_test)[:, 1]
	test_predictions = (test_probabilities >= threshold).astype(np.int8)
	training_majority = int(pd.Series(y_train).value_counts().idxmax())
	baseline_predictions = np.full(len(y_test), training_majority, dtype=np.int8)
	training_prevalence = float(y_train.mean())
	baseline_probabilities = np.full(len(y_test), training_prevalence, dtype=float)
	model_test_metrics = _score_predictions(y_test, test_predictions, test_probabilities)
	baseline_test_metrics = _score_predictions(y_test, baseline_predictions, baseline_probabilities)
	model_bootstrap = _bootstrap_intervals(
		y_test,
		test_predictions,
		test_probabilities,
		baseline_predictions,
		baseline_probabilities,
		iterations=bootstrap_iterations,
	)
	baseline_bootstrap = {
		"method": model_bootstrap["method"],
		"requested_iterations": model_bootstrap["requested_iterations"],
		"valid_iterations": model_bootstrap["valid_iterations"],
		"confidence_level": model_bootstrap["confidence_level"],
		"model_metrics": model_bootstrap["majority_baseline_metrics"],
	}

	calibrated_base = final_model.calibrated_classifiers_[0].estimator
	feature_importance = _pipeline_importance(calibrated_base)
	class_counts = frame[TARGET].value_counts().sort_index()
	test_counts = test[TARGET].value_counts().sort_index()
	train_counts = training[TARGET].value_counts().sort_index()
	metadata = {
		"label": "REAL DATA (ERA5 rainfall)",
		"model_name": best_name,
		"target": TARGET,
		"target_spec_id": TARGET_SPEC_ID,
		"target_interpretation": "IFI event-start association only; a negative is a no-match in the declared inventory snapshot, not verified absence of flooding.",
		"label_provenance": {
			"inventory_snapshot_id": sorted(frame["label_inventory_snapshot_id"].unique().tolist()),
			"matching_rule_id": sorted(frame["label_matching_rule_id"].unique().tolist()),
			"matching_rule_version": sorted(frame["label_matching_rule_version"].unique().tolist()),
		},
		"positive_label": 1,
		"feature_columns": FEATURE_COLUMNS,
		"districts": sorted(training["district"].unique().tolist()),
		"district_lgd_codes": sorted(int(value) for value in training["lgd_code"].unique()),
		"decision_threshold": threshold,
		"calibration": "CalibratedClassifierCV(method=sigmoid, grouped year folds, ensemble=False)",
		"random_state": 42,
	}
	report = {
		"label": "REAL DATA (ERA5 rainfall)",
		"target_spec_id": TARGET_SPEC_ID,
		"target_interpretation": "IFI event-start association only; negatives mean no match in the declared inventory snapshot, not verified absence of flooding.",
		"data_notice": "IFI event-association proxy labels with ERA5 reanalysis rainfall; inventory non-matches are not flood-absence labels, and ERA5 is not observed station rainfall.",
		"source": {
			"flood_inventory": "Zenodo IFI-Impacts concept DOI 10.5281/zenodo.4742142; latest record 16994648",
			"weather": "Open-Meteo Historical Weather API, models=era5, daily precipitation_sum (mm)",
			"boundary": "LGD_Districts.parquet matched by exact dist_lgd; CC0 release of Government of India LGD boundaries",
			"districts": [
				{"lgd_code": int(code), "district": name}
				for code, name in sorted({int(row.lgd_code): row.district.split(" (LGD")[0] for row in frame[["lgd_code", "district"]].itertuples(index=False)}.items())
			],
			"era5_cache": "data/real/era5/archive/",
			"reanalysis_not_observed": True,
		},
		"dataset": {
			"path": str(dataset_path),
			"rows": int(len(frame)),
			"positive_count": int(class_counts.get(1, 0)),
			"negative_count": int(class_counts.get(0, 0)),
			"class_counts": {str(k): int(v) for k, v in class_counts.items()},
			"date_range": [frame["date"].min().date().isoformat(), frame["date"].max().date().isoformat()],
			"missing_values": {str(k): int(v) for k, v in frame.isna().sum().items()},
			"negative_sampling": "1:1 target per district-year-monsoon-month stratum; 17 negative rows unavailable in 10 strata because all candidates were event-window excluded",
		},
		"split": {
			"train_years": [2000, 2018],
			"test_years": [2019, 2023],
			"training_rows": int(len(training)),
			"test_rows": int(len(test)),
			"training_class_counts": {str(k): int(v) for k, v in train_counts.items()},
			"test_class_counts": {str(k): int(v) for k, v in test_counts.items()},
			"test_used_for_model_selection": False,
			"cv": f"{n_repeats} repeats of 5-fold expanding-window validation, with whole calendar years as indivisible groups and training strictly earlier than each validation block",
			"threshold_oof": "Forward-chaining year blocks; training years only",
		},
		"model_selection": {
			"candidates": list(cv_metrics),
			"selection_metric": "mean repeated-CV average precision (PR-AUC), then ROC-AUC, then recall",
			"best_model": best_name,
			"randomized_search_iterations_per_base_model": n_iter,
			"best_parameters": {
				name: search.best_params_ for name, search in searches.items()
			},
			"xgboost_early_stopping": "Chronological final 15% of each training fold is used as eval_set; final selected tree count is refit without early stopping on all training years.",
			"class_imbalance": "Logistic Regression and Random Forest use class_weight; XGBoost computes scale_pos_weight per fit partition.",
		},
		"threshold_selection": threshold_metadata,
		"majority_baseline": {
			"class_from_training_only": training_majority,
			"test_metrics": baseline_test_metrics,
			"bootstrap_95_ci": baseline_bootstrap,
		},
		"comparisons": {
			best_name: {
				"test_metrics": model_test_metrics,
				"cv_metrics": cv_metrics[best_name],
				"bootstrap_95_ci": model_bootstrap,
			},
			"MajorityClassBaseline": {
				"test_metrics": baseline_test_metrics,
				"cv_metrics": {},
				"bootstrap_95_ci": baseline_bootstrap,
			},
		},
		"cv_metrics_all_candidates": cv_metrics,
		"feature_importance": feature_importance,
		"limitations": (
			"IFI event start dates are inventory reports, not a complete flood observation calendar; negatives mean no selected IFI event within the event window, not independently verified absence of flooding. "
			"Only five Maharashtra districts and monsoon dates are included. District summaries may merge/misstate historical boundary changes. ERA5 is reanalysis, with an approximate centroid/nearest-grid fallback for Mumbai. "
			"Metrics describe this selected, matched synthetic-free sample and are not a national operational forecast assessment."
		),
	}
	model_output = Path(model_path)
	json_output = Path(json_report_path)
	markdown_output = Path(markdown_report_path)
	model_output.parent.mkdir(parents=True, exist_ok=True)
	json_output.parent.mkdir(parents=True, exist_ok=True)
	joblib.dump(
		{
			"pipeline": final_model,
			"metadata": metadata,
			"metrics": report["comparisons"],
			"threshold_selection": threshold_metadata,
			"data_notice": report["data_notice"],
		},
		model_output,
	)
	json_output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
	markdown_output.write_text(_markdown_report(report), encoding="utf-8")
	logger.info("Saved REAL DATA model to %s and evaluation to %s", model_output, json_output)
	return report