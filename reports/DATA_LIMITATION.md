# Data Limitation: No Valid Delhi 2024 Daily Flood Target

## Finding

The climate dataset has 366 daily observations for one Delhi point (28.6139, 77.2090) in 2024. Research identified a strong, real event-observation candidate: Copernicus CEMS Global Flood Monitoring (GFM), which provides 20 m Sentinel-1 observed-flood rasters and timestamped scenes. At the exact climate coordinate, a query found 269 scene items over 110 UTC dates. Pixel samples showed 50 distinct dates with an explicit no-flood value, no flood-valued pixels, and 316 climate dates without a valid point classification.

GFM snapshots are not continuous daily observations. A value of 0 applies only to the exact pixel at the satellite overpass; it cannot show that a whole daily interval was flood-free. Value 255 is no-data, and absence of an acquisition is unknown. GFM documentation also warns that urban floods can be missed. The 2024 check therefore did not validate a usable daily `flood_event` target. These results do not establish that there were no floods elsewhere in Delhi or at other times.

NASA OPERA DSWx-HLS also has 168 granules intersecting this point during 2024, but it maps surface water, not independently verified flood events. NASA Global Flood Database v1 ends in 2018. The CWC Flood Forecast portal is station/river-stage focused; no documented open historical Delhi 2024 daily station series was verified during this check. Candidate details and official links are in [FLOOD_DATASET_INFO.md](../data/metadata/FLOOD_DATASET_INFO.md); exact match accounting is in [flood_data_compatibility.md](flood_data_compatibility.md).

All 366 daily flood statuses remain unknown. No synthetic labels, event dates, or measurements have been created.

## Required data to proceed

For a daily target at the existing point, obtain authoritative dated inundation observations that include:

- timestamps and a defined daily aggregation/timezone rule;
- georeferenced flood extent at the point or in a clearly defined Delhi/NCT study area;
- documented flood/no-flood classes and confidence/quality flags;
- observation-coverage flags or a sufficiently complete daily record, so missing scenes are not treated as negative;
- documentation of urban detection limits and validation, plus a license for intended use.

An official CWC 2024 time series could support a separate gauge-level target if it includes station coordinates, complete timestamps, quality flags, and official warning/danger thresholds. Such a target must be named and interpreted as a gauge-stage event, not city-wide inundation or flooding at the current NASA POWER point.

## Project impact

- `data/processed/delhi_climate_daily_processed.csv` remains unchanged.
- No `flood_event` daily labels or `data/processed/delhi_flood_ml_dataset.csv` were produced.
- No `src/create_flood_labels.py` was created because a defensible daily join is not available.
- Existing training code, the demo artifact, and its evaluation results remain untouched.
- No new model training or performance claims were made.