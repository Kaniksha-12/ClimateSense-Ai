"""CSV dataset inspection and command-line reporting."""

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def load_csv(data_path: str | Path) -> pd.DataFrame:
	"""Load a non-empty CSV, reporting common file and parsing errors clearly."""
	path = Path(data_path)
	if not path.is_file():
		raise FileNotFoundError(f"Dataset CSV does not exist: {path}")
	try:
		frame = pd.read_csv(path, comment="#")
	except (OSError, UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
		raise ValueError(f"Could not read dataset CSV '{path}': {exc}") from exc
	if frame.empty:
		raise ValueError(f"Dataset CSV contains no rows: {path}")
	if frame.shape[1] == 0:
		raise ValueError(f"Dataset CSV contains no columns: {path}")
	return frame


def analyze_dataframe(frame: pd.DataFrame) -> dict[str, Any]:
	"""Return a JSON-serializable overview of a structured dataset."""
	if frame.empty or frame.shape[1] == 0:
		raise ValueError("Cannot analyze an empty dataset.")
	categorical = frame.select_dtypes(exclude=["number", "datetime", "timedelta"]).columns
	numerical = frame.select_dtypes(include="number").columns
	categorical_details = {
		str(column): {
			"unique_count": int(frame[column].nunique(dropna=True)),
			"unique_values": [str(value) for value in frame[column].dropna().unique()[:50]],
			"unique_values_truncated": frame[column].nunique(dropna=True) > 50,
		}
		for column in categorical
	}
	stats_json = json.loads(frame.describe(include="all").to_json())
	return {
		"rows": int(frame.shape[0]),
		"columns_count": int(frame.shape[1]),
		"columns": [str(column) for column in frame.columns],
		"data_types": {str(column): str(dtype) for column, dtype in frame.dtypes.items()},
		"missing_values": {str(column): int(count) for column, count in frame.isna().sum().items()},
		"duplicate_rows": int(frame.duplicated().sum()),
		"numerical_columns": [str(column) for column in numerical],
		"categorical_columns": [str(column) for column in categorical],
		"basic_statistics": stats_json,
		"categorical_unique_values": categorical_details,
		"possible_target_columns": [
			str(column)
			for column in frame.columns
			if frame[column].nunique(dropna=True) > 1
			and frame[column].nunique(dropna=True) < len(frame)
		],
	}


def analyze_csv(data_path: str | Path) -> dict[str, Any]:
	"""Load and analyze a CSV dataset."""
	return analyze_dataframe(load_csv(data_path))


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--data", required=True, help="Path to a structured CSV dataset")
	args = parser.parse_args()
	logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
	try:
		print(json.dumps(analyze_csv(args.data), indent=2, default=str))
	except (FileNotFoundError, ValueError) as exc:
		logger.error("%s", exc)
		raise SystemExit(2) from exc


if __name__ == "__main__":
	main()
