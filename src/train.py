"""Train and compare random-forest and XGBoost classification pipelines."""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
	RandomizedSearchCV,
	StratifiedKFold,
	TimeSeriesSplit,
	cross_validate,
	train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from src.config import (
	DEFAULT_HIGH_RISK_THRESHOLD,
	DEFAULT_LOW_RISK_THRESHOLD,
	DEFAULT_MODEL_PATH,
	DEFAULT_REPORTS_DIR,
	RANDOM_STATE,
)
from src.data_analyzer import load_csv
from src.evaluate import classification_scorers, evaluate_predictions, select_best_model
from src.feature_engineering import ClimateFeatureEngineer
from src.preprocessing import build_preprocessor, validate_dataset

logger = logging.getLogger(__name__)


def _positive_class_index(classes: list[str], explicit_label: str | None) -> int:
	if explicit_label is not None:
		matches = [index for index, label in enumerate(classes) if label == str(explicit_label)]
		if not matches:
			raise ValueError(f"Positive label '{explicit_label}' is not in target classes: {classes}.")
		return matches[0]
	positive_names = {"1", "true", "yes", "flood", "flooded", "high", "positive"}
	matches = [index for index, label in enumerate(classes) if label.strip().lower() in positive_names]
	return matches[-1] if matches else len(classes) - 1


def _elevated_class_indices(classes: list[str], positive_index: int) -> list[int]:
	elevated_names = {
		"1", "true", "yes", "medium", "high", "severe", "very high", "extreme",
		"flood", "flooded", "positive",
	}
	identified = [index for index, label in enumerate(classes) if label.strip().lower() in elevated_names]
	return identified or [positive_index]


def _make_estimators(class_count: int, random_state: int) -> dict[str, Any]:
	xgb_parameters: dict[str, Any] = {
		"n_estimators": 100,
		"max_depth": 4,
		"learning_rate": 0.08,
		"subsample": 0.9,
		"colsample_bytree": 0.9,
		"reg_lambda": 1.0,
		"random_state": random_state,
		"n_jobs": 2,
		"tree_method": "hist",
		"verbosity": 0,
	}
	if class_count == 2:
		xgb_parameters.update(objective="binary:logistic", eval_metric="logloss")
	else:
		xgb_parameters.update(objective="multi:softprob", eval_metric="mlogloss", num_class=class_count)
	return {
		"RandomForest": RandomForestClassifier(
			n_estimators=150,
			max_features="sqrt",
			class_weight="balanced_subsample",
			random_state=random_state,
			n_jobs=2,
		),
		"XGBoost": ClassBalancedXGBClassifier(**xgb_parameters),
	}


class ClassBalancedXGBClassifier(XGBClassifier):
	"""Calculate balanced sample weights from each fit partition, including CV folds."""

	def fit(self, X: Any, y: Any, **kwargs: Any) -> "ClassBalancedXGBClassifier":
		kwargs["sample_weight"] = compute_sample_weight(class_weight="balanced", y=y)
		super().fit(X, y, **kwargs)
		return self


def _build_pipeline(estimator: Any, features: pd.DataFrame) -> Pipeline:
	return Pipeline(
		[
			("feature_engineering", ClimateFeatureEngineer()),
			("preprocessor", build_preprocessor(features)),
			("classifier", estimator),
		]
	)


def _find_temporal_column(frame: pd.DataFrame) -> str | None:
	for column in frame.columns:
		if pd.api.types.is_datetime64_any_dtype(frame[column]):
			return str(column)
		if re.search(r"(^|_)(date|datetime|timestamp|time)($|_)", str(column).lower()):
			parsed = pd.to_datetime(frame[column], errors="coerce", utc=True)
			if parsed.notna().mean() >= 0.8:
				return str(column)
	return None


def _profile_dataset(
	original: pd.DataFrame,
	development: pd.DataFrame,
	final_test: pd.DataFrame,
	target: str,
	temporal_column: str | None,
) -> dict[str, Any]:
	feature_columns = [column for column in development.columns if column != target]
	feature_frame = development[feature_columns]
	numeric = feature_frame.select_dtypes(include="number")
	outliers: dict[str, int] = {}
	if not numeric.empty:
		first_quartile = numeric.quantile(0.25)
		third_quartile = numeric.quantile(0.75)
		spread = third_quartile - first_quartile
		outliers = {
			str(column): int(
				((numeric[column] < first_quartile[column] - 1.5 * spread[column])
				 | (numeric[column] > third_quartile[column] + 1.5 * spread[column])).sum()
			)
			for column in numeric.columns
		}
	correlations = feature_frame.corr(numeric_only=True)
	high_correlations = [
		{
			"feature_a": str(correlations.columns[left]),
			"feature_b": str(correlations.columns[right]),
			"correlation": float(correlations.iloc[left, right]),
		}
		for left in range(len(correlations.columns))
		for right in range(left + 1, len(correlations.columns))
		if abs(correlations.iloc[left, right]) >= 0.85
	]
	class_distribution = lambda labels: {
		str(label): {
			"count": int(count),
			"percent": float(100 * count / len(labels)),
		}
		for label, count in labels.astype(str).value_counts().sort_index().items()
	}
	feature_leakage_suspects = [
		str(column)
		for column in feature_columns
		if any(term in str(column).lower() for term in ("target", "label", "outcome", "future", "tomorrow"))
	]
	target_correlations = {}
	if pd.api.types.is_numeric_dtype(development[target]):
		target_correlations = {
			str(name): float(value)
			for name, value in development[feature_columns + [target]].corr(numeric_only=True)[target]
			.drop(labels=[target])
		.items()
		}
	return {
		"development_shape": [int(development.shape[0]), int(development.shape[1])],
		"final_test_shape": [int(final_test.shape[0]), int(final_test.shape[1])],
		"original_shape": [int(original.shape[0]), int(original.shape[1])],
		"feature_columns": [str(column) for column in feature_columns],
		"feature_dtypes": {str(column): str(dtype) for column, dtype in feature_frame.dtypes.items()},
		"missing_values_in_original": {
			str(column): int(value) for column, value in original.isna().sum().items()
		},
		"duplicate_rows_in_original": int(original.duplicated().sum()),
		"outlier_counts_iqr_development_features": outliers,
		"highly_correlated_feature_pairs_abs_ge_0_85": high_correlations,
		"numeric_feature_target_correlations": target_correlations,
		"possible_leakage_feature_names": feature_leakage_suspects,
		"temporal_column": temporal_column,
		"observation_type": "temporal series" if temporal_column else "independent observations",
		"split_strategy": "chronological" if temporal_column else "stratified random",
		"development_class_distribution": class_distribution(development[target]),
		"final_test_class_distribution": class_distribution(final_test[target]),
	}


def _summarize_cv(scores: dict[str, np.ndarray], metric_names: list[str]) -> dict[str, Any]:
	return {
		metric: {
			"mean": float(np.nanmean(scores[f"test_{metric}"])),
			"std": float(np.nanstd(scores[f"test_{metric}"], ddof=1)),
			"fold_scores": [float(value) for value in scores[f"test_{metric}"]],
		}
		for metric in metric_names
	}


def _write_visualizations(
	results: dict[str, dict[str, Any]],
	best_name: str,
	figure_dir: Path,
	class_names: list[str],
	best_pipeline: Pipeline,
	class_distribution: dict[str, int],
	data_notice: str | None,
) -> None:
	figure_dir.mkdir(parents=True, exist_ok=True)
	fig, axis = plt.subplots(figsize=(6, 4))
	class_positions = np.arange(len(class_distribution))
	axis.bar(class_positions, list(class_distribution.values()))
	axis.set_xticks(class_positions, list(class_distribution.keys()))
	axis.set_ylabel("Observations")
	axis.set_title(f"{data_notice}\nTarget class distribution" if data_notice else "Target class distribution")
	fig.tight_layout()
	fig.savefig(figure_dir / "class_distribution.png", dpi=140)
	plt.close(fig)

	metric_names = ["accuracy", "precision", "recall", "f1"]
	positions = np.arange(len(metric_names))
	width = 0.8 / len(results)
	fig, axis = plt.subplots(figsize=(8, 4.5))
	for model_index, (model_name, metrics) in enumerate(results.items()):
		values = [metrics[name] for name in metric_names]
		axis.bar(positions - 0.4 + width / 2 + model_index * width, values, width, label=model_name)
	axis.set_xticks(positions, metric_names)
	axis.set_ylim(0, 1)
	axis.set_ylabel("Held-out score")
	axis.set_title(f"{data_notice}\nModel comparison" if data_notice else "Model comparison")
	axis.legend()
	fig.tight_layout()
	fig.savefig(figure_dir / "model_comparison.png", dpi=140)
	plt.close(fig)

	matrix = np.asarray(results[best_name]["confusion_matrix"])
	fig, axis = plt.subplots(figsize=(5, 4.5))
	image = axis.imshow(matrix, interpolation="nearest", cmap="Blues")
	fig.colorbar(image, ax=axis)
	axis.set(
		xticks=np.arange(len(class_names)),
		yticks=np.arange(len(class_names)),
		xticklabels=class_names,
		yticklabels=class_names,
		xlabel="Predicted label",
		ylabel="True label",
		title=f"{data_notice}\n{best_name} confusion matrix" if data_notice else f"{best_name} confusion matrix",
	)
	plt.setp(axis.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")
	for row in range(matrix.shape[0]):
		for column in range(matrix.shape[1]):
			axis.text(column, row, str(matrix[row, column]), ha="center", va="center")
	fig.tight_layout()
	fig.savefig(figure_dir / "confusion_matrix.png", dpi=140)
	plt.close(fig)

	classifier = best_pipeline.named_steps["classifier"]
	if hasattr(classifier, "feature_importances_"):
		importance = np.asarray(classifier.feature_importances_)
		feature_names = best_pipeline.named_steps["preprocessor"].get_feature_names_out()
		top_indices = np.argsort(importance)[-15:]
		fig, axis = plt.subplots(figsize=(8, max(4, len(top_indices) * 0.28)))
		axis.barh(np.asarray(feature_names)[top_indices], importance[top_indices])
		axis.set_xlabel("Feature importance")
		axis.set_title(
			f"{data_notice}\n{best_name} feature importance"
			if data_notice
			else f"{best_name} feature importance"
		)
		fig.tight_layout()
		fig.savefig(figure_dir / "feature_importance.png", dpi=140)
		plt.close(fig)


def train_model(
	data: pd.DataFrame,
	target: str,
	model_path: str | Path = DEFAULT_MODEL_PATH,
	reports_dir: str | Path = DEFAULT_REPORTS_DIR,
	test_size: float = 0.2,
	random_state: int = RANDOM_STATE,
	positive_label: str | None = None,
	low_threshold: float = DEFAULT_LOW_RISK_THRESHOLD,
	high_threshold: float = DEFAULT_HIGH_RISK_THRESHOLD,
	data_notice: str | None = None,
	final_test_data: pd.DataFrame | None = None,
	cv_folds: int = 3,
	tuning_iterations: int = 4,
) -> dict[str, Any]:
	"""Tune on development data, evaluate candidates on held-out data, and save the CV-selected model."""
	if not 0 < test_size < 1:
		raise ValueError("test_size must be greater than 0 and less than 1.")
	if not 0 <= low_threshold < high_threshold <= 1:
		raise ValueError("Risk thresholds must satisfy 0 <= low < high <= 1.")
	if cv_folds < 2:
		raise ValueError("cv_folds must be at least 2.")
	if tuning_iterations < 1:
		raise ValueError("tuning_iterations must be at least 1.")
	original = data.copy()
	clean = validate_dataset(original, target)
	feature_columns = [column for column in clean.columns if column != target]
	if not feature_columns:
		raise ValueError("Training data must contain at least one feature in addition to the target.")
	encoder = LabelEncoder()
	development_labels = encoder.fit_transform(clean[target].astype(str))
	classes = [str(label) for label in encoder.classes_]
	class_counts = np.bincount(development_labels)
	if class_counts.min() < 2:
		raise ValueError("Each target class needs at least two labeled development rows.")
	positive_index = _positive_class_index(classes, positive_label)
	elevated_indices = _elevated_class_indices(classes, positive_index)
	temporal_column = _find_temporal_column(clean.drop(columns=[target]))
	if final_test_data is None:
		if temporal_column:
			timestamps = pd.to_datetime(clean[temporal_column], errors="coerce", utc=True)
			if timestamps.isna().any():
				raise ValueError(f"Temporal column '{temporal_column}' contains invalid or missing timestamps.")
			ordered_indices = np.argsort(timestamps.to_numpy())
			cutoff = int(len(clean) * (1 - test_size))
			if cutoff < 2 or len(clean) - cutoff < 1:
				raise ValueError("Not enough rows for the requested chronological holdout split.")
			development = clean.iloc[ordered_indices[:cutoff]].reset_index(drop=True)
			final_test = clean.iloc[ordered_indices[cutoff:]].reset_index(drop=True)
		else:
			development, final_test = train_test_split(
				clean,
				test_size=test_size,
				random_state=random_state,
				stratify=clean[target].astype(str),
			)
			development = development.reset_index(drop=True)
			final_test = final_test.reset_index(drop=True)
	else:
		development = clean.reset_index(drop=True)
		final_test = validate_dataset(final_test_data, target).reset_index(drop=True)
		final_features = [column for column in final_test.columns if column != target]
		if set(final_features) != set(feature_columns):
			raise ValueError(
				"Final test features must match development features. "
				f"Expected {feature_columns}, found {final_features}."
			)
		final_test = final_test[feature_columns + [target]]
		if temporal_column:
			if temporal_column not in final_test.columns:
				raise ValueError(f"Final test data must include temporal column '{temporal_column}'.")
			development_times = pd.to_datetime(development[temporal_column], errors="coerce", utc=True)
			test_times = pd.to_datetime(final_test[temporal_column], errors="coerce", utc=True)
			if development_times.isna().any() or test_times.isna().any():
				raise ValueError(f"Temporal column '{temporal_column}' contains invalid or missing timestamps.")
			if development_times.max() >= test_times.min():
				raise ValueError("Chronological holdout must occur strictly after all development observations.")
			development = development.iloc[np.argsort(development_times.to_numpy())].reset_index(drop=True)
			final_test = final_test.iloc[np.argsort(test_times.to_numpy())].reset_index(drop=True)

	development_features = development[feature_columns]
	final_test_features = final_test[feature_columns]
	try:
		development_labels = encoder.fit_transform(development[target].astype(str))
		final_test_labels = encoder.transform(final_test[target].astype(str))
	except ValueError as exc:
		raise ValueError("Final test target labels must match the development target classes.") from exc
	class_counts = np.bincount(development_labels, minlength=len(classes))
	if class_counts.min() < 2:
		raise ValueError("Each target class needs at least two labeled development rows.")
	if len(np.unique(final_test_labels)) < 2:
		logger.warning("Final test set contains only one class; ROC-AUC will be unavailable.")
	if temporal_column:
		cv_splits = min(cv_folds, len(development) - 1)
		cv = TimeSeriesSplit(n_splits=cv_splits)
	else:
		cv_splits = min(cv_folds, int(class_counts.min()))
		cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=random_state)
	if cv_splits < 2:
		raise ValueError("Not enough development rows for at least 2 cross-validation folds.")
	split_indices = list(cv.split(development_features, development_labels))
	if temporal_column and any(
		len(np.unique(development_labels[train_indices])) < 2
		for train_indices, _ in split_indices
	):
		raise ValueError("Temporal CV training folds must contain all target classes; reduce cv_folds or add data.")
	scoring = classification_scorers(len(classes), positive_index)
	metric_names = list(scoring)
	base_estimators = _make_estimators(len(classes), random_state)
	baseline_pipelines = {
		name: _build_pipeline(estimator, development_features)
		for name, estimator in base_estimators.items()
	}
	cv_summary: dict[str, dict[str, Any]] = {}
	for name, pipeline in baseline_pipelines.items():
		fold_scores = cross_validate(
			pipeline,
			development_features,
			development_labels,
			cv=split_indices,
			scoring=scoring,
			n_jobs=1,
			error_score="raise",
		)
		cv_summary[f"Baseline {name}"] = _summarize_cv(fold_scores, metric_names)

	search_spaces = {
		"RandomForest": {
			"classifier__n_estimators": [100, 200, 300],
			"classifier__max_depth": [None, 4, 8, 12],
			"classifier__min_samples_split": [2, 5, 10],
			"classifier__min_samples_leaf": [1, 2, 4],
			"classifier__max_features": ["sqrt", 0.7],
			"classifier__class_weight": [None, "balanced", "balanced_subsample"],
		},
		"XGBoost": {
			"classifier__n_estimators": [80, 150, 240],
			"classifier__max_depth": [2, 3, 4],
			"classifier__learning_rate": [0.03, 0.08, 0.15],
			"classifier__min_child_weight": [1, 3, 5],
			"classifier__subsample": [0.7, 0.9, 1.0],
			"classifier__colsample_bytree": [0.7, 0.9, 1.0],
			"classifier__reg_alpha": [0.0, 0.1, 0.5],
			"classifier__reg_lambda": [1.0, 3.0, 5.0],
		},
	}
	searches: dict[str, RandomizedSearchCV] = {}
	tuned_pipelines: dict[str, Pipeline] = {}
	for name in ("RandomForest", "XGBoost"):
		search = RandomizedSearchCV(
			estimator=_build_pipeline(clone(base_estimators[name]), development_features),
			param_distributions=search_spaces[name],
			n_iter=tuning_iterations,
			scoring=scoring,
			refit="f1",
			cv=split_indices,
			random_state=random_state,
			n_jobs=1,
			return_train_score=False,
			error_score="raise",
		)
		search.fit(development_features, development_labels)
		searches[name] = search
		tuned_pipelines[name] = search.best_estimator_
		best_index = int(search.best_index_)
		cv_summary[f"Tuned {name}"] = {
			metric: {
				"mean": float(search.cv_results_[f"mean_test_{metric}"][best_index]),
				"std": float(search.cv_results_[f"std_test_{metric}"][best_index]),
				"fold_scores": [],
			}
			for metric in metric_names
		}

	tuned_names = [name for name in cv_summary if name.startswith("Tuned ")]
	if tuned_names:
		best_name = max(
			tuned_names,
			key=lambda name: (
				cv_summary[name]["f1"]["mean"],
				cv_summary[name]["recall"]["mean"],
				cv_summary[name]["precision"]["mean"],
			),
		)
	else:
		best_name = max(
			cv_summary,
			key=lambda name: (
				cv_summary[name]["f1"]["mean"],
				cv_summary[name]["recall"]["mean"],
				cv_summary[name]["precision"]["mean"],
			),
		)
	model_pipelines: dict[str, Pipeline] = {
		f"Baseline {name}": pipeline for name, pipeline in baseline_pipelines.items()
	}
	model_pipelines.update({f"Tuned {name}": pipeline for name, pipeline in tuned_pipelines.items()})
	best_pipeline = model_pipelines[best_name]
	for name, pipeline in baseline_pipelines.items():
		pipeline.fit(development_features, development_labels)
	final_test_evaluations: dict[str, dict[str, Any]] = {}
	for name, pipeline in model_pipelines.items():
		final_predictions = pipeline.predict(final_test_features)
		final_probabilities = pipeline.predict_proba(final_test_features)
		final_test_evaluations[name] = evaluate_predictions(
			final_test_labels,
			final_predictions,
			final_probabilities,
			len(classes),
			positive_index,
		)
		metrics = final_test_evaluations[name]
		logger.info(
			"%s%s final holdout: accuracy %.3f, precision %.3f, recall %.3f, F1 %.3f",
			f"{data_notice} | " if data_notice else "",
			name,
			metrics["accuracy"],
			metrics["precision"],
			metrics["recall"],
			metrics["f1"],
		)
	final_test_evaluations["Best Model"] = final_test_evaluations[best_name]
	class_distribution = {
		label: int(count) for label, count in zip(classes, class_counts)
	}
	data_profile = _profile_dataset(original, development, final_test, target, temporal_column)
	importance = getattr(best_pipeline.named_steps["classifier"], "feature_importances_", None)
	feature_names = best_pipeline.named_steps["preprocessor"].get_feature_names_out()
	feature_importance: list[dict[str, Any]] = []
	if importance is not None:
		feature_importance = [
			{"feature": str(feature_names[index]), "importance": float(importance[index])}
			for index in np.argsort(importance)[::-1]
		]
	model_configuration = (
		searches[best_name.removeprefix("Tuned ")].best_params_
		if best_name.startswith("Tuned ")
		else best_pipeline.named_steps["classifier"].get_params(deep=False)
	)
	metadata = {
		"model_name": best_name,
		"target": target,
		"risk_type": "flood" if "flood" in target.lower() else target,
		"feature_columns": [str(column) for column in feature_columns],
		"classes": classes,
		"positive_class": classes[positive_index],
		"positive_class_index": positive_index,
		"elevated_class_indices": elevated_indices,
		"low_risk_threshold": low_threshold,
		"high_risk_threshold": high_threshold,
		"random_state": random_state,
		"test_size": test_size,
		"cv_folds": int(cv_splits),
		"training_rows": int(len(development_features)),
		"test_rows": int(len(final_test_features)),
		"data_notice": data_notice,
		"feature_names_after_engineering": [
			str(name) for name in best_pipeline.named_steps["feature_engineering"].get_feature_names_out(feature_columns)
		],
	}
	model_file = Path(model_path)
	model_file.parent.mkdir(parents=True, exist_ok=True)
	joblib.dump(
		{
			"pipeline": best_pipeline,
			"metadata": metadata,
			"metrics": final_test_evaluations,
			"model_configuration": model_configuration,
			"feature_metadata": {
				"input_features": metadata["feature_columns"],
				"engineered_features": metadata["feature_names_after_engineering"],
			},
		},
		model_file,
	)
	report_path = Path(reports_dir)
	report_path.mkdir(parents=True, exist_ok=True)
	report = {
		"best_model": best_name,
		"selection_metric": "Mean CV F1, then mean CV recall, then mean CV precision",
		"final_test_used_for_model_selection": False,
		"target": target,
		"data_notice": data_notice,
		"classes": classes,
		"features": metadata["feature_names_after_engineering"],
		"dataset_profile": data_profile,
		"class_imbalance_strategy": (
			"Target is near balanced; no resampling used. Random Forest compares class weights; "
			"XGBoost computes balanced weights within each fit fold."
		),
		"cross_validation": cv_summary,
		"tuning": {
			"cv_folds": int(cv_splits),
			"iterations_per_model": int(tuning_iterations),
			"selected_configuration": model_configuration,
		},
		"model_comparison_final_test": final_test_evaluations,
		"final_test_metrics": final_test_evaluations["Best Model"],
		"feature_importance": feature_importance,
	}
	(report_path / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
	_write_visualizations(
		final_test_evaluations,
		best_name,
		report_path / "figures",
		classes,
		best_pipeline,
		class_distribution,
		data_notice,
	)
	logger.info("Saved best model (%s) to %s", best_name, model_file)
	return {
		"best_model": best_name,
		"metadata": metadata,
		"evaluations": final_test_evaluations,
		"cross_validation": cv_summary,
		"dataset_profile": data_profile,
		"feature_importance": feature_importance,
		"data_notice": data_notice,
	}


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--data", required=True, help="Path to a labeled CSV")
	parser.add_argument("--target", required=True, help="Name of the existing label column")
	parser.add_argument("--model", default=str(DEFAULT_MODEL_PATH), help="Output joblib path")
	parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
	parser.add_argument("--test-size", type=float, default=0.2)
	parser.add_argument("--seed", type=int, default=RANDOM_STATE)
	parser.add_argument("--positive-label", help="Optional positive class label for binary metrics")
	parser.add_argument("--low-threshold", type=float, default=DEFAULT_LOW_RISK_THRESHOLD)
	parser.add_argument("--high-threshold", type=float, default=DEFAULT_HIGH_RISK_THRESHOLD)
	parser.add_argument("--data-notice", help="Provenance notice stored with results and predictions")
	parser.add_argument("--final-test-data", help="Optional independent labeled CSV held out from CV and tuning")
	parser.add_argument("--cv-folds", type=int, default=3)
	parser.add_argument("--tuning-iterations", type=int, default=4)
	args = parser.parse_args()
	logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
	try:
		result = train_model(
			data=load_csv(args.data),
			target=args.target,
			model_path=args.model,
			reports_dir=args.reports_dir,
			test_size=args.test_size,
			random_state=args.seed,
			positive_label=args.positive_label,
			low_threshold=args.low_threshold,
			high_threshold=args.high_threshold,
			data_notice=args.data_notice,
			final_test_data=load_csv(args.final_test_data) if args.final_test_data else None,
			cv_folds=args.cv_folds,
			tuning_iterations=args.tuning_iterations,
		)
		print(json.dumps(result, indent=2))
	except (FileNotFoundError, ValueError, ImportError) as exc:
		logger.error("Training failed: %s", exc)
		raise SystemExit(2) from exc


if __name__ == "__main__":
	main()
