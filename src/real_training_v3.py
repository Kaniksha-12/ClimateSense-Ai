"""Train v3 IFI-association models using training years only for all choices."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import (
	accuracy_score,
	average_precision_score,
	balanced_accuracy_score,
	brier_score_loss,
	confusion_matrix,
	fbeta_score,
	precision_score,
	recall_score,
	roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, cross_val_score

from scripts.build_real_dataset_v2 import IFI_PATH, prepare_event_labels
from src.fetch_features import DISTRICT_NAMES
from src.label_contract import (
	IFI_NEXT_0_TO_2_DAYS_SPEC_ID,
	IFI_SAME_DAY_SPEC_ID,
	validate_ifi_association_rows,
)
from src.real_training_v2 import EarlyStoppingXGBClassifier, _pipeline, _search_spaces
from src.preprocessing import build_preprocessor
from src.temporal_features import (
	forward_chaining_oof_probabilities,
	forward_chaining_year_splits,
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data/processed/real_flood_dataset_v3.csv"
MODEL_PATH = ROOT / "models/real_flood_v3.pkl"
JSON_REPORT_PATH = ROOT / "reports/real_data_evaluation_v3.json"
MARKDOWN_REPORT_PATH = ROOT / "reports/real_data_evaluation_v3.md"
V2_REPORT_PATH = ROOT / "reports/real_data_evaluation_v2.json"
TRAIN_START_YEAR = 2000
CV_END_YEAR = 2014
VALIDATION_START_YEAR = 2015
TRAIN_END_YEAR = 2018
TEST_START_YEAR = 2019
TEST_END_YEAR = 2023
LABELS = {
	"same_day": "same_day_label_value",
	"next_0_to_2_days": "next_0_to_2_days_label_value",
}
LABEL_SPECIFICATIONS = {
	"same_day": IFI_SAME_DAY_SPEC_ID,
	"next_0_to_2_days": IFI_NEXT_0_TO_2_DAYS_SPEC_ID,
}
CORE_FEATURE_COLUMNS = [
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
EXTENDED_FEATURE_COLUMNS = CORE_FEATURE_COLUMNS[:-2] + [
	"rainfall_60d_total_mm",
	"rainfall_90d_total_mm",
	"rainfall_3d_to_30d_intensity_ratio",
] + CORE_FEATURE_COLUMNS[-2:]
FEATURE_SETS = {"core": CORE_FEATURE_COLUMNS, "extended": EXTENDED_FEATURE_COLUMNS}
MINIMUM_PRECISION = 0.10
FIXED_BANDS = {"Low": [0.0, 0.10], "Medium": [0.10, 0.30], "High": [0.30, 1.0000000001]}


def _validate_frame(frame: pd.DataFrame) -> None:
	protected = {
		"flood_risk",
		"same_day_flood_risk",
		*LABELS.values(),
		"event_ueis",
		"date",
		"year",
		"lgd_code",
	}
	if protected.intersection(CORE_FEATURE_COLUMNS + EXTENDED_FEATURE_COLUMNS):
		raise ValueError("Label, event identifiers, or split columns entered the v3 feature lists.")
	if frame.duplicated(["lgd_code", "date"]).any():
		raise ValueError("V3 data contains duplicate LGD district-days.")
	if set(frame["lgd_code"].astype(int)) != set(DISTRICT_NAMES):
		raise ValueError("V3 data must contain exactly the five selected LGD district codes.")
	if frame["date"].dt.year.ne(frame["year"]).any():
		raise ValueError("V3 year field does not match observation dates.")
	train = frame[frame["year"].between(TRAIN_START_YEAR, TRAIN_END_YEAR)]
	test = frame[frame["year"].between(TEST_START_YEAR, TEST_END_YEAR)]
	train_rows = set(zip(train["lgd_code"].astype(int), train["date"].dt.strftime("%Y-%m-%d")))
	test_rows = set(zip(test["lgd_code"].astype(int), test["date"].dt.strftime("%Y-%m-%d")))
	train_events = {uei for value in train["event_ueis"].dropna().astype(str) for uei in value.split("|") if uei}
	test_events = {uei for value in test["event_ueis"].dropna().astype(str) for uei in value.split("|") if uei}
	if train_rows.intersection(test_rows) or train_events.intersection(test_events):
		raise ValueError("Train/test district-day or event overlap detected.")
	for label in LABELS.values():
		if set(frame[label].dropna().unique()) - {0, 1}:
			raise ValueError(f"Label {label} is not binary.")


def _f2(labels: np.ndarray, predictions: np.ndarray) -> float:
	return float(fbeta_score(labels, predictions, beta=2, zero_division=0))


def _threshold_metrics(
	labels: np.ndarray,
	probabilities: np.ndarray,
	thresholds: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
	order = np.argsort(probabilities)
	sorted_probabilities = probabilities[order]
	sorted_labels = labels[order]
	positive_prefix = np.concatenate(([0], np.cumsum(sorted_labels, dtype=np.int64)))
	first_predicted = np.searchsorted(sorted_probabilities, thresholds, side="left")
	true_positives = int(labels.sum()) - positive_prefix[first_predicted]
	predicted_counts = len(labels) - first_predicted
	precision = np.divide(
		true_positives,
		predicted_counts,
		out=np.zeros(len(thresholds), dtype=float),
		where=predicted_counts > 0,
	)
	recall = np.divide(
		true_positives,
		int(labels.sum()),
		out=np.zeros(len(thresholds), dtype=float),
		where=int(labels.sum()) > 0,
	)
	f2 = np.divide(
		5.0 * precision * recall,
		4.0 * precision + recall,
		out=np.zeros(len(thresholds), dtype=float),
		where=(4.0 * precision + recall) > 0,
	)
	return precision, recall, f2


def _metrics(labels: np.ndarray, predictions: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
	return {
		"accuracy": float(accuracy_score(labels, predictions)),
		"balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
		"precision": float(precision_score(labels, predictions, zero_division=0)),
		"recall": float(recall_score(labels, predictions, zero_division=0)),
		"f1": float(fbeta_score(labels, predictions, beta=1, zero_division=0)),
		"f2": _f2(labels, predictions),
		"roc_auc": float(roc_auc_score(labels, probabilities)),
		"pr_auc": float(average_precision_score(labels, probabilities)),
		"brier_score": float(brier_score_loss(labels, probabilities)),
		"confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
	}


def _threshold_candidates(oof_probabilities: np.ndarray) -> np.ndarray:
	return np.unique(
		np.concatenate(
			(
				[0.0],
				oof_probabilities,
				[np.nextafter(float(np.max(oof_probabilities)), 2.0)],
			)
		)
	)


def _oof_threshold_summary(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
	thresholds = _threshold_candidates(probabilities)
	precisions, recalls, f2_scores = _threshold_metrics(labels, probabilities, thresholds)
	feasible = np.flatnonzero(precisions >= MINIMUM_PRECISION)
	if not len(feasible):
		return {"precision_constraint_met": False, "best_f2": None}
	best = max(
		feasible,
		key=lambda index: (f2_scores[index], precisions[index], recalls[index], thresholds[index]),
	)
	return {
		"threshold": float(thresholds[best]),
		"precision": float(precisions[best]),
		"recall": float(recalls[best]),
		"f2": float(f2_scores[best]),
		"precision_constraint_met": True,
	}


def _select_validation_threshold(
	labels: np.ndarray,
	probabilities: np.ndarray,
	oof_probabilities: np.ndarray,
) -> tuple[float, dict[str, Any]]:
	thresholds = _threshold_candidates(oof_probabilities)
	precisions, recalls, f2_scores = _threshold_metrics(labels, probabilities, thresholds)
	feasible = np.flatnonzero(precisions >= MINIMUM_PRECISION)
	if not len(feasible):
		raise ValueError("No OOF-derived threshold achieves validation precision >= 0.10; refusing to score the test period.")
	best = max(
		feasible,
		key=lambda index: (f2_scores[index], precisions[index], recalls[index], thresholds[index]),
	)
	return float(thresholds[best]), {
		"threshold": float(thresholds[best]),
		"precision": float(precisions[best]),
		"recall": float(recalls[best]),
		"f2": float(f2_scores[best]),
		"precision_constraint_met": True,
		"minimum_precision": MINIMUM_PRECISION,
		"threshold_candidates_from_oof": True,
		"selection_data": (
			"2015-2018 held-out validation block; threshold candidates derived from "
			"forward-chaining OOF probabilities for 2000-2014, excluding warm-up years"
		),
	}


def _freeze_classifier(classifier: Any) -> Any:
	frozen = clone(classifier)
	if isinstance(classifier, EarlyStoppingXGBClassifier):
		best_iteration = int(getattr(classifier, "best_iteration_", classifier.n_estimators - 1))
		frozen.set_params(
			n_estimators=max(1, min(int(classifier.n_estimators), best_iteration + 1)),
			use_early_stopping=False,
		)
	elif isinstance(classifier, VotingClassifier):
		fitted_estimators = getattr(classifier, "named_estimators_", {})
		frozen.set_params(
			estimators=[
				(name, _freeze_classifier(fitted_estimators.get(name, estimator)))
				for name, estimator in classifier.estimators
			]
		)
	return frozen


def _final_refit(pipeline: Any, features: pd.DataFrame, labels: np.ndarray) -> Any:
	refit = clone(pipeline)
	refit.set_params(classifier=_freeze_classifier(pipeline.named_steps["classifier"]))
	refit.fit(features, labels)
	return refit


def _feature_importances(pipeline: Any) -> list[dict[str, Any]]:
	names = pipeline.named_steps["preprocessor"].get_feature_names_out()
	classifier = pipeline.named_steps["classifier"]
	if isinstance(classifier, VotingClassifier):
		vectors = []
		for estimator in classifier.named_estimators_.values():
			if hasattr(estimator, "feature_importances_"):
				values = np.asarray(estimator.feature_importances_, dtype=float)
			elif hasattr(estimator, "coef_"):
				values = np.abs(np.asarray(estimator.coef_, dtype=float)).reshape(-1)
			else:
				continue
			normalized = values / values.sum() if values.sum() else values
			vectors.append(normalized)
		if not vectors:
			return []
		importance = np.mean(vectors, axis=0)
	elif hasattr(classifier, "feature_importances_"):
		importance = np.asarray(classifier.feature_importances_, dtype=float)
	elif hasattr(classifier, "coef_"):
		importance = np.abs(np.asarray(classifier.coef_, dtype=float)).reshape(-1)
	else:
		return []
	if len(names) != len(importance):
		return []
	order = np.argsort(importance)[::-1][:10]
	return [{"feature": str(names[index]), "importance": float(importance[index])} for index in order]


def _bootstrap(
	labels: np.ndarray,
	predictions: np.ndarray,
	probabilities: np.ndarray,
	baseline_predictions: np.ndarray,
	baseline_probabilities: np.ndarray,
	iterations: int = 2000,
	seed: int = 3030,
) -> dict[str, Any]:
	metric_names = ("accuracy", "balanced_accuracy", "precision", "recall", "f1", "f2", "roc_auc", "pr_auc", "brier_score")
	samples: dict[str, list[float]] = {name: [] for name in metric_names}
	baseline_samples: dict[str, list[float]] = {name: [] for name in metric_names}
	differences: dict[str, list[float]] = {name: [] for name in metric_names}
	rng = np.random.default_rng(seed)
	for _ in range(iterations):
		indices = rng.integers(0, len(labels), size=len(labels))
		sampled = labels[indices]
		if len(np.unique(sampled)) != 2:
			continue
		model_metrics = _metrics(sampled, predictions[indices], probabilities[indices])
		baseline_metrics = _metrics(sampled, baseline_predictions[indices], baseline_probabilities[indices])
		for name in metric_names:
			samples[name].append(model_metrics[name])
			baseline_samples[name].append(baseline_metrics[name])
			differences[name].append(model_metrics[name] - baseline_metrics[name])
	interval = lambda values: [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]
	return {
		"method": "Paired bootstrap of held-out 2019-2023 rows; single-class resamples skipped.",
		"iterations_requested": iterations,
		"iterations_valid": len(samples["accuracy"]),
		"confidence_level": 0.95,
		"selected_model": {name: interval(values) for name, values in samples.items()},
		"majority_baseline": {name: interval(values) for name, values in baseline_samples.items()},
		"paired_difference_vs_majority": {name: interval(values) for name, values in differences.items()},
	}


def _probability_bands(labels: np.ndarray, probabilities: np.ndarray) -> list[dict[str, Any]]:
	rows = []
	for name, (lower, upper) in FIXED_BANDS.items():
		mask = (probabilities >= lower) & (probabilities < upper)
		rows.append(
			{
				"band": name,
				"lower_probability": lower,
				"upper_probability_exclusive": upper,
				"rows": int(mask.sum()),
				"ifi_association_positives": int(labels[mask].sum()),
				"association_positive_rate": float(labels[mask].mean()) if mask.any() else None,
			}
		)
	return rows


def _train_configuration(
	core: pd.DataFrame,
	validation: pd.DataFrame,
	label_name: str,
	feature_name: str,
	n_iter: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
	label_column = LABELS[label_name]
	features = FEATURE_SETS[feature_name]
	core_eligibility = f"__{label_name}_training_eligible"
	validation_eligibility = f"__{label_name}_evaluation_eligible"
	core = core[core[label_column].notna() & core[core_eligibility]].sort_values(["date", "lgd_code"]).reset_index(drop=True)
	validation = validation[
		validation[label_column].notna() & validation[validation_eligibility]
	].sort_values(["date", "lgd_code"]).reset_index(drop=True)
	X_core = core[features].copy()
	y_core = core[label_column].to_numpy(dtype=np.int8)
	X_validation = validation[features].copy()
	y_validation = validation[label_column].to_numpy(dtype=np.int8)
	if set(np.unique(y_core)) != {0, 1} or set(np.unique(y_validation)) != {0, 1}:
		raise ValueError(f"Both classes are required in core and validation for {label_name}/{feature_name}.")
	groups = core["year"].to_numpy(dtype=int)
	splits = forward_chaining_year_splits(
		groups,
		y_core,
		n_splits=5,
		min_train_years=4,
	)
	searches = {}
	candidates: list[dict[str, Any]] = []
	for model_name, (classifier, distributions) in _search_spaces().items():
		logger.info(
			"%s/%s: %s search, %d trials, forward-chaining year folds",
			label_name,
			feature_name,
			model_name,
			n_iter,
		)
		search = RandomizedSearchCV(
			estimator=_pipeline(classifier, X_core),
			param_distributions=distributions,
			n_iter=n_iter,
			scoring="average_precision",
			refit=True,
			cv=splits,
			random_state=42,
			n_jobs=1,
			return_train_score=False,
			error_score="raise",
		)
		search.fit(X_core, y_core)
		searches[model_name] = search
		oof_labels, oof = forward_chaining_oof_probabilities(
			search.best_estimator_,
			X_core,
			y_core,
			splits,
		)
		validation_probabilities = search.best_estimator_.predict_proba(X_validation)[:, 1]
		candidates.append(
			{
				"label_name": label_name,
				"feature_name": feature_name,
				"model_name": model_name,
				"estimator": search.best_estimator_,
				"search": search,
				"cv_mean_pr_auc": float(search.best_score_),
				"cv_std_pr_auc": float(search.cv_results_["std_test_score"][search.best_index_]),
				"oof_probabilities": oof,
				"oof_threshold": _oof_threshold_summary(oof_labels, oof),
				"validation_probabilities": validation_probabilities,
				"y_core": y_core,
				"y_validation": y_validation,
				"validation": validation,
				"feature_columns": features,
				"best_parameters": search.best_params_,
			}
		)

	best_single_cv = max(candidate["cv_mean_pr_auc"] for candidate in candidates)
	voting = VotingClassifier(
		estimators=[(name.lower(), search.best_estimator_.named_steps["classifier"]) for name, search in searches.items()],
		voting="soft",
		n_jobs=1,
	)
	voting_pipeline = _pipeline(voting, X_core)
	voting_scores = cross_val_score(voting_pipeline, X_core, y_core, cv=splits, scoring="average_precision", n_jobs=1)
	voting_mean = float(np.mean(voting_scores))
	voting_oof_labels, voting_oof = forward_chaining_oof_probabilities(
		voting_pipeline,
		X_core,
		y_core,
		splits,
	)
	voting_pipeline.fit(X_core, y_core)
	candidates.append(
		{
			"label_name": label_name,
			"feature_name": feature_name,
			"model_name": "SoftVotingEnsemble",
			"estimator": voting_pipeline,
			"search": None,
			"cv_mean_pr_auc": voting_mean,
			"cv_std_pr_auc": float(np.std(voting_scores, ddof=1)),
			"oof_probabilities": voting_oof,
			"oof_threshold": _oof_threshold_summary(voting_oof_labels, voting_oof),
			"validation_probabilities": voting_pipeline.predict_proba(X_validation)[:, 1],
			"y_core": y_core,
			"y_validation": y_validation,
			"validation": validation,
			"feature_columns": features,
			"best_parameters": {name: search.best_params_ for name, search in searches.items()},
		}
	)
	return candidates, {"cv_splits": splits, "searches": searches, "voting_cv_scores": [float(value) for value in voting_scores]}


def _evaluate_validation_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
	threshold, threshold_info = _select_validation_threshold(
		candidate["y_validation"],
		candidate["validation_probabilities"],
		candidate["oof_probabilities"],
	)
	predictions = (candidate["validation_probabilities"] >= threshold).astype(np.int8)
	return {
		"label_name": candidate["label_name"],
		"feature_name": candidate["feature_name"],
		"model_name": candidate["model_name"],
		"cv_mean_pr_auc": candidate["cv_mean_pr_auc"],
		"cv_std_pr_auc": candidate["cv_std_pr_auc"],
		"validation_pr_auc": float(average_precision_score(candidate["y_validation"], candidate["validation_probabilities"])),
		"validation_roc_auc": float(roc_auc_score(candidate["y_validation"], candidate["validation_probabilities"])),
		"validation_metrics": _metrics(candidate["y_validation"], predictions, candidate["validation_probabilities"]),
		"threshold_selection": threshold_info,
		"oof_threshold_summary": candidate["oof_threshold"],
		"threshold": threshold,
		"feature_columns": candidate["feature_columns"],
		"candidate": candidate,
	}


def _markdown_report(report: dict[str, Any]) -> str:
	selected = report["selection"]
	metrics = report["test_results"]["selected_model"]
	lines = [
		"# REAL DATA - ERA5 reanalysis rainfall",
		"",
		"> IFI event-association targets only. A negative is a no-match in the declared inventory snapshot, not evidence of no flooding.",
		"> Second look at the 2019–2023 test years: these years were already scored for v2. This is not a fresh independent test set.",
		"",
		"## Data and decisions",
		"",
		f"- Dataset rows: {report['dataset']['rows']}; next-0-to-2-day label counts: {report['label_balance']['next_0_to_2_days']['all_rows']}; same-day eligible counts: {report['label_balance']['same_day']['all_rows']}.",
		f"- Training core: 2000–2014 forward-chaining year folds; final validation: 2015–2018; final refit: 2000–2018; second-look test: 2019–2023.",
		f"- Selected label: {selected['label_name']}; feature set: {selected['feature_name']}; model: {selected['model_name']}; threshold: {selected['threshold']:.6f}.",
		f"- Validation threshold precision/recall/F2: {selected['threshold_selection']['precision']:.3f}/{selected['threshold_selection']['recall']:.3f}/{selected['threshold_selection']['f2']:.3f}; precision constraint met: {selected['threshold_selection']['precision_constraint_met']}.",
		"- Test was scored once after all choices were frozen. Model probabilities are grouped as Low < 0.10, Medium 0.10–<0.30, High ≥ 0.30.",
		"",
		"## Test performance",
		"",
		"Confusion matrices use `[[TN, FP], [FN, TP]]`.",
		"",
		"| Model | Accuracy | Balanced accuracy | Precision | Recall | F1 | F2 | ROC-AUC | PR-AUC | Brier | Confusion matrix |",
		"|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
	]
	for name, row in report["test_results"].items():
		lines.append(
			f"| {name} | {row['accuracy']:.3f} | {row['balanced_accuracy']:.3f} | {row['precision']:.3f} | {row['recall']:.3f} | "
			f"{row['f1']:.3f} | {row['f2']:.3f} | {row['roc_auc']:.3f} | {row['pr_auc']:.3f} | {row['brier_score']:.4f} | `{row['confusion_matrix']}` |"
		)
	lines.extend(["", "## Probability bands", "", "| Band | Probability range | Rows | IFI association positives | Positive rate |", "|---|---:|---:|---:|---:|"])
	for row in report["probability_bands"]:
		rate = "n/a" if row["association_positive_rate"] is None else f"{row['association_positive_rate']:.3f}"
		lines.append(f"| {row['band']} | {row['lower_probability']:.2f}–<{row['upper_probability_exclusive']:.2f} | {row['rows']} | {row['ifi_association_positives']} | {rate} |")
	lines.extend(["", "## Validation and label comparison", "", "| Label | Features | Model | CV PR-AUC | Validation PR-AUC | Validation F2 | Validation precision | Threshold |", "|---|---|---|---:|---:|---:|---:|---:|"])
	for row in report["candidate_validation_results"]:
		lines.append(f"| {row['label_name']} | {row['feature_name']} | {row['model_name']} | {row['cv_mean_pr_auc']:.3f} ± {row['cv_std_pr_auc']:.3f} | {row['validation_pr_auc']:.3f} | {row['validation_metrics']['f2']:.3f} | {row['validation_metrics']['precision']:.3f} | {row['threshold']:.4f} |")
	lines.extend(["", "## Bootstrap and per-district recall", ""])
	lines.append(f"- Bootstrap 95% CI: {json.dumps(report['bootstrap_95_ci']['selected_model'], sort_keys=True)}")
	lines.append(f"- Paired difference vs majority: {json.dumps(report['bootstrap_95_ci']['paired_difference_vs_majority'], sort_keys=True)}")
	lines.extend(["", "| District | Positive test rows | Recall |", "|---|---:|---:|"])
	for row in report["per_district_recall"]:
		lines.append(f"| {row['district']} | {row['positive_support']} | {row['recall']:.3f} |")
	lines.extend(["", "## Top 10 feature importances", ""])
	for row in report["top_10_feature_importances"]:
		lines.append(f"- `{row['feature']}`: {row['importance']:.5f}")
	lines.extend([
		"",
		"## V2 comparison and limitations",
		"",
		"The v2 and v3 results use the same previously scored 2019–2023 years; v3 is a second look, not a fresh test.",
		"Confusion matrices use `[[TN, FP], [FN, TP]]`.",
		"",
		"| Version | Label | Accuracy | Balanced accuracy | Precision | Recall | F1 | F2 | ROC-AUC | PR-AUC | Brier | Confusion matrix |",
		"|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
	])
	for row in report["v2_vs_v3"]:
		metrics = row["metrics"]
		lines.append(
			f"| {row['version']} | {row['label']} | {metrics['accuracy']:.3f} | {metrics['balanced_accuracy']:.3f} | "
			f"{metrics['precision']:.3f} | {metrics['recall']:.3f} | {metrics['f1']:.3f} | {metrics['f2']:.3f} | "
			f"{metrics['roc_auc']:.3f} | {metrics['pr_auc']:.3f} | {metrics['brier_score']:.4f} | `{metrics['confusion_matrix']}` |"
		)
	lines.extend([
		"",
		"### Majority baselines",
		"",
		"| Version | Accuracy | Balanced accuracy | Precision | Recall | F1 | F2 | ROC-AUC | PR-AUC | Brier | Confusion matrix |",
		"|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
	])
	for row in report["v2_vs_v3"]:
		metrics = row["majority_baseline"]
		lines.append(
			f"| {row['version']} | {metrics['accuracy']:.3f} | {metrics['balanced_accuracy']:.3f} | "
			f"{metrics['precision']:.3f} | {metrics['recall']:.3f} | {metrics['f1']:.3f} | {metrics['f2']:.3f} | "
			f"{metrics['roc_auc']:.3f} | {metrics['pr_auc']:.3f} | {metrics['brier_score']:.4f} | `{metrics['confusion_matrix']}` |"
		)
	lines.extend([
		"",
		"### Bootstrap 95% confidence intervals",
		"",
		"V2 intervals are limited to the metrics retained by its original report; v3 intervals are paired row-bootstrap intervals.",
		"",
		"| Metric | V2 | V3 |",
		"|---|---:|---:|",
	])
	v2_ci = report["v2_vs_v3"][0]["bootstrap_95_ci"]
	v3_ci = report["v2_vs_v3"][1]["bootstrap_95_ci"]["selected_model"]
	for metric, v2_key, v3_key in (
		("Accuracy", "test_accuracy", "accuracy"),
		("Balanced accuracy", "test_balanced_accuracy", "balanced_accuracy"),
		("Precision", "test_precision", "precision"),
		("Recall", "test_recall", "recall"),
		("F1", "test_f1", "f1"),
		("F2", "test_f2", "f2"),
		("ROC-AUC", "test_roc_auc", "roc_auc"),
		("PR-AUC", "test_pr_auc", "pr_auc"),
		("Brier", "test_brier_score", "brier_score"),
	):
		v2_interval = v2_ci.get(v2_key)
		v2_text = "not retained" if v2_interval is None else f"[{v2_interval[0]:.3f}, {v2_interval[1]:.3f}]"
		interval = v3_ci[v3_key]
		lines.append(f"| {metric} | {v2_text} | [{interval[0]:.3f}, {interval[1]:.3f}] |")
	lines.extend([
		"",
		"### Per-district recall",
		"",
		"| District | V2 positives | V2 recall | V3 positives | V3 recall |",
		"|---|---:|---:|---:|---:|",
	])
	v2_districts = {str(row["lgd_code"]): row for row in report["v2_vs_v3"][0]["per_district_recall"]}
	v3_districts = {str(row["lgd_code"]): row for row in report["v2_vs_v3"][1]["per_district_recall"]}
	for code in sorted(set(v2_districts) | set(v3_districts)):
		v2_row = v2_districts.get(code)
		v3_row = v3_districts.get(code)
		name = (v3_row or v2_row)["district"]
		v2_support = "n/a" if v2_row is None else str(v2_row["positive_support"])
		v2_recall = "n/a" if v2_row is None else f"{v2_row['recall']:.3f}"
		v3_support = "n/a" if v3_row is None else str(v3_row["positive_support"])
		v3_recall = "n/a" if v3_row is None else f"{v3_row['recall']:.3f}"
		lines.append(f"| {name} | {v2_support} | {v2_recall} | {v3_support} | {v3_recall} |")
	lines.extend(["", "## Verdict", "", report["verdict"], "", report["limitations"], ""])
	return "\n".join(lines)


def train_real_model_v3(
	dataset_path: str | Path = DATASET_PATH,
	model_path: str | Path = MODEL_PATH,
	json_report_path: str | Path = JSON_REPORT_PATH,
	markdown_report_path: str | Path = MARKDOWN_REPORT_PATH,
	n_iter: int = 20,
	bootstrap_iterations: int = 2000,
) -> dict[str, Any]:
	if n_iter != 20:
		raise ValueError("V3 requires exactly 20 randomized trials per model.")
	outputs = [Path(model_path), Path(json_report_path), Path(markdown_report_path)]
	if any(path.exists() for path in outputs):
		raise FileExistsError(f"Refusing to overwrite existing v3 outputs: {[str(path) for path in outputs if path.exists()]}")
	frame = pd.read_csv(dataset_path, parse_dates=["date"])
	ifi_events = pd.read_csv(IFI_PATH, dtype={"District_LGD_Codes": "string"})
	_, _, dropped_events = prepare_event_labels(ifi_events)
	for label_name in LABELS:
		result = validate_ifi_association_rows(
			frame.to_dict(orient="records"),
			target_spec_id=LABEL_SPECIFICATIONS[label_name],
			prefix=f"{label_name}_label",
		)
		frame[f"__{label_name}_training_eligible"] = result.training_eligible
		frame[f"__{label_name}_evaluation_eligible"] = result.evaluation_eligible
	_validate_frame(frame)
	core_all = frame[frame["year"].between(TRAIN_START_YEAR, CV_END_YEAR)].copy()
	validation_all = frame[frame["year"].between(VALIDATION_START_YEAR, TRAIN_END_YEAR)].copy()
	full_training = frame[frame["year"].between(TRAIN_START_YEAR, TRAIN_END_YEAR)].copy()
	test_all = frame[frame["year"].between(TEST_START_YEAR, TEST_END_YEAR)].copy()

	all_candidates: list[dict[str, Any]] = []
	configuration_summaries = []
	for label_name in LABELS:
		for feature_name in FEATURE_SETS:
			candidates, details = _train_configuration(core_all, validation_all, label_name, feature_name, n_iter)
			all_candidates.extend(candidates)
			for candidate in candidates:
				if candidate["model_name"] == "SoftVotingEnsemble":
					parameters = candidate["best_parameters"]
				else:
					parameters = candidate["search"].best_params_
				configuration_summaries.append(
					{
						"label_name": label_name,
						"feature_name": feature_name,
						"model_name": candidate["model_name"],
						"cv_mean_pr_auc": candidate["cv_mean_pr_auc"],
						"cv_std_pr_auc": candidate["cv_std_pr_auc"],
						"oof_threshold_summary": candidate["oof_threshold"],
						"best_parameters": parameters,
						"soft_voting_cv_scores": details["voting_cv_scores"],
					}
				)

	validated_candidates = [_evaluate_validation_candidate(candidate) for candidate in all_candidates]
	feasible = [row for row in validated_candidates if row["threshold_selection"]["precision_constraint_met"]]
	if not feasible:
		raise ValueError("No candidate reaches validation precision >= 0.10; refusing to score the test period.")
	selection_pool = feasible
	selected = max(
		selection_pool,
		key=lambda row: (
			row["validation_metrics"]["f2"],
			row["validation_metrics"]["precision"],
			row["validation_pr_auc"],
			row["cv_mean_pr_auc"],
		),
	)
	selected_candidate = selected["candidate"]
	selected_label_column = LABELS[selected["label_name"]]
	selected_training_eligibility = f"__{selected['label_name']}_training_eligible"
	selected_evaluation_eligibility = f"__{selected['label_name']}_evaluation_eligible"
	selected_features = selected["feature_columns"]
	training = full_training[
		full_training[selected_label_column].notna()
		& full_training[selected_training_eligibility]
	].sort_values(["date", "lgd_code"])
	test = test_all[
		test_all[selected_label_column].notna()
		& test_all[selected_evaluation_eligibility]
	].sort_values(["date", "lgd_code"])
	X_training = training[selected_features].copy()
	y_training = training[selected_label_column].to_numpy(dtype=np.int8)
	X_test = test[selected_features].copy()
	y_test = test[selected_label_column].to_numpy(dtype=np.int8)
	if set(np.unique(y_training)) != {0, 1} or set(np.unique(y_test)) != {0, 1}:
		raise ValueError("Selected label does not contain both classes in final training and test periods.")

	final_model = _final_refit(selected_candidate["estimator"], X_training, y_training)
	# Refit the separately tuned logistic baseline on the same selected label/features.
	logistic_name = selected["label_name"], selected["feature_name"], "LogisticRegression"
	logistic_candidate = next(
		candidate
		for candidate in all_candidates
		if (candidate["label_name"], candidate["feature_name"], candidate["model_name"]) == logistic_name
	)
	logistic_model = _final_refit(logistic_candidate["estimator"], X_training, y_training)
	threshold = float(selected["threshold"])
	probabilities = final_model.predict_proba(X_test)[:, 1]
	predictions = (probabilities >= threshold).astype(np.int8)
	logistic_probabilities = logistic_model.predict_proba(X_test)[:, 1]
	logistic_predictions = (logistic_probabilities >= 0.5).astype(np.int8)
	majority = int(pd.Series(y_training).value_counts().idxmax())
	majority_predictions = np.full(len(y_test), majority, dtype=np.int8)
	majority_probabilities = np.full(len(y_test), float(y_training.mean()), dtype=float)
	test_results = {
		"selected_model": _metrics(y_test, predictions, probabilities),
		"logistic_regression_baseline": _metrics(y_test, logistic_predictions, logistic_probabilities),
		"majority_class_baseline": _metrics(y_test, majority_predictions, majority_probabilities),
	}
	bootstrap = _bootstrap(
		y_test,
		predictions,
		probabilities,
		majority_predictions,
		majority_probabilities,
		iterations=bootstrap_iterations,
	)
	probability_bands = _probability_bands(y_test, probabilities)
	district_recall = []
	for code in sorted(test["lgd_code"].astype(int).unique()):
		mask = test["lgd_code"].astype(int).to_numpy() == code
		district_recall.append(
			{
				"lgd_code": code,
				"district": DISTRICT_NAMES[code],
				"positive_support": int(y_test[mask].sum()),
				"recall": float(recall_score(y_test[mask], predictions[mask], zero_division=0)),
			}
		)
	importance = _feature_importances(final_model)

	# V2 is included only as an already-scored reference, never as a selection input.
	v2_report = json.loads(V2_REPORT_PATH.read_text(encoding="utf-8"))
	v2_metrics = v2_report["test_results"]["selected_model"]
	v2_as_v3 = dict(v2_metrics)
	v2_as_v3["brier_score"] = float(v2_report["reliability"]["brier_score"])
	v2_as_v3["f2"] = float(fbeta_score(
		# Reconstruct the v2 confusion-matrix point metrics, not row predictions.
		[0] * v2_metrics["confusion_matrix"][0][0]
		+ [0] * v2_metrics["confusion_matrix"][0][1]
		+ [1] * v2_metrics["confusion_matrix"][1][0]
		+ [1] * v2_metrics["confusion_matrix"][1][1],
		[0] * v2_metrics["confusion_matrix"][0][0]
		+ [1] * v2_metrics["confusion_matrix"][0][1]
		+ [0] * v2_metrics["confusion_matrix"][1][0]
		+ [1] * v2_metrics["confusion_matrix"][1][1],
		beta=2,
		zero_division=0,
	))
	v2_baseline_metrics = dict(v2_report["majority_baseline"]["metrics"])
	v2_baseline_confusion = v2_baseline_metrics["confusion_matrix"]
	v2_baseline_metrics["f2"] = float(fbeta_score(
		[0] * v2_baseline_confusion[0][0]
		+ [0] * v2_baseline_confusion[0][1]
		+ [1] * v2_baseline_confusion[1][0]
		+ [1] * v2_baseline_confusion[1][1],
		[0] * v2_baseline_confusion[0][0]
		+ [1] * v2_baseline_confusion[0][1]
		+ [0] * v2_baseline_confusion[1][0]
		+ [1] * v2_baseline_confusion[1][1],
		beta=2,
		zero_division=0,
	))
	v2_baseline_metrics["brier_score"] = (
		v2_baseline_confusion[1][0] + v2_baseline_confusion[1][1]
	) / sum(sum(row) for row in v2_baseline_confusion)
	v2_comparison = {
		"version": "v2",
		"label": "legacy same-day IFI event-start proxy (already seen test years)",
		"metrics": v2_as_v3,
		"majority_baseline": v2_baseline_metrics,
		"bootstrap_95_ci": v2_report["bootstrap_95_ci"],
		"per_district_recall": v2_report["per_district_recall"],
		"test_rows": v2_report["split"]["test_rows"],
	}
	v3_comparison = {
		"version": "v3",
		"label": "event starts in t through t+2",
		"metrics": test_results["selected_model"],
		"majority_baseline": test_results["majority_class_baseline"],
		"bootstrap_95_ci": bootstrap,
		"per_district_recall": district_recall,
		"test_rows": int(len(test)),
	}
	comparison = [v2_comparison, v3_comparison]

	label_balance = {}
	for label_name, label_column in LABELS.items():
		eligible = frame[frame[label_column].notna()]
		training_eligible_rows = eligible[eligible[f"__{label_name}_training_eligible"]]
		evaluation_eligible_rows = eligible[eligible[f"__{label_name}_evaluation_eligible"]]
		label_balance[label_name] = {
			"target_spec_id": LABEL_SPECIFICATIONS[label_name],
			"definition": "IFI event-start association only; negatives are inventory-snapshot non-matches, not verified flood absences.",
			"all_rows": {str(key): int(value) for key, value in eligible[label_column].value_counts().sort_index().items()},
			"training_eligible_rows": int(len(training_eligible_rows)),
			"evaluation_eligible_rows": int(len(evaluation_eligible_rows)),
			"train_2000_2018": {str(key): int(value) for key, value in training_eligible_rows[training_eligible_rows["year"].between(TRAIN_START_YEAR, TRAIN_END_YEAR)][label_column].value_counts().sort_index().items()},
			"validation_2015_2018": {str(key): int(value) for key, value in evaluation_eligible_rows[evaluation_eligible_rows["year"].between(VALIDATION_START_YEAR, TRAIN_END_YEAR)][label_column].value_counts().sort_index().items()},
			"test_2019_2023_second_look": {str(key): int(value) for key, value in evaluation_eligible_rows[evaluation_eligible_rows["year"].between(TEST_START_YEAR, TEST_END_YEAR)][label_column].value_counts().sort_index().items()},
		}

	all_validation_rows = []
	for row in validated_candidates:
		all_validation_rows.append({key: value for key, value in row.items() if key != "candidate"})
	selected_metadata = {
		"label": "REAL DATA - ERA5 reanalysis rainfall",
		"training_rows": int(len(training)),
		"validation_rows": int(len(selected_candidate["validation"])),
		"test_rows": int(len(test)),
		"feature_columns": selected_features,
		"target": selected_label_column,
		"target_spec_id": LABEL_SPECIFICATIONS[selected["label_name"]],
		"target_interpretation": "IFI event association only; a negative is a no-match in the declared inventory snapshot, not verified absence of flooding.",
		"selected_label_definition": selected["label_name"],
		"decision_threshold": threshold,
		"selected_model": selected["model_name"],
		"feature_set": selected["feature_name"],
		"train_period": [TRAIN_START_YEAR, TRAIN_END_YEAR],
		"model_selection_core": [TRAIN_START_YEAR, CV_END_YEAR],
		"validation_period": [VALIDATION_START_YEAR, TRAIN_END_YEAR],
		"test_period_second_look": [TEST_START_YEAR, TEST_END_YEAR],
		"test_years_previously_scored_for_v2": True,
		"train_test_row_and_event_overlap": False,
		"label_in_features": False,
	}
	selected_validation = {key: value for key, value in selected.items() if key != "candidate"}
	selected_validation["oof_threshold_summary"] = selected["oof_threshold_summary"]
	verdict = (
		f"Selected {selected['model_name']} with {selected['feature_name']} features and {selected['label_name']} labels. "
		f"At the frozen threshold, second-look test precision is {test_results['selected_model']['precision']:.3f} and recall is {test_results['selected_model']['recall']:.3f}. "
		"This test period was already scored for v2; these v3 test results are a second look, not fresh independent evidence."
	)
	report = {
		"label": "REAL DATA - ERA5 reanalysis rainfall",
		"target_interpretation": "IFI event association only; a negative means no match in the declared inventory snapshot, not verified absence of flooding.",
		"data_notice": "These are IFI association proxy targets, not independently verified flood-occurrence labels. ERA5 is reanalysis, not observed station rainfall.",
		"honesty_notice": "2019-2023 was already scored once for v2. V3 reports a second look at those test years, not a fresh independent test set.",
		"dataset": {"path": str(dataset_path), "rows": int(len(frame)), "source": "IFI-Impacts + data/real/era5/three_point/district_daily_rainfall.csv"},
		"label_balance": label_balance,
		"label_provenance": {
			label_name: {
				"inventory_snapshot_id": sorted(frame[f"{label_name}_label_inventory_snapshot_id"].unique().tolist()),
				"matching_rule_id": sorted(frame[f"{label_name}_label_matching_rule_id"].unique().tolist()),
				"matching_rule_version": sorted(frame[f"{label_name}_label_matching_rule_version"].unique().tolist()),
			}
			for label_name in LABELS
		},
		"dropped_events": dropped_events,
		"development_protocol": {
			"cv_years": [TRAIN_START_YEAR, CV_END_YEAR],
			"cv": (
				"Five expanding-window calendar-year folds on 2000-2014; each validation "
				"block follows its training years, with four initial warm-up years"
			),
			"final_validation_years": [VALIDATION_START_YEAR, TRAIN_END_YEAR],
			"final_refit_years": [TRAIN_START_YEAR, TRAIN_END_YEAR],
			"randomized_search_iterations_per_model": n_iter,
			"cv_scoring": "PR-AUC / average precision",
			"threshold_selection": (
				"Candidate thresholds from forward-chaining OOF predictions on 2000-2014 "
				"(initial warm-up years excluded); maximize F2 on 2015-2018 validation "
				"subject to precision >= 0.10."
			),
			"model_and_feature_selection": "Validation-block F2 under the precision constraint, then validation PR-AUC and CV PR-AUC tie-breaks.",
		},
		"selection": selected_validation,
		"candidate_validation_results": all_validation_rows,
		"cv_label_feature_model_comparison": configuration_summaries,
		"test_results": test_results,
		"probability_bands": probability_bands,
		"bootstrap_95_ci": bootstrap,
		"per_district_recall": district_recall,
		"top_10_feature_importances": importance,
		"v2_vs_v3": comparison,
		"v2_comparison_note": "V2 test metrics are historical legacy IFI-association proxy results; v3 uses the versioned IFI target gate. The same test years were used before, so this comparison is descriptive only and does not establish verified flood prediction.",
		"optional_variable_coverage": {
			"soil_moisture": SOIL_MOISTURE_COVERAGE,
			"river_discharge": RIVER_DISCHARGE_COVERAGE,
		},
		"verdict": verdict,
		"limitations": "Labels are IFI event associations, not verified flood occurrence. A negative means only no match in the declared inventory snapshot under the matching rule. IFI-Impacts is not a complete event-observation calendar. Optional soil moisture and river discharge were excluded because complete daily coverage could not be verified for every selected point. The v3 test comparison is a second look at 2019-2023, not an independent test.",
		"bundle_metadata": selected_metadata,
	}
	# Add event filtering metadata from the v3 dataset's retained source-row audit.
	outputs = [Path(model_path), Path(json_report_path), Path(markdown_report_path)]
	for path in outputs:
		path.parent.mkdir(parents=True, exist_ok=True)
	joblib.dump(
		{"pipeline": final_model, "metadata": selected_metadata, "threshold_selection": selected["threshold_selection"]},
		outputs[0],
	)
	outputs[1].write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
	outputs[2].write_text(_markdown_report(report), encoding="utf-8")
	print(json.dumps({"selection": selected_metadata, "test_results": test_results, "bootstrap_95_ci": bootstrap, "outputs": [str(path) for path in outputs]}, indent=2, default=str))
	return report


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--data", default=str(DATASET_PATH))
	parser.add_argument("--model", default=str(MODEL_PATH))
	parser.add_argument("--json-report", default=str(JSON_REPORT_PATH))
	parser.add_argument("--markdown-report", default=str(MARKDOWN_REPORT_PATH))
	parser.add_argument("--n-iter", type=int, default=20)
	parser.add_argument("--bootstrap-iterations", type=int, default=2000)
	args = parser.parse_args()
	logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
	try:
		train_real_model_v3(
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