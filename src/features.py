from __future__ import annotations

import pandas as pd


def generate_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create leakage-safe climate features based on historical observations only."""
    if df is None or df.empty:
        raise ValueError("Dataset is empty or missing.")

    out = df.copy().sort_values("date").reset_index(drop=True)

    if "rainfall_mm" not in out.columns:
        raise ValueError("Rainfall column is required for feature engineering.")

    out["previous_day_rainfall_mm"] = out["rainfall_mm"].shift(1, fill_value=0)
    out["rain_3day_mm"] = out["rainfall_mm"].rolling(window=3, min_periods=1).sum()
    out["rain_7day_mm"] = out["rainfall_mm"].rolling(window=7, min_periods=1).sum()
    rolling_mean = out["rainfall_mm"].shift(1).rolling(window=7, min_periods=1).mean()
    out["rainfall_anomaly_mm"] = out["rainfall_mm"] - rolling_mean.fillna(0)
    return out
