# Flood Dataset Research

## Decision

No assessed source supports a complete daily `flood_event` target for the 366 NASA POWER observations at (28.6139, 77.2090), Delhi, during 2024. Copernicus GFM is the strongest event-observation candidate: its Sentinel-1 flood layer intersects the exact point and has 2024 acquisitions, but those are intermittent overpass snapshots. At the exact pixel, the 2024 query returned 50 distinct UTC dates with an explicit no-flood value, no flood-valued pixels, and unknown/no-data on the remaining 316 climate dates. A clear satellite snapshot at one instant cannot establish that the entire daily interval was flood-free. Therefore no daily target or joined ML dataset was created; the 50 snapshots must not be converted to daily zero labels.

See [the compatibility report](../../reports/flood_data_compatibility.md) and [the data limitation report](../../reports/DATA_LIMITATION.md) for candidate-by-candidate checks and required follow-up data.

## Candidate 1: Copernicus Global Flood Monitoring

- **Dataset:** Global Flood Monitoring (GFM), Copernicus Emergency Management Service (CEMS), Global Flood Awareness System.
- **Official collection:** [EODC GFM STAC collection](https://stac.eodc.eu/api/v1/collections/GFM)
- **Official documentation:** [GFM Product User Manual](https://extwiki.eodc.eu/en/GFM/PUM), [Product Definition Document](https://extwiki.eodc.eu/en/GFM/PDD), and [Copernicus GFM portal](https://global-flood.emergency.copernicus.eu/).
- **Scientific references:** The STAC collection cites https://doi.org/10.1109/IGARSS47720.2021.9554214 and https://doi.org/10.3390/rs14153673.
- **Coverage:** Global; catalog temporal extent starts 2015-01-01 and continues to present.
- **Resolution and variables:** 20 m Sentinel-1-derived observed flood extent, observed water extent, reference-water mask, exclusion mask, advisory flags, and likelihood layers. The STAC catalog exposes these as georeferenced raster assets.
- **Event definition:** The ensemble `Observed Flood Extent` layer maps pixels covered by floodwater from Sentinel-1 SAR backscatter. Permanent/reference water is treated separately. The documented binary flood layer uses 1 for observed flood, 0 for observed no flood, and 255 as raster no-data in the sampled assets.
- **Access/license:** The CEMS manual describes public access through STAC, REST APIs, WMS, and viewers. The STAC collection declares its license as `proprietary`; review the applicable CEMS/EODC terms before redistribution or deployment.
- **Delhi 2024 check:** A STAC time-and-point query returned 269 scene items spanning 110 UTC dates intersecting the exact climate coordinate. Sampling the `ensemble_flood_extent` COG at that coordinate returned 50 distinct dates with value 0, no dates with value 1, and 219 scene samples with value 255. Ten sampled zero dates also had exclusion-mask 0, advisory-flags 0, and likelihood values 13-21. These are instantaneous overpass observations, not daily coverage.
- **Matching method and limitation:** Query STAC with the climate coordinate and 2024 UTC interval, then sample the observed flood extent at the point using the EODC COG point service. Join by the overpass UTC date to the NASA POWER date. Missing scenes and no-data pixels remain unknown. Even a valid 0 only says no flood was mapped at the pixel at that overpass, not that no flood occurred at any time that day. The climate point is also not representative of all Delhi/NCR. The point-level query detected no positive flood pixel in 2024; this is not evidence that Delhi had no floods elsewhere.

## Candidate 2: NASA OPERA DSWx-HLS

- **Dataset:** OPERA Level-3 Dynamic Surface Water Extent from Harmonized Landsat-Sentinel-2, Version 1 (`OPERA_L3_DSWX-HLS_V1`).
- **Official catalog:** [NASA CMR collection metadata](https://cmr.earthdata.nasa.gov/search/collections.umm_json?short_name=OPERA_L3_DSWX-HLS_V1&provider=POCLOUD).
- **Coverage/resolution:** Global catalog extent, 30 m pixels, temporal metadata from 2016 onward; the catalog abstract describes validated observations beginning April 2023.
- **Observation definition:** Optical HLS imagery is processed into dynamic surface-water extent classifications and confidence/quality layers. This is a surface-water product, not a catalog of verified flood events; water presence alone is not proof of flooding.
- **Delhi 2024 check:** A NASA CMR point-and-time query returned 168 granules intersecting the Delhi coordinate during 2024.
- **Join decision:** Date and coordinate overlap, but its surface-water classification does not independently establish flood-event occurrence or complete daily negatives. No flood labels were derived from it. Optical cloud/observation gaps and the need to separate normal/permanent water from floodwater remain material limitations.

## Candidate 3: CWC Flood Forecast portal

- **Source:** Central Water Commission, Government of India, [Flood Forecast portal](https://ffs.india-water.gov.in/).
- **Coverage and variables:** The public service presents flood forecasts and river-station water-level/warning information. River stage at a named gauge is not equivalent to inundation at the ClimateSense point or to city-wide flooding.
- **Delhi 2024 check:** The publicly accessible portal/API inspection did not establish an openly downloadable, documented historical 2024 daily time series for a geolocated Delhi gauge. No historical records or station observations were joined.
- **What could make it usable:** Obtain the official 2024 timestamped stage series, station coordinates, station-specific warning/danger levels, and provenance. It could define a separately named gauge-threshold target, but should not be represented as observed urban inundation without independent validation.

## Candidate 4: NASA Global Flood Database v1

- **Dataset:** Global Flood Database v1, hosted in the [Google Earth Engine Data Catalog](https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1); event inventory based on Dartmouth Flood Observatory information and MODIS mapping.
- **Coverage/resolution:** 913 selected global events from 2000 through 2018, with nominal 250 m event flood maps.
- **Event definition:** Mapped maximum flood extent and duration for catalogued events, with permanent-water and clear-observation information.
- **Access/license:** Catalog access through Google Earth Engine; catalog states CC BY-NC 4.0.
- **Delhi 2024 check:** No temporal overlap; cannot label any 2024 date. Selected events are not a complete daily positive/negative record.

## Final labeling status

- Climate observations: 366, 2024-01-01 through 2024-12-31, one point, `Delhi`.
- GFM scene items intersecting the point: 269, across 110 UTC dates.
- Distinct dates with an explicit valid no-flood pixel at an overpass: 50. These are not daily no-flood labels.
- Positive GFM flood pixels at the exact point in the queried 2024 items: 0.
- Dates with no valid GFM flood classification at the point: 316 of 366.
- Valid daily `flood_event` labels: 0; daily flood status remains unknown for all 366 records.
- Final label dataset and label-generation script: not created because there is no valid daily target to emit.