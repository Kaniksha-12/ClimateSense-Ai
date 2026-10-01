"""Run the complete prediction-to-GIS-output pipeline."""

import argparse
from pathlib import Path

from data_loader import DEFAULT_DATA_PATH, load_predictions
from geo_processor import export_geojson, to_geodataframe
from regional_processor import (
    DEFAULT_BOUNDARY_PATH,
    aggregate_predictions_by_region,
    load_admin_regions,
)
from risk_map import create_risk_map


DEFAULT_OUTPUT_DIRECTORY = Path(__file__).resolve().parent.parent / "output"


def run_pipeline(
    predictions_path: str | Path = DEFAULT_DATA_PATH,
    boundary_path: str | Path = DEFAULT_BOUNDARY_PATH,
    output_directory: str | Path = DEFAULT_OUTPUT_DIRECTORY,
) -> dict[str, Path]:
    """Validate predictions, spatially process them, and write GIS artifacts."""
    predictions = load_predictions(predictions_path)
    prediction_points = to_geodataframe(predictions)
    boundaries = load_admin_regions(boundary_path)
    regional_risk = aggregate_predictions_by_region(prediction_points, boundaries)
    risk_map = create_risk_map(
        prediction_points,
        boundary_path=boundary_path,
        regional_data=regional_risk,
    )

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs = {
        "map": output_directory / "climate_risk_map.html",
        "predictions": output_directory / "predictions.geojson",
        "regions": output_directory / "regional_risk.geojson",
    }
    risk_map.save(str(outputs["map"]))
    export_geojson(prediction_points, outputs["predictions"])
    export_geojson(regional_risk, outputs["regions"])
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ClimateSense AI GIS outputs from ML predictions.")
    parser.add_argument(
        "--predictions",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="ML prediction JSON file using the documented GIS input schema.",
    )
    parser.add_argument(
        "--boundaries",
        type=Path,
        default=DEFAULT_BOUNDARY_PATH,
        help="State/UT boundary GeoJSON file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Directory for generated HTML and GeoJSON outputs.",
    )
    arguments = parser.parse_args()
    for artifact, path in run_pipeline(
        predictions_path=arguments.predictions,
        boundary_path=arguments.boundaries,
        output_directory=arguments.output_dir,
    ).items():
        print(f"{artifact}: {path}")


if __name__ == "__main__":
    main()
