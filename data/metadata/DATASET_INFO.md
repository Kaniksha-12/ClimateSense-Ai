# ClimateSense AI Dataset Information

## 1. Dataset name
Delhi daily climate observations for ClimateSense AI (NASA POWER extraction)

## 2. Source
NASA Langley Research Center POWER Project

## 3. Official URL
https://power.larc.nasa.gov/

## 4. Geographic coverage
- Location: Delhi, India
- Coordinates: latitude 28.6139, longitude 77.2090
- Coverage type: point extraction for a single city-level location

## 5. Date range
2024-01-01 to 2024-12-31

## 6. Resolution
- Temporal resolution: daily
- Spatial resolution: point-based daily extraction for one coordinate pair

## 7. Variables
- rainfall_mm
- temperature_c
- relative_humidity_pct
- wind_speed_m_s
- surface_pressure_kpa
- latitude
- longitude
- location
- derived rainfall features: previous_day_rainfall_mm, rain_3day_mm, rain_7day_mm, rainfall_anomaly_mm

## 8. Units
- rainfall_mm: millimetres per day
- temperature_c: degrees Celsius
- relative_humidity_pct: percent
- wind_speed_m_s: metres per second
- surface_pressure_kpa: kilopascals
- latitude/longitude: decimal degrees

## 9. Missing-value handling
Missing numeric values were filled with median values for their respective columns before validation. No rows were silently dropped unless they contained malformed date or invalid geographic coordinates.

## 10. Cleaning steps
1. Load raw file
2. Standardize column names
3. Parse dates to datetime values
4. Remove exact duplicates on date + location + coordinates
5. Sort by time
6. Fill missing numeric values with medians
7. Validate geographic coordinates and climate ranges
8. Save cleaned dataset

## 11. Feature engineering
The final processed dataset includes:
- previous_day_rainfall_mm: rainfall from the previous day only
- rain_3day_mm: trailing three-day rainfall total including the current day
- rain_7day_mm: trailing seven-day rainfall total including the current day
- rainfall_anomaly_mm: rainfall minus the previous 7-day rolling mean

These features are derived using only historical values available at the same date, preventing future-data leakage.

## 12. Target methodology
No validated flood-event or flood-impact dataset was identified for this location/date range from the selected authoritative sources. The dataset therefore does not contain a supervised target column such as flood_event.

This is intentional and scientifically defensible. Creating a flood label from rainfall alone would be a proxy that has not been validated against real flood observations.

## 13. Limitations
- Dataset is single-location and not yet district-level or pan-India coverage
- No flood target is available, so supervised flood-risk model training is not yet possible
- This is a climate observations dataset and not a flood-event dataset

## 14. Final processed dataset path
data/processed/delhi_climate_daily_processed.csv
