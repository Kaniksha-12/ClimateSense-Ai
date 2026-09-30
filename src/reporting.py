from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def generate_quality_report(
    df: pd.DataFrame,
    report_path: str | Path,
    duplicates_removed: int = 0,
    features_created: list[str] | None = None,
) -> str:
    """Create a human-readable report describing the cleaned climate dataset."""
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    features_created = features_created or []
    missing = df.isna().sum()
    missing_pct = (missing / len(df) * 100) if len(df) else 0.0

    text_lines = [
        "# ClimateSense AI Data Quality Report",
        "",
        "## Dataset Overview",
        f"- Total records: {len(df)}",
        f"- Total columns: {len(df.columns)}",
        f"- Date range: {df['date'].min()} to {df['date'].max()}",
        f"- Geographic coverage: {df['latitude'].min():.4f} to {df['latitude'].max():.4f} latitude and {df['longitude'].min():.4f} to {df['longitude'].max():.4f} longitude",
        f"- Duplicate records removed: {duplicates_removed}",
        f"- Features created: {', '.join(features_created) if features_created else 'none'}",
        "",
        "## Missing Values",
    ]

    for column in df.columns:
        text_lines.append(f"- {column}: {missing[column]} ({missing_pct[column]:.2f}%)")

    text_lines.extend([
        "",
        "## Value Summaries",
    ])
    for column in df.select_dtypes(include=["number"]).columns:
        series = df[column]
        text_lines.append(
            f"- {column}: min={series.min()}, max={series.max()}, mean={series.mean():.3f}, median={series.median():.3f}"
        )

    text_lines.extend([
        "",
        "## Target State",
        "- Target data: currently unavailable because no validated flood-event dataset was identified for this MVP.",
    ])

    report_path.write_text("\n".join(text_lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    if "rainfall_mm" in df.columns:
        axes[0].hist(df["rainfall_mm"].dropna(), bins=20, color="#4c78a8")
        axes[0].set_title("Rainfall distribution")
    if "temperature_c" in df.columns:
        axes[1].hist(df["temperature_c"].dropna(), bins=20, color="#f58518")
        axes[1].set_title("Temperature distribution")
    if "relative_humidity_pct" in df.columns:
        axes[2].hist(df["relative_humidity_pct"].dropna(), bins=20, color="#54a24b")
        axes[2].set_title("Humidity distribution")
    for ax in axes:
        ax.set_xlabel("Value")
        ax.set_ylabel("Count")
    fig.tight_layout()
    plot_path = report_path.parent / "climate_distributions.png"
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)

    return str(report_path)
