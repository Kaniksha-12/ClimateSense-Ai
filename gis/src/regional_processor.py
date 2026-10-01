"""Join climate predictions to administrative regions and summarize regional risk."""

from pathlib import Path

import geopandas as gpd
import pandas as pd


DEFAULT_BOUNDARY_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "india_admin1_simplified.geojson"
)
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")
RISK_TYPES = ("flood", "drought", "heatwave", "air_quality")


def load_admin_regions(boundary_path: str | Path = DEFAULT_BOUNDARY_PATH) -> gpd.GeoDataFrame:
    """Load state/UT boundaries and standardize their name field and CRS."""
    boundaries = gpd.read_file(boundary_path)
    if boundaries.crs is None:
        raise ValueError("Administrative boundaries must declare a coordinate reference system.")

    name_field = next(
        (field for field in ("region_name", "shapeName", "NAME_1", "name") if field in boundaries),
        None,
    )
    if name_field is None:
        raise ValueError("Administrative boundaries must contain a region name field.")

    boundaries = boundaries[[name_field, "geometry"]].rename(columns={name_field: "region_name"})
    if boundaries.crs.to_epsg() != 4326:
        boundaries = boundaries.to_crs("EPSG:4326")
    if boundaries["region_name"].isna().any():
        raise ValueError("Administrative boundaries contain unnamed regions.")

    return boundaries


def aggregate_predictions_by_region(
    predictions: gpd.GeoDataFrame,
    boundaries: gpd.GeoDataFrame | None = None,
) -> gpd.GeoDataFrame:
    """Spatially assign predictions to regions and attach per-region risk counts."""
    required_fields = {"location", "risk_type", "risk_score", "risk_level", "geometry"}
    missing_fields = required_fields - set(predictions.columns)
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Predictions are missing regional aggregation fields: {missing}.")
    if predictions.crs is None:
        raise ValueError("Predictions must declare a coordinate reference system.")

    regions = load_admin_regions() if boundaries is None else boundaries.copy()
    if regions.crs is None:
        raise ValueError("Administrative boundaries must declare a coordinate reference system.")
    if "region_name" not in regions.columns:
        raise ValueError("Administrative boundaries must contain a region_name field.")
    if regions.crs.to_epsg() != 4326:
        regions = regions.to_crs("EPSG:4326")
    if predictions.crs.to_epsg() != 4326:
        predictions = predictions.to_crs("EPSG:4326")

    joined = gpd.sjoin(
        predictions[["location", "risk_type", "risk_score", "risk_level", "geometry"]],
        regions[["region_name", "geometry"]],
        how="left",
        predicate="within",
    )
    assigned = joined.dropna(subset=["region_name"])

    summary_rows = []
    for region_name, group in assigned.groupby("region_name"):
        mean_score = float(group["risk_score"].mean())
        if mean_score < 0.40:
            regional_risk_level = "LOW"
        elif mean_score < 0.70:
            regional_risk_level = "MEDIUM"
        else:
            regional_risk_level = "HIGH"

        summary = {
            "region_name": region_name,
            "location_count": len(group),
            "average_risk_score": mean_score,
            "regional_risk_level": regional_risk_level,
        }
        summary.update(
            {f"{level.lower()}_count": int(group["risk_level"].eq(level).sum()) for level in RISK_LEVELS}
        )
        summary.update(
            {f"{risk_type}_count": int(group["risk_type"].eq(risk_type).sum()) for risk_type in RISK_TYPES}
        )
        summary_rows.append(summary)

    regional_summary = pd.DataFrame.from_records(summary_rows)
    result = regions.merge(regional_summary, on="region_name", how="left")
    count_fields = ["location_count"]
    count_fields.extend(f"{level.lower()}_count" for level in RISK_LEVELS)
    count_fields.extend(f"{risk_type}_count" for risk_type in RISK_TYPES)
    result[count_fields] = result[count_fields].fillna(0).astype(int)
    result["regional_risk_level"] = result["regional_risk_level"].fillna("NO DATA")

    return gpd.GeoDataFrame(result, geometry="geometry", crs=regions.crs)
