# ClimateSense AI GIS Module

## Purpose

The GIS module will turn climate-risk predictions and geographic coordinates into a clear spatial view. This foundation defines the prediction data contract and planned visualization direction; it does not implement or render a map yet.

## Expected input format

Predictions are expected as a JSON array with one object per location. Each object contains:

| Field | Type | Description |
| --- | --- | --- |
| `location` | string | Human-readable place name |
| `latitude` | number | Decimal latitude in WGS 84 coordinates |
| `longitude` | number | Decimal longitude in WGS 84 coordinates |
| `risk_type` | string | One of `flood`, `drought`, `heatwave`, or `air_quality` |
| `risk_score` | number | Normalized score from 0.0 (lower risk) to 1.0 (higher risk) |
| `risk_level` | string | `LOW`, `MEDIUM`, or `HIGH`, derived from the score |

For consistency in demonstrations, the proposed bands are LOW below 0.40, MEDIUM from 0.40 to below 0.70, and HIGH from 0.70 through 1.00. The GIS module should validate incoming records and confirm that score and level agree before visualization.

`data/sample_predictions.json` contains nine illustrative Indian locations. **All records are mock/demo data only, not live observations, official forecasts, or validated model output.**

## Folder structure

```text
gis/
├── data/
│   ├── sample_predictions.json
│   └── india_admin1_simplified.geojson
├── src/
│   ├── data_loader.py
│   ├── geo_processor.py
│   ├── regional_processor.py
│   ├── risk_map.py
│   └── pipeline.py
├── output/
│   ├── climate_risk_map.html
│   ├── predictions.geojson
│   └── regional_risk.geojson
├── requirements.txt
└── README.md
```

`src/` contains the data loading, geospatial processing, regional aggregation, map rendering, and pipeline modules. `output/` contains generated map and GeoJSON artifacts.

## Receiving ML predictions

The ML module should export a JSON file conforming to the input contract above. The pipeline accepts a replaceable prediction file path, so ML can write its results to a shared file location without changes to the GIS processing or map code. For example, from the repository root:

```bash
python gis/src/pipeline.py --predictions /path/to/ml_predictions.json
```

If `--predictions` is omitted, the mock sample file is used. `--boundaries` and `--output-dir` can also be supplied. This integration is file-based; it does not add an API or modify the ML, backend, or frontend modules.

## Regional GIS layer

The GIS module spatially joins prediction points to India state and union-territory polygons, then exports per-region prediction counts, risk-level counts, risk-type counts, mean risk score, and a regional risk level. The level is derived from the mean score using the same LOW (< 0.40), MEDIUM (0.40 to < 0.70), and HIGH (>= 0.70) bands. Regions without matched predictions remain in the output as `NO DATA`.

`data/india_admin1_simplified.geojson` contains 36 simplified ADM1 state/UT polygons. Source: geoBoundaries `gbOpen` India ADM1, boundary year 2011, from the DataMeet India community / Election Commission of India. Licensed under Creative Commons Attribution 2.5 India (CC BY 2.5 IN); source metadata: <https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/>. These are administrative reference boundaries, not a definitive treatment of disputed borders. Regional matching uses point-in-polygon spatial joins; predictions that fall outside the supplied boundary data are not included in regional aggregates.

## Final pipeline outputs

The pipeline validates the prediction JSON, creates WGS84 point features, joins them to regional boundaries, and writes:

- `output/climate_risk_map.html`: interactive Folium map with regional risk polygons, prediction markers, summaries, and risk-type filtering.
- `output/predictions.geojson`: point features with the original prediction attributes.
- `output/regional_risk.geojson`: state/UT polygons with aggregated prediction counts and risk summaries.

The map uses OpenStreetMap tiles and requires an internet connection to display the basemap in a browser.

## Planned visualization approach

The interactive Folium map centers and fits to the prediction extent. Risk-level markers and state/UT polygons distinguish local and regional risk; popups and tooltips show location, risk type, score, level, and regional aggregates. Map labels and boundaries remain legible, with clutter kept low. Risk colors are accessible and distinct: muted green for LOW, amber for MEDIUM, and muted orange-red for HIGH.

## Visual design direction

The GIS experience will follow ClimateSense AI's premium environmental identity: warm beige or cream map surroundings, forest and sage greens, muted olive accents, and clean off-white information surfaces with subtle borders and restrained shadows. Typography and data presentation should feel minimal and professional. Green and earth tones establish the visual language, while harmonious warning colors preserve clear, accessible risk distinctions.
