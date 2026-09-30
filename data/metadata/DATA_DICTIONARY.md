# Data Dictionary

| Column | Meaning | Unit | Type | Source | Role |
|---|---|---:|---|---|---|
| date | Observation date | datetime | datetime64 | NASA POWER | Identifier |
| rainfall_mm | Daily total precipitation | mm/day | float | NASA POWER | Feature |
| temperature_c | Air temperature at 2 m | °C | float | NASA POWER | Feature |
| relative_humidity_pct | Relative humidity at 2 m | % | float | NASA POWER | Feature |
| wind_speed_m_s | Wind speed at 2 m | m/s | float | NASA POWER | Feature |
| surface_pressure_kpa | Surface pressure | kPa | float | NASA POWER | Feature |
| latitude | Latitude of point location | decimal degrees | float | NASA POWER / configuration | Identifier |
| longitude | Longitude of point location | decimal degrees | float | NASA POWER / configuration | Identifier |
| location | Human-readable location label | string | object | configuration | Identifier |
| previous_day_rainfall_mm | Rainfall on the previous calendar day | mm/day | float | Derived | Feature |
| rain_3day_mm | Three-day rolling rainfall total including current day | mm | float | Derived | Feature |
| rain_7day_mm | Seven-day rolling rainfall total including current day | mm | float | Derived | Feature |
| rainfall_anomaly_mm | Rainfall minus the previous 7-day mean | mm | float | Derived | Feature |

Notes:
- No target column is present because no validated flood-event dataset was available for this MVP.
- The processing pipeline prevents future-data leakage by using only historical values when creating derived rainfall features.
