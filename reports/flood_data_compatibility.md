# Flood Data Compatibility Report

## Climate input

- File: `data/processed/delhi_climate_daily_processed.csv`
- Rows: 366 daily observations, 2024-01-01 through 2024-12-31, all unique dates
- Location: `Delhi`; one NASA POWER point at latitude 28.6139, longitude 77.2090
- Duplicate rows: 0; missing values in source file: 0; no target column

## Candidate checks

| Dataset | 2024 temporal match | Delhi spatial match | Result |
| --- | --- | --- | --- |
| Copernicus CEMS Global Flood Monitoring (GFM), 20 m Sentinel-1 observed flood extent | Yes. STAC point/date search returned 269 scene items across 110 UTC dates. | Yes at the exact point for scene footprints; pixel value must still be checked. | Pixel samples: 50 distinct dates had value 0, zero had value 1, and 219 scene samples were 255/no-data. A scene is an overpass snapshot, not full-day coverage. Urban-area false negatives and excluded/no-data pixels are documented. No daily event target can be constructed. |
| NASA OPERA DSWx-HLS, 30 m dynamic surface water | Yes. CMR point/date search returned 168 granules in 2024. | Yes, granule geometry intersects the point. | Surface water is not itself a validated flood-event label. No flood labels assigned. |
| CWC Flood Forecast portal | A documented/open historical daily 2024 record was not verified through the public interface inspected. | The portal is station-based; a river gauge is not the same location/phenomenon as city-point inundation. | Requires station history, coordinates, official thresholds, and a separately defined gauge target. Not joined. |
| NASA Global Flood Database v1 | No. Dataset ends in 2018. | Global mapped footprints, but dates do not overlap. | Cannot label 2024. |

## GFM point-level measurement details

The GFM STAC query used the exact coordinate (77.209, 28.6139) and the 2024 UTC interval. Each returned `ensemble_flood_extent` raster was sampled at that coordinate through the EODC COG point service. The output uses 1 for a flood pixel, 0 for a no-flood pixel, and 255 for no-data. The query returned 269 items, 110 distinct UTC dates, 50 distinct dates with at least one value 0, no value 1, and 219 item samples with value 255. A spot check of ten valid-zero dates found exclusion-mask 0, advisory-flags 0, and likelihood below 50.

The source dataset describes the time of each satellite acquisition. A valid 0 establishes no mapped flood at the sampled point and acquisition instant only. It does not establish that no flood occurred elsewhere in Delhi or at any other time during that climate date. No GFM acquisition or no-data value is unknown, not non-flood.

## Daily join accounting

- GFM items with spatial/time overlap: 269 scene items.
- Distinct overpass dates with a valid observed no-flood pixel: 50.
- Distinct overpass dates with a flood pixel at the climate point: 0.
- Climate dates with no valid point-level GFM classification: 316 of 366 (including no acquisition and no-data).
- Valid daily `flood_event` labels: 0 of 366. The 50 instantaneous non-flood classifications are insufficient to mark an entire day as `0`.
- Daily records left unknown: 366 of 366. There is no positive pixel detection to label `1`, and negative instantaneous readings do not establish full-day negatives.

## Decision

Do not create a daily `flood_event` target, `data/processed/delhi_flood_ml_dataset.csv`, or `src/create_flood_labels.py` from these products. Keep the original climate dataset unchanged. Candidate sources, definitions, and links are recorded in [FLOOD_DATASET_INFO.md](../data/metadata/FLOOD_DATASET_INFO.md); data needed to proceed is in [DATA_LIMITATION.md](DATA_LIMITATION.md).