"""Climate-aware feature generation that only uses columns present in the data."""

import re
from typing import Any

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class ClimateFeatureEngineer(BaseEstimator, TransformerMixin):
    """Add precipitation aggregates and calendar features when source fields exist."""

    def fit(self, features: pd.DataFrame, y: Any = None) -> "ClimateFeatureEngineer":
        if not isinstance(features, pd.DataFrame):
            raise TypeError("ClimateFeatureEngineer expects pandas DataFrame input.")
        self.feature_names_in_ = features.columns.to_numpy(dtype=object)
        self.n_features_in_ = features.shape[1]
        self.precipitation_columns_ = [
            column
            for column in features.columns
            if re.search(r"rain|precip", str(column), flags=re.IGNORECASE)
        ]
        self.date_columns_ = []
        for column in features.columns:
            if re.search(r"(^|_)(date|datetime|timestamp|time)($|_)", str(column).lower()):
                parsed = pd.to_datetime(features[column], errors="coerce", utc=True)
                if parsed.notna().sum() >= max(1, int(len(features) * 0.5)):
                    self.date_columns_.append(column)
        return self

    def transform(self, features: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(features, pd.DataFrame):
            raise TypeError("ClimateFeatureEngineer expects pandas DataFrame input.")
        transformed = features.copy()
        precipitation_columns = getattr(self, "precipitation_columns_", [])
        if len(precipitation_columns) > 1:
            precipitation = transformed[precipitation_columns].apply(pd.to_numeric, errors="coerce")
            transformed["precipitation_total"] = precipitation.sum(axis=1, min_count=1)
        for column in getattr(self, "date_columns_", []):
            parsed = pd.to_datetime(transformed[column], errors="coerce", utc=True)
            transformed[f"{column}_month"] = parsed.dt.month
            transformed[f"{column}_day_of_year"] = parsed.dt.dayofyear
            transformed[f"{column}_day_of_week"] = parsed.dt.dayofweek
            transformed = transformed.drop(columns=[column])
        return transformed

    def get_feature_names_out(self, input_features: Any = None) -> Any:
        names = list(input_features if input_features is not None else self.feature_names_in_)
        output = names[:]
        precipitation_columns = getattr(self, "precipitation_columns_", [])
        date_columns = getattr(self, "date_columns_", [])
        if len(precipitation_columns) > 1:
            output.append("precipitation_total")
        for name in names:
            if name in date_columns:
                output.remove(name)
                output.extend([f"{name}_month", f"{name}_day_of_year", f"{name}_day_of_week"])
        return pd.Index(output, dtype=object).to_numpy()
