"""Load and validate climate-risk predictions from JSON."""

import json
from pathlib import Path

import pandas as pd


REQUIRED_FIELDS = {
    "location",
    "latitude",
    "longitude",
    "risk_type",
    "risk_score",
    "risk_level",
}
VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_predictions.json"


def load_predictions(file_path: str | Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Load prediction records from JSON and return them as a DataFrame."""
    path = Path(file_path)
    try:
        with path.open(encoding="utf-8") as predictions_file:
            records = json.load(predictions_file)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in predictions file {path}: {error}") from error

    if not isinstance(records, list):
        raise ValueError("Predictions JSON must contain a list of records.")

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Prediction at index {index} must be a JSON object.")

        missing_fields = REQUIRED_FIELDS - record.keys()
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"Prediction at index {index} is missing required fields: {missing}.")

        score = record["risk_score"]
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0 <= score <= 1
        ):
            raise ValueError(f"Prediction at index {index} must have a risk_score between 0 and 1.")

        risk_level = record["risk_level"]
        if not isinstance(risk_level, str) or risk_level not in VALID_RISK_LEVELS:
            raise ValueError(
                f"Prediction at index {index} has invalid risk_level {risk_level!r}; "
                "expected LOW, MEDIUM, or HIGH."
            )

    return pd.DataFrame.from_records(records)