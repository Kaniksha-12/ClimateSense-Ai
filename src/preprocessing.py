"""Dataset validation and leakage-safe sklearn preprocessing."""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data_analyzer import load_csv

logger = logging.getLogger(__name__)
_LEAKAGE_TERMS = ("target", "label", "outcome", "future", "next_day", "tomorrow")


def validate_dataset(
    frame: pd.DataFrame,
    target: str | None = None,
    max_missing_fraction: float = 0.6,
) -> pd.DataFrame:
    """Validate data, remove exact duplicates, and normalize invalid numeric values."""
    if not 0 <= max_missing_fraction <= 1:
        raise ValueError("max_missing_fraction must be between 0 and 1.")
    if frame.empty or frame.shape[1] == 0:
        raise ValueError("Dataset is empty; provide a CSV with rows and columns.")
    if not frame.columns.is_unique:
        raise ValueError("Dataset has duplicate column names; rename them before training.")
    clean = frame.copy()
    if target is not None and target not in clean.columns:
        raise ValueError(
            f"Target column '{target}' was not found. Available columns: "
            f"{', '.join(map(str, clean.columns))}. A valid labeled target is required "
            "for supervised prediction; labels will not be invented."
        )
    duplicates = int(clean.duplicated().sum())
    if duplicates:
        logger.warning("Removing %d duplicate rows.", duplicates)
        clean = clean.drop_duplicates().reset_index(drop=True)

    for column in clean.select_dtypes(include="number").columns:
        values = clean[column].to_numpy(dtype=float, na_value=np.nan)
        invalid_count = int(np.isinf(values).sum())
        if invalid_count:
            logger.warning("Replacing %d infinite values in '%s' with missing values.", invalid_count, column)
            clean[column] = clean[column].replace([np.inf, -np.inf], np.nan)
    for column in clean.select_dtypes(include=["object", "string"]).columns:
        present = clean[column].dropna()
        if present.empty:
            continue
        converted = pd.to_numeric(present, errors="coerce")
        if converted.notna().mean() >= 0.9:
            before = int(clean[column].isna().sum())
            clean[column] = pd.to_numeric(clean[column], errors="coerce")
            invalid_count = int(clean[column].isna().sum()) - before
            if invalid_count > 0:
                logger.warning(
                    "Found %d invalid numeric values in '%s'; treating them as missing.",
                    invalid_count,
                    column,
                )

    excessive = [
        str(column)
        for column, fraction in clean.isna().mean().items()
        if fraction > max_missing_fraction and column != target
    ]
    if excessive:
        logger.warning(
            "Columns exceed %.0f%% missing values and may be unsuitable features: %s",
            max_missing_fraction * 100,
            ", ".join(excessive),
        )
    if target is not None:
        missing_targets = int(clean[target].isna().sum())
        if missing_targets:
            logger.warning("Dropping %d rows with missing target labels.", missing_targets)
            clean = clean.dropna(subset=[target]).reset_index(drop=True)
        classes = clean[target].nunique(dropna=True)
        if classes < 2:
            raise ValueError(
                f"Target '{target}' must contain at least two labeled classes; found {classes}."
            )
        if clean.empty:
            raise ValueError(f"No labeled rows remain for target '{target}'.")
        suspects = [
            str(column)
            for column in clean.columns
            if column != target
            and any(term in str(column).lower() for term in _LEAKAGE_TERMS)
        ]
        if suspects:
            logger.warning(
                "Potential target leakage: review feature columns %s before training.",
                ", ".join(suspects),
            )
    logger.info("Validated %d rows and %d columns.", len(clean), clean.shape[1])
    return clean


def load_and_validate_csv(
    data_path: str | Path,
    target: str | None = None,
    max_missing_fraction: float = 0.6,
) -> pd.DataFrame:
    """Read and validate a dataset CSV."""
    return validate_dataset(load_csv(data_path), target, max_missing_fraction)


def build_preprocessor(features: pd.DataFrame) -> ColumnTransformer:
    """Build preprocessing that will be fit only on the training partition."""
    numeric_columns = list(features.select_dtypes(include="number").columns)
    categorical_columns = [column for column in features.columns if column not in numeric_columns]
    if not numeric_columns and not categorical_columns:
        raise ValueError("No usable feature columns were found.")
    transformers: list[tuple[str, Pipeline, list[Any]]] = []
    if numeric_columns:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_columns,
            )
        )
    if categorical_columns:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(strategy="constant", fill_value="__missing__", keep_empty_features=True),
                        ),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_columns,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop", verbose_feature_names_out=True)
