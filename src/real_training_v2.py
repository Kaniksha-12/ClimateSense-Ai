"""Train and evaluate v2 models on real IFI / ERA5 data."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
	accuracy_score,
	average_precision_score,
	balanced_accuracy_score,
	brier_score_loss,
	confusion_matrix,
	f1_score,
	precision_score,
	recall_score,
	roc_auc_score,
)
from sklearn.model_selection import GroupKFold, RandomizedSearchCV, cross_val_predict
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from scripts.build_real_dataset_v2 import IFI_PATH, prepare_event_labels
from src.fetch_features import DISTRICT_NAMES
from src.preprocessing import build_preprocessor

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data/processed/real_flood_dataset_v2.csv"
MODEL_PATH = ROOT / "models/real_flood_v2.pkl"
JSON_REPORT_PATH = ROOT / "reports/real_data_evaluation_v2.json"
MARKDOWN_REPORT_PATH = ROOT / "reports/real_data_evaluation_v2.md"
TRAIN_START_YEAR = 2000
TRAIN_END_YEAR = 2018
TEST_START_YEAR = 2019
TEST_END_YEAR = 2023
TARGET = "flood_risk"
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
SCORING = {"roc_auc": "roc_auc", "pr_auc": "average_precision"}


class EarlyStoppingXGBClassifier(ClassifierMixin, BaseEstimator):
	"""XGBoost wrapper that reserves the chronological tail of each fit for stopping."""

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
			raise ValueError("XGBoost requires both binary classes in each fit.")
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
		self.best_iteration_ = int(getattr(self.model_, "best_iteration", self.n_estimators - 1))
		self.early_stopping_used_ = bool(can_early_stop)
		return self

	def predict_proba(self, X: Any) -> np.ndarray:
		return self.model_.predict_proba(np.asarray(X))

	def predict(self, X: Any) -> np.ndarray:
		return self.model_.predict(np.asarray(X))

	@property
	def feature_importances_(self) -> np.ndarray:
		return self.model_.feature_importances_


def _pipeline(classifier: Any, training_features: pd.DataFrame) -> Pipeline:
	return Pipeline(
		[
			("preprocessor", build_preprocessor(training_features)),
			("classifier", classifier),
		]
	)


def _search_spaces(seed: int = 42) -> dict[str, tuple[Any, dict[str, list[Any]]]]:
	return {
		"LogisticRegression": (
			LogisticRegression(solver="liblinear", max_iter=2000, random_state=seed),
			{
				"classifier__C": [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0],
				"classifier__class_weight": ["balanced"],
				"classifier__tol": [1e-3, 1e-4],
			},
		),
		"RandomForest": (
			RandomForestClassifier(random_state=seed, n_jobs=2, class_weight="balanced"),
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
			EarlyStoppingXGBClassifier(random_state=seed, n_jobs=2),
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


def _assert_no_leakage(frame: pd.DataFrame, training: pd.DataFrame, test: pd.DataFrame) -> dict[str, int]:
	protected = {TARGET, "event_ueis", "date", "year", "lgd_code"}
	if protected.intersection(FEATURE_COLUMNS):
		raise ValueError(f"Protected label, event, or split columns are in features: {sorted(protected.intersection(FEATURE_COLUMNS))}")
	if set(FEATURE_COLUMNS) - set(frame.columns):
		raise ValueError(f"Dataset is missing feature columns: {sorted(set(FEATURE_COLUMNS) - set(frame.columns))}")
	train_rows = set(zip(training["lgd_code"].astype(int), training["date"].dt.strftime("%Y-%m-%d")))
	test_rows = set(zip(test["lgd_code"].astype(int), test["date"].dt.strftime("%Y-%m-%d")))
	train_events = {
		uei
		for value in training["event_ueis"].dropna().astype(str)
		for uei in value.split("|")
		if uei
	}
	test_events = {
		uei
		for value in test["event_ueis"].dropna().astype(str)
		for uei in value.split("|")
		if uei
	}
	row_overlap = train_rows.intersection(test_rows)
	event_overlap = train_events.intersection(test_events)
	if row_overlap or event_overlap:
		raise ValueError(f"Train/test overlap detected: rows={len(row_overlap)}, events={len(event_overlap)}")
	return {"row_overlap": len(row_overlap), "event_overlap": len(event_overlap)}


def _select_threshold(
	labels: np.ndarray,
	probabilities: np.ndarray,
	recall_target: float = 0.8,
	minimum_precision: float = 0.05,
) -> tuple[float, dict[str, Any]]:
	thresholds = np.unique(np.concatenate(([0.0], probabilities, [1.0, np.nextafter(1.0, 2.0)])))
	rows = []
	for threshold in thresholds:
		predictions = (probabilities >= threshold).astype(np.int8)
		precision = float(precision_score(labels, predictions, zero_division=0))
		recall = float(recall_score(labels, predictions, zero_division=0))
		rows.append((float(threshold), precision, recall, float(f1_score(labels, predictions, zero_division=0))))
	feasible = [row for row in rows if row[2] >= recall_target and row[1] >= minimum_precision]
	policy = "recall_target_and_minimum_precision"
	if not feasible:
		feasible = [row for row in rows if row[2] >= recall_target]
		policy = "recall_target_precision_constraint_unmet"
	if not feasible:
		feasible = rows
		policy = "maximum_available_recall"
	selected = max(feasible, key=lambda row: (row[1], row[3], row[2], row[0]))
	return selected[0], {
		"threshold": selected[0],
		"oof_precision": selected[1],
		"oof_recall": selected[2],
		"oof_f1": selected[3],
		"recall_target": recall_target,
		"minimum_precision": minimum_precision,
		"precision_constraint_met": selected[1] >= minimum_precision,
		"selection_policy": policy,
	}


def _metrics(labels: np.ndarray, predictions: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
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


def _bootstrap_test_intervals(
	labels: np.ndarray,
	predictions: np.ndarray,
	probabilities: np.ndarray,
	majority_probabilities: np.ndarray,
	iterations: int = 2000,
	seed: int = 2026,
) -> dict[str, Any]:
	rng = np.random.default_rng(seed)
	roc_scores: list[float] = []
	recall_scores: list[float] = []
	auc_differences: list[float] = []
	for _ in range(iterations):
		indices = rng.integers(0, len(labels), size=len(labels))
		sampled_labels = labels[indices]
		if len(np.unique(sampled_labels)) < 2:
			continue
		model_auc = float(roc_auc_score(sampled_labels, probabilities[indices]))
		baseline_auc = float(roc_auc_score(sampled_labels, majority_probabilities[indices]))
		roc_scores.append(model_auc)
		recall_scores.append(float(recall_score(sampled_labels, predictions[indices], zero_division=0)))
		auc_differences.append(model_auc - baseline_auc)
	interval = lambda values: [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]
	return {
		"method": "paired nonparametric bootstrap of held-out test rows; single-class resamples skipped",
		"requested_iterations": iterations,
		"valid_iterations": len(roc_scores),
		"confidence_level": 0.95,
		"test_roc_auc": interval(roc_scores),
		"test_recall": interval(recall_scores),
		"roc_auc_difference_vs_majority_baseline": interval(auc_differences),
	}


def _calibration_table(labels: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> list[dict[str, Any]]:
	edges = np.linspace(0.0, 1.0, bins + 1)
	indices = np.digitize(probabilities, edges[1:-1], right=True)
	rows = []
	for bin_index in range(bins):
		mask = indices == bin_index
		if not mask.any():
			continue
		rows.append(
			{
				"lower": float(edges[bin_index]),
				"upper": float(edges[bin_index + 1]),
				"count": int(mask.sum()),
				"mean_predicted_probability": float(probabilities[mask].mean()),
				"observed_positive_rate": float(labels[mask].mean()),
			}
		)
	return rows


def _feature_importance(pipeline: Pipeline) -> list[dict[str, Any]]:
	feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
	classifier = pipeline.named_steps["classifier"]
	if hasattr(classifier, "feature_importances_"):
		values = np.asarray(classifier.feature_importances_, dtype=float)
	elif hasattr(classifier, "coef_"):
		values = np.abs(np.asarray(classifier.coef_, dtype=float)).reshape(-1)
	else:
		return []
	if len(feature_names) != len(values):
		return []
	order = np.argsort(values)[::-1][:10]
	return [{"feature": str(feature_names[index]), "importance": float(values[index])} for index in order]


def _freeze_and_refit(pipeline: Pipeline, X: pd.DataFrame, y: np.ndarray) -> Pipeline:
	final_pipeline = clone(pipeline)
	classifier = pipeline.named_steps["classifier"]
	if isinstance(classifier, EarlyStoppingXGBClassifier):
		best_iteration = int(getattr(classifier, "best_iteration_", classifier.n_estimators - 1))
		final_pipeline.set_params(
			classifier__n_estimators=max(1, min(int(classifier.n_estimators), best_iteration + 1)),
			classifier__use_early_stopping=False,
		)
	final_pipeline.fit(X, y)
	return final_pipeline


def _markdown_report(report: dict[str, Any]) -> str:
	model = report["model_selection"]["selected_model"]
	metrics = report["test_results"]["selected_model"]
	baseline = report["test_results"]["majority_class_baseline"]
	logistic = report["test_results"]["logistic_regression_baseline"]
	lines = [
		"# REAL DATA - ERA5 reanalysis rainfall",
		"",
		"> IFI-Impacts event labels with ERA5 reanalysis rainfall; rainfall is not observed station data.",
		"",
		"## Dataset and split",
		"",
		f"- Rows: {report['dataset']['rows']}; positives: {report['dataset']['class_counts']['1']}; negatives: {report['dataset']['class_counts']['0']}; majority accuracy baseline: {report['dataset']['majority_class_baseline_accuracy']:.3f}.",
		f"- Train: 2000–2018 ({report['split']['training_rows']} rows); test: 2019–2023 ({report['split']['test_rows']} rows).",
		f"- Test classes: {report['split']['test_class_counts']}; dropped-event counts: `{json.dumps(report['dataset']['dropped_events'], sort_keys=True)}`.",
		f"- Selected model: {model}; threshold {report['threshold_selection']['threshold']:.6f}, training OOF precision {report['threshold_selection']['oof_precision']:.3f}, recall {report['threshold_selection']['oof_recall']:.3f}.",
		"- Features use rainfall through the day before event start; monthly rainfall means use training years only. Test years were used once after model selection and threshold freezing.",
		"",
		"## Test results",
		"",
		"Confusion matrix order: `[[TN, FP], [FN, TP]]`.",
		"",
		"| Model | Accuracy | Balanced accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Confusion matrix |",
		"|---|---:|---:|---:|---:|---:|---:|---:|---|",
	]
	for name, values in ((model, metrics), ("Logistic Regression", logistic), ("Majority class", baseline)):
		lines.append(
			f"| {name} | {values['accuracy']:.3f} | {values['balanced_accuracy']:.3f} | {values['precision']:.3f} | "
			f"{values['recall']:.3f} | {values['f1']:.3f} | {values['roc_auc']:.3f} | {values['pr_auc']:.3f} | `{values['confusion_matrix']}` |"
		)
	lines.extend(["", "## Training CV and reliability", ""])
	for name, cv in report["cv_metrics"].items():
		lines.append(f"- {name}: ROC-AUC {cv['roc_auc']['mean']:.3f} ± {cv['roc_auc']['std']:.3f}; PR-AUC {cv['pr_auc']['mean']:.3f} ± {cv['pr_auc']['std']:.3f}.")
	lines.append(f"- Test ROC-AUC 95% CI: {report['bootstrap_95_ci']['test_roc_auc']}; recall 95% CI: {report['bootstrap_95_ci']['test_recall']}.")
	lines.append(f"- Test Brier score: {report['reliability']['brier_score']:.5f}.")
	lines.extend(["", "### Calibration", "", "| Probability bin | Rows | Mean predicted | Observed positive rate |", "|---|---:|---:|---:|"])
	for row in report["reliability"]["calibration_table"]:
		lines.append(f"| {row['lower']:.1f}–{row['upper']:.1f} | {row['count']} | {row['mean_predicted_probability']:.3f} | {row['observed_positive_rate']:.3f} |")
	lines.extend(["", "### Per-district recall", "", "| District | Positive test rows | Recall |", "|---|---:|---:|"])
	for row in report["per_district_recall"]:
		lines.append(f"| {row['district']} | {row['positive_support']} | {row['recall']:.3f} |")
	lines.extend(["", "### Top 10 feature importances", ""])
	for row in report["top_10_feature_importances"]:
		lines.append(f"- `{row['feature']}`: {row['importance']:.5f}")
	lines.extend(["", "## Verdict and limitations", "", report["verdict"], "", report["limitations"], ""])
	return "\n".join(lines)


def train_real_model_v2(
	dataset_path: str | Path = DATASET_PATH,
	model_path: str | Path = MODEL_PATH,
	json_report_path: str | Path = JSON_REPORT_PATH,
	markdown_report_path: str | Path = MARKDOWN_REPORT_PATH,
	n_iter: int = 15,
	bootstrap_iterations: int = 2000,
) -> dict[str, Any]:
	"""Tune on training years, freeze/refit, and evaluate the fixed test period once."""
	if n_iter < 1 or bootstrap_iterations < 1:
		raise ValueError("n_iter and bootstrap_iterations must be positive.")
	outputs = [Path(model_path), Path(json_report_path), Path(markdown_report_path)]
	if any(path.exists() for path in outputs):
		raise FileExistsError(f"Refusing to overwrite existing v2 output(s): {[str(path) for path in outputs if path.exists()]}")
	frame = pd.read_csv(dataset_path, parse_dates=["date"])
	ifi_events = pd.read_csv(IFI_PATH, dtype={"District_LGD_Codes": "string"})
	_, _, dropped_events = prepare_event_labels(ifi_events)
	required = {"date", "year", "lgd_code", "district", "event_ueis", TARGET, *FEATURE_COLUMNS}
	if required - set(frame.columns):
		raise ValueError(f"V2 dataset is missing columns: {sorted(required - set(frame.columns))}")
	if set(frame[TARGET].dropna().unique()) != {0, 1}:
		raise ValueError("Target must contain exactly binary classes 0 and 1.")
	if frame[TARGET].isna().any() or frame[FEATURE_COLUMNS].isna().all(axis=None):
		raise ValueError("Target or all feature values are missing.")
	if frame.duplicated(["lgd_code", "date"]).any():
		raise ValueError("V2 data has duplicate LGD district-days.")
	frame = frame.sort_values(["date", "lgd_code"]).reset_index(drop=True)
	training = frame[frame["year"].between(TRAIN_START_YEAR, TRAIN_END_YEAR)].reset_index(drop=True)
	test = frame[frame["year"].between(TEST_START_YEAR, TEST_END_YEAR)].reset_index(drop=True)
	if training.empty or test.empty:
		raise ValueError("The fixed training and test year partitions must be non-empty.")
	for name, partition in (("training", training), ("test", test)):
		if set(partition[TARGET].unique()) != {0, 1}:
			raise ValueError(f"{name} years do not contain both classes; fixed years will not be changed.")
	overlap = _assert_no_leakage(frame, training, test)

	X_train = training[FEATURE_COLUMNS].copy()
	y_train = training[TARGET].to_numpy(dtype=np.int8)
	groups = training["year"].to_numpy(dtype=int)
	n_splits = 5
	if len(np.unique(groups)) < n_splits:
		raise ValueError(f"At least {n_splits} training years are required for GroupKFold.")
	group_kfold = GroupKFold(n_splits=n_splits)
	cv_splits = list(group_kfold.split(X_train, y_train, groups))
	for fold, (_, validation_indices) in enumerate(cv_splits, start=1):
		if len(np.unique(y_train[validation_indices])) != 2:
			raise ValueError(f"GroupKFold year fold {fold} contains one class; cannot calculate ROC-AUC.")

	searches: dict[str, RandomizedSearchCV] = {}
	best_estimators: dict[str, Pipeline] = {}
	cv_metrics: dict[str, dict[str, dict[str, Any]]] = {}
	for name, (classifier, distributions) in _search_spaces().items():
		logger.info("Searching %s with %d randomized trials and 5 GroupKFold year folds", name, n_iter)
		search = RandomizedSearchCV(
			estimator=_pipeline(classifier, X_train),
			param_distributions=distributions,
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
		index = int(search.best_index_)
		cv_metrics[name] = {
			metric: {
				"mean": float(search.cv_results_[f"mean_test_{metric}"][index]),
				"std": float(search.cv_results_[f"std_test_{metric}"][index]),
				"fold_scores": [float(search.cv_results_[f"split{fold}_test_{metric}"][index]) for fold in range(n_splits)],
			}
			for metric in SCORING
		}
		logger.info("%s best CV PR-AUC %.4f", name, cv_metrics[name]["pr_auc"]["mean"])

	selected_name = max(
		searches,
		key=lambda name: (cv_metrics[name]["pr_auc"]["mean"], cv_metrics[name]["roc_auc"]["mean"]),
	)
	selected_search = searches[selected_name]
	selected_estimator = selected_search.best_estimator_
	oof_probabilities = cross_val_predict(
		clone(selected_estimator),
		X_train,
		y_train,
		cv=cv_splits,
		method="predict_proba",
		n_jobs=1,
	)[:, 1]
	training_prevalence = float(y_train.mean())
	minimum_precision = max(0.05, 2.0 * training_prevalence)
	threshold, threshold_metadata = _select_threshold(
		y_train,
		oof_probabilities,
		recall_target=0.8,
		minimum_precision=minimum_precision,
	)
	threshold_metadata["oof_rows"] = int(len(oof_probabilities))
	threshold_metadata["oof_method"] = "five-fold GroupKFold by calendar year, training years only"
	threshold_metadata["training_prevalence"] = training_prevalence

	final_model = _freeze_and_refit(selected_estimator, X_train, y_train)
	logistic_model = _freeze_and_refit(best_estimators["LogisticRegression"], X_train, y_train)
	X_test = test[FEATURE_COLUMNS].copy()
	y_test = test[TARGET].to_numpy(dtype=np.int8)
	model_probabilities = final_model.predict_proba(X_test)[:, 1]
	model_predictions = (model_probabilities >= threshold).astype(np.int8)
	logistic_probabilities = logistic_model.predict_proba(X_test)[:, 1]
	logistic_predictions = (logistic_probabilities >= 0.5).astype(np.int8)
	majority_label = int(pd.Series(y_train).value_counts().idxmax())
	majority_predictions = np.full(len(y_test), majority_label, dtype=np.int8)
	majority_probabilities = np.full(len(y_test), training_prevalence, dtype=float)
	test_results = {
		"selected_model": _metrics(y_test, model_predictions, model_probabilities),
		"logistic_regression_baseline": _metrics(y_test, logistic_predictions, logistic_probabilities),
		"majority_class_baseline": _metrics(y_test, majority_predictions, majority_probabilities),
	}
	bootstrap = _bootstrap_test_intervals(
		y_test,
		model_predictions,
		model_probabilities,
		majority_probabilities,
		iterations=bootstrap_iterations,
	)
	reliability = {
		"brier_score": float(brier_score_loss(y_test, model_probabilities)),
		"calibration_table": _calibration_table(y_test, model_probabilities),
	}
	district_recalls = []
	for code in sorted(test["lgd_code"].astype(int).unique()):
		mask = test["lgd_code"].astype(int).to_numpy() == code
		district_recalls.append(
			{
				"lgd_code": code,
				"district": DISTRICT_NAMES[code],
				"positive_support": int(y_test[mask].sum()),
				"recall": float(recall_score(y_test[mask], model_predictions[mask], zero_division=0)),
			}
		)
	feature_importance = _feature_importance(final_model)
	auc_difference_ci = bootstrap["roc_auc_difference_vs_majority_baseline"]
	if auc_difference_ci[0] > 0:
		verdict = "The model's test ROC-AUC exceeds the majority baseline (0.5), with the paired 95% bootstrap interval for the AUC difference entirely above zero."
	else:
		verdict = "The model does not establish a test ROC-AUC improvement over the majority baseline: the paired 95% bootstrap interval for the AUC difference includes zero."
	precision = test_results["selected_model"]["precision"]
	if precision < 0.1:
		weakness = "The main weakness is low positive precision, so reaching the recall target produces many false alerts under the highly imbalanced all-negative-day sampling frame."
	else:
		weakness = "The main weakness is the limited, event-inventory-based sample: missing IFI events can be mislabeled as non-events, and performance is restricted to five districts."
	metadata = {
		"label": "REAL DATA - ERA5 reanalysis rainfall",
		"dataset_path": str(dataset_path),
		"training_rows": int(len(training)),
		"test_rows": int(len(test)),
		"feature_columns": FEATURE_COLUMNS,
		"transformed_feature_columns": [str(value) for value in final_model.named_steps["preprocessor"].get_feature_names_out()],
		"target": TARGET,
		"decision_threshold": float(threshold),
		"train_years": [TRAIN_START_YEAR, TRAIN_END_YEAR],
		"test_years": [TEST_START_YEAR, TEST_END_YEAR],
		"selected_model": selected_name,
		"randomized_search_iterations_per_model": n_iter,
		"cv": "GroupKFold(n_splits=5), grouped by calendar year; training years only",
		"train_test_overlap": overlap,
		"class_weights": "balanced Logistic Regression and Random Forest; scale_pos_weight for XGBoost",
	}
	report = {
		"label": "REAL DATA - ERA5 reanalysis rainfall",
		"data_notice": "IFI-Impacts binary event labels with ERA5 reanalysis rainfall; rainfall is reanalysis, not observed station data.",
		"dataset": {
			"path": str(dataset_path),
			"rows": int(len(frame)),
			"class_counts": {str(k): int(v) for k, v in frame[TARGET].value_counts().sort_index().items()},
			"class_balance": {str(k): float(v / len(frame)) for k, v in frame[TARGET].value_counts().sort_index().items()},
			"majority_class": majority_label,
			"majority_class_baseline_accuracy": float(accuracy_score(y_test, majority_predictions)),
			"rainfall_source": "data/real/era5/three_point/district_daily_rainfall.csv",
			"districts": [{"lgd_code": code, "district": DISTRICT_NAMES[code]} for code in sorted(DISTRICT_NAMES)],
			"dropped_events": dropped_events,
		},
		"split": {
			"train_years": [TRAIN_START_YEAR, TRAIN_END_YEAR],
			"test_years": [TEST_START_YEAR, TEST_END_YEAR],
			"training_rows": int(len(training)),
			"test_rows": int(len(test)),
			"training_class_counts": {str(k): int(v) for k, v in training[TARGET].value_counts().sort_index().items()},
			"test_class_counts": {str(k): int(v) for k, v in test[TARGET].value_counts().sort_index().items()},
			"row_overlap": overlap["row_overlap"],
			"event_overlap": overlap["event_overlap"],
			"test_used_for_tuning_or_threshold": False,
		},
		"feature_columns": FEATURE_COLUMNS,
		"features_are_one_hot_district": True,
		"target_in_features": False,
		"model_selection": {
			"selected_model": selected_name,
			"candidates": list(searches),
			"selection_metric": "GroupKFold mean PR-AUC, with ROC-AUC as tie-breaker",
			"randomized_search_iterations_per_model": n_iter,
			"best_parameters": {name: search.best_params_ for name, search in searches.items()},
			"xgboost_early_stopping": "Each fold's chronological final 15% is the early-stopping evaluation tail; selected tree count is frozen before full training-year refit.",
			"class_imbalance": metadata["class_weights"],
		},
		"cv_metrics": cv_metrics,
		"threshold_selection": threshold_metadata,
		"test_results": test_results,
		"majority_baseline": {
			"class_from_training_only": majority_label,
			"metrics": test_results["majority_class_baseline"],
		},
		"bootstrap_95_ci": bootstrap,
		"reliability": reliability,
		"per_district_recall": district_recalls,
		"top_10_feature_importances": feature_importance,
		"verdict": f"{verdict} {weakness}",
		"limitations": "IFI-Impacts records are not a complete flood-observation calendar; eligible non-event days can include unreported floods. ERA5 is reanalysis, not observed station rainfall. Results cover five Maharashtra districts and June-September only; they are not a national operational flood forecast.",
		"bundle_metadata": metadata,
	}
	for path in outputs:
		path.parent.mkdir(parents=True, exist_ok=True)
	joblib.dump({"pipeline": final_model, "metadata": metadata, "threshold_selection": threshold_metadata}, outputs[0])
	outputs[1].write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
	outputs[2].write_text(_markdown_report(report), encoding="utf-8")
	print(json.dumps({"selected_model": selected_name, "threshold": threshold, "test_results": test_results, "bootstrap_95_ci": bootstrap, "outputs": [str(path) for path in outputs]}, indent=2, default=str))
	return report


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--data", default=str(DATASET_PATH))
	parser.add_argument("--model", default=str(MODEL_PATH))
	parser.add_argument("--json-report", default=str(JSON_REPORT_PATH))
	parser.add_argument("--markdown-report", default=str(MARKDOWN_REPORT_PATH))
	parser.add_argument("--n-iter", type=int, default=15)
	parser.add_argument("--bootstrap-iterations", type=int, default=2000)
	args = parser.parse_args()
	logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
	try:
		train_real_model_v2(
			args.data,
			args.model,
			args.json_report,
			args.markdown_report,
			n_iter=args.n_iter,
			bootstrap_iterations=args.bootstrap_iterations,
		)
	except (FileNotFoundError, FileExistsError, ValueError) as exc:
		parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
	main()