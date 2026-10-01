"""Classification metrics and model comparison helpers."""

from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, make_scorer
from sklearn.metrics import (
	accuracy_score,
	confusion_matrix,
	f1_score,
	precision_score,
	recall_score,
	roc_auc_score,
)
from sklearn.preprocessing import label_binarize


def evaluate_predictions(
	y_true: np.ndarray,
	y_pred: np.ndarray,
	probabilities: np.ndarray,
	class_count: int,
	positive_class_index: int,
) -> dict[str, Any]:
	"""Calculate classification metrics, emphasizing flood-class recall and F1."""
	binary = class_count == 2
	average = "binary" if binary else "macro"
	metric_options: dict[str, Any] = {"average": average, "zero_division": 0}
	if binary:
		metric_options["pos_label"] = positive_class_index
	results: dict[str, Any] = {
		"accuracy": float(accuracy_score(y_true, y_pred)),
		"precision": float(precision_score(y_true, y_pred, **metric_options)),
		"recall": float(recall_score(y_true, y_pred, **metric_options)),
		"f1": float(f1_score(y_true, y_pred, **metric_options)),
		"roc_auc": None,
		"pr_auc": None,
		"confusion_matrix": confusion_matrix(y_true, y_pred, labels=np.arange(class_count)).tolist(),
	}
	try:
		if binary:
			results["roc_auc"] = float(
				roc_auc_score(y_true == positive_class_index, probabilities[:, positive_class_index])
			)
			results["pr_auc"] = float(
				average_precision_score(y_true == positive_class_index, probabilities[:, positive_class_index])
			)
		else:
			results["roc_auc"] = float(
				roc_auc_score(y_true, probabilities, multi_class="ovr", average="macro")
			)
	except (ValueError, IndexError):
		results["roc_auc"] = None
		results["pr_auc"] = None
	return results


def classification_scorers(class_count: int, positive_class_index: int) -> dict[str, Any]:
	"""Build consistent binary-positive or macro-averaged CV scorers."""
	binary = class_count == 2
	average = "binary" if binary else "macro"
	metric_options: dict[str, Any] = {"average": average, "zero_division": 0}
	if binary:
		metric_options["pos_label"] = positive_class_index
	scorers: dict[str, Any] = {
		"accuracy": "accuracy",
		"precision": make_scorer(precision_score, **metric_options),
		"recall": make_scorer(recall_score, **metric_options),
		"f1": make_scorer(f1_score, **metric_options),
	}
	if binary:
		def roc_auc_scorer(estimator: Any, features: Any, labels: np.ndarray) -> float:
			probabilities = estimator.predict_proba(features)[:, positive_class_index]
			return float(roc_auc_score(labels == positive_class_index, probabilities))

		def pr_auc_scorer(estimator: Any, features: Any, labels: np.ndarray) -> float:
			probabilities = estimator.predict_proba(features)[:, positive_class_index]
			return float(average_precision_score(labels == positive_class_index, probabilities))

		scorers["roc_auc"] = roc_auc_scorer
		scorers["pr_auc"] = pr_auc_scorer
	else:
		def roc_auc_scorer(estimator: Any, features: Any, labels: np.ndarray) -> float:
			return float(
				roc_auc_score(labels, estimator.predict_proba(features), multi_class="ovr", average="macro")
			)

		scorers["roc_auc"] = roc_auc_scorer
	return scorers


def select_best_model(results: dict[str, dict[str, Any]]) -> str:
	"""Prefer F1, then recall, then precision for risk detection."""
	if not results:
		raise ValueError("No model evaluation results are available.")
	return max(
		results,
		key=lambda model: (
			results[model].get("f1", 0.0),
			results[model].get("recall", 0.0),
			results[model].get("precision", 0.0),
		),
	)
