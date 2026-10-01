# Backend ML Contract

## Prediction Functions

`src.predict.predict_risk(input_data, model_path=..., location=...)` remains the default demo API. It accepts one mapping or a pandas DataFrame containing `rainfall`, `temperature`, `humidity`, `pressure`, and `wind_speed` (the CSV wrapper also recognizes common climate aliases). It returns one JSON-serializable prediction object for a mapping or one-row input, or a list for a multi-row DataFrame. Every response includes `data_notice: "DEMO ONLY — NOT REAL CLIMATE PERFORMANCE"` unless the artifact supplies a more specific notice. This synthetic model is not evidence of real-world flood prediction.

Use `src.real_predict.predict_real_risk(district_lgd, rainfall_history, prediction_date, model_path="models/real_flood_v2.pkl")` to opt in to the real v2 model. `district_lgd` must be one of `482` (Mumbai), `484` (Nagpur), `490` (Pune), `497` (Thane), or `499` (Washim). `rainfall_history` is a list of `{ "date": "YYYY-MM-DD", "mm": number }` objects or a DataFrame with `date` and `mm` columns. Rainfall must be finite, nonnegative, daily, unique, and complete from `2000-05-02` through the day before `prediction_date`. Values for the prediction day or later are ignored; the model never uses them. The full history is required to reproduce the v2 `days_since_rain_gt20mm` feature as well as its 1/3/7/14/30-day windows. Gaps and insufficient history raise `ValueError`.

The output fields are `district`, `district_lgd`, `prediction_date`, `probability`, `predicted_flag`, `risk_band`, `risk_band_status`, `threshold`, `model`, `model_version`, and `label`. The label is `REAL DATA - ERA5 reanalysis rainfall`. Risk bands are explicitly **provisional**: High when probability is at least the frozen model threshold; Medium when it is at least half that threshold; otherwise Low. No independently selected training-year band cut points are stored in the existing artifact, so these bands are not presented as calibrated categories.

## Example

The example assumes `rainfall_history` was populated with every day from `2000-05-02` through the day before the prediction date; do not send only the abbreviated sample rows below to the function.

```python
from src.real_predict import predict_real_risk

result = predict_real_risk(
    district_lgd=482,
    rainfall_history=[
        {"date": "2000-05-02", "mm": 0.0},
        # Include every daily record through 2024-07-13.
        {"date": "2024-07-13", "mm": 8.4},
    ],
    prediction_date="2024-07-14",
)
```

Example response shape:

```json
{
  "district": "Mumbai",
  "district_lgd": 482,
  "prediction_date": "2024-07-14",
  "probability": 0.42,
  "predicted_flag": true,
  "risk_band": "High",
  "risk_band_status": "provisional",
  "threshold": 0.3352925985872756,
  "model": "RandomForest",
  "model_version": "real_flood_v2",
  "label": "REAL DATA - ERA5 reanalysis rainfall"
}
```

## Rainfall Retrieval and Limits

Fetch rainfall for the requested LGD district from Open-Meteo's Historical Weather API using ERA5 (`models=era5`, daily `precipitation_sum`, UTC). Request only dates strictly before the prediction date, and retain a complete cached daily series from `2000-05-02` so the history-dependent features match training. The v2 model averages three selected effective ERA5 grid cells per district; ERA5 is reanalysis, not observed station rainfall. Do not substitute prediction-day or future rainfall.

The model was trained on IFI-Impacts event labels for only five Maharashtra districts and June-September records. On the previously scored 2019-2023 period, precision was approximately 0.08 (recall approximately 0.83); the high false-alert rate and incomplete event inventory limit operational use. This result is not a fresh independent test and must not be represented as a national flood forecast. The artifact and v2 dataset are required for inference; regenerating the model requires the v2 training pipeline and source inputs documented in `data/real/SOURCES.md`.