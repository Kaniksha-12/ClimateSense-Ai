# REAL DATA - ERA5 reanalysis rainfall

> IFI-Impacts event labels with ERA5 reanalysis rainfall; rainfall is not observed station data.

## Dataset and split

- Rows: 12316; positives: 283; negatives: 12033; majority accuracy baseline: 0.950.
- Train: 2000–2018 (10217 rows); test: 2019–2023 (2099 rows).
- Test classes: {'0': 1994, '1': 105}; dropped-event counts: `{"district_lgd_token_count_mismatch": 7, "end_before_start": 1, "ifi_event_rows_total": 6876, "missing_or_invalid_start_date": 1, "not_single_state_maharashtra": 5864, "unique_positive_district_start_dates": 283, "valid_selected_district_event_associations": 625}`.
- Selected model: RandomForest; threshold 0.335293, training OOF precision 0.031, recall 0.803.
- Features use rainfall through the day before event start; monthly rainfall means use training years only. Test years were used once after model selection and threshold freezing.

## Test results

Confusion matrix order: `[[TN, FP], [FN, TP]]`.

| Model | Accuracy | Balanced accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Confusion matrix |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| RandomForest | 0.527 | 0.670 | 0.082 | 0.829 | 0.149 | 0.745 | 0.158 | `[[1019, 975], [18, 87]]` |
| Logistic Regression | 0.689 | 0.615 | 0.085 | 0.533 | 0.147 | 0.665 | 0.120 | `[[1391, 603], [49, 56]]` |
| Majority class | 0.950 | 0.500 | 0.000 | 0.000 | 0.000 | 0.500 | 0.050 | `[[1994, 0], [105, 0]]` |

## Training CV and reliability

- LogisticRegression: ROC-AUC 0.778 ± 0.049; PR-AUC 0.107 ± 0.037.
- RandomForest: ROC-AUC 0.759 ± 0.044; PR-AUC 0.116 ± 0.038.
- XGBoost: ROC-AUC 0.762 ± 0.052; PR-AUC 0.112 ± 0.060.
- Test ROC-AUC 95% CI: [0.69795959280377, 0.7933144725374854]; recall 95% CI: [0.7545342771982116, 0.8985553109521188].
- Test Brier score: 0.18302.

### Calibration

| Probability bin | Rows | Mean predicted | Observed positive rate |
|---|---:|---:|---:|
| 0.1–0.2 | 319 | 0.156 | 0.016 |
| 0.2–0.3 | 519 | 0.258 | 0.013 |
| 0.3–0.4 | 390 | 0.341 | 0.038 |
| 0.4–0.5 | 261 | 0.445 | 0.038 |
| 0.5–0.6 | 292 | 0.552 | 0.072 |
| 0.6–0.7 | 176 | 0.647 | 0.102 |
| 0.7–0.8 | 58 | 0.741 | 0.207 |
| 0.8–0.9 | 84 | 0.858 | 0.202 |

### Per-district recall

| District | Positive test rows | Recall |
|---|---:|---:|
| Mumbai | 14 | 0.929 |
| Nagpur | 29 | 0.690 |
| Pune | 13 | 0.923 |
| Thane | 21 | 0.952 |
| Washim | 28 | 0.786 |

### Top 10 feature importances

- `numeric__rainfall_anomaly_vs_training_monthly_mean_mm`: 0.16499
- `numeric__rainfall_1d_total_mm`: 0.14835
- `numeric__rainfall_1d_max_daily_mm`: 0.13671
- `numeric__rainfall_3d_max_daily_mm`: 0.08819
- `numeric__days_since_rain_gt20mm`: 0.08066
- `numeric__rainfall_3d_total_mm`: 0.07726
- `numeric__rainfall_7d_max_daily_mm`: 0.06354
- `numeric__rainfall_7d_total_mm`: 0.04789
- `categorical__district_Pune (LGD 490)`: 0.03170
- `numeric__rainfall_14d_max_daily_mm`: 0.03159

## Verdict and limitations

The model's test ROC-AUC exceeds the majority baseline (0.5), with the paired 95% bootstrap interval for the AUC difference entirely above zero. The main weakness is low positive precision, so reaching the recall target produces many false alerts under the highly imbalanced all-negative-day sampling frame.

IFI-Impacts records are not a complete flood-observation calendar; eligible non-event days can include unreported floods. ERA5 is reanalysis, not observed station rainfall. Results cover five Maharashtra districts and June-September only; they are not a national operational flood forecast.
