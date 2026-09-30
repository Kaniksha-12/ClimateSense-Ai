# Sources

## Primary dataset
- Name: NASA POWER Daily Climate Data
- Organization: NASA Langley Research Center / POWER Project
- Official URL: https://power.larc.nasa.gov/
- Coverage: global point/region data; this project uses a Delhi, India point location
- Time coverage: 2024-01-01 to 2024-12-31
- Temporal resolution: daily
- Spatial resolution: point-based daily extraction at the selected coordinates
- File format: CSV after export, JSON from API before export
- Variables used: rainfall, temperature, relative humidity, wind speed, and surface pressure
- Licensing/access: publicly available through NASA POWER API; no login required for typical public access

## Flood target data status
- A validated flood-event dataset for the same location and date range was not identified from an authoritative source within the scope of this MVP.
- The final project dataset therefore contains climate features only and does not fabricate a supervised flood target.
- Additional flood-event or impact datasets would be required before a supervised flood-risk model can be trained.
