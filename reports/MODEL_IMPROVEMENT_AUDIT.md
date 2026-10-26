# Model Improvement Audit — Data Quality, Leakage, and Optimization

**Audit date:** 2026-10-24
**Decision:** Training is blocked. The saved results are exploratory IFI-association experiments, not verified flood-occurrence performance.

This audit is read-only with respect to existing datasets and models. No model was deserialized, trained, or evaluated, and no legacy artifact was overwritten.

## Repository and preservation

The audit began on branch `ml-model` at HEAD `f0ef543708c5083a5e7dcd0da0311ba665f05a89`. Existing modifications and untracked files were preserved. The only new file from this audit is this report; no source code, dataset, model, or earlier report was modified.

## Experiments are distinct

| Experiment | Dataset and labels | Model | Split and reported sample sizes | Provenance/reproducibility |
|---|---|---|---|---|
| v1 | Local `data/processed/real_flood_dataset.csv`; 559 sampled district-days, with `flood_risk` positive for selected IFI event-start associations and sampled negative for inventory non-matches. Rows are limited to five Maharashtra districts and June–September. | The untracked `models/real_flood_v1.pkl` statically contains a calibrated scikit-learn pipeline with `LogisticRegression`, consistent with the untracked JSON/Markdown report. | Report says 2000–2018 training (360 rows; 183 positive, 177 negative) and 2019–2023 test (199 rows; 105 positive, 94 negative). | The dataset and report agree on row counts, labels, dates, and metrics, and the artifact timestamps are close. But no model/dataset checksums or run identifier bind them. The current v1 trainer expects `label_value` plus contract metadata, whereas this legacy CSV has `flood_risk` and no contract columns. The historical score is not reproducible through the current trainer. |
| v2 | Tracked `data/processed/real_flood_dataset_v2.csv`; 12,316 June–September district-days, 283 positive IFI event starts and 12,033 inventory non-matches. | Tracked `models/real_flood_v2.pkl`; static strings indicate `RandomForestClassifier`, consistent with the v2 report metadata. | Report says 2000–2018 training (10,217; 178 positive, 10,039 negative) and 2019–2023 test (2,099; 105 positive, 1,994 negative). | The model metadata/report identify the same dataset path, target and split, but no checksums bind model, data, and report. The current v2 trainer also requires contract fields missing from this legacy table. Do not load the pickle or claim an independently reproduced score. |

The v1 and v2 experiments have different sampling frames, class prevalence, target construction, and models. Their scores are not a comparable before/after pair.

## Historical report metrics (not independently reproduced)

These values are transcribed from the saved reports only. They are not verified flood-prediction metrics.

| Experiment/model | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Confusion matrix `[[TN, FP], [FN, TP]]` |
|---|---:|---:|---:|---:|---:|---:|---|
| v1 Logistic Regression | 0.678 | 0.656 | 0.819 | 0.729 | 0.783 | 0.794 | `[[49, 45], [19, 86]]` |
| v1 all-positive majority baseline | 0.528 | 0.528 | 1.000 | 0.691 | 0.500 | 0.528 | `[[0, 94], [0, 105]]` |
| v2 Random Forest | 0.527 | 0.082 | 0.829 | 0.149 | 0.745 | 0.158 | `[[1019, 975], [18, 87]]` |
| v2 all-negative majority baseline | 0.950 | 0.000 | 0.000 | 0.000 | 0.500 | 0.050 | `[[1994, 0], [105, 0]]` |

The v1 test positive prevalence is 105/199 = 52.8%, reflecting its approximately balanced negative sampling, not the prevalence among all district-days. Its report's paired bootstrap interval for F1 improvement over the all-positive baseline crosses zero (approximately -0.020 to 0.095).

The v2 test positive prevalence is 105/2,099 = 5.0%. The report gives PR-AUC 0.158 versus the 0.050 prevalence baseline and high recall at very low precision. Its majority baseline has high accuracy only because it predicts every row negative. The v2 report's bootstrap says its ROC-AUC exceeds the chance baseline on this selected label sample; this does not establish observed-flood accuracy.

## Label and source audit

- `flood_risk` in these legacy tables is an IFI inventory-event association, not an independently verified flood-occurrence target. An IFI non-match means only no match in the chosen inventory and rule; it cannot establish no flood occurred.
- The v1 sampled negatives are selected from dates not blocked by known event windows. The v2 table includes all June–September dates outside state-filtered event windows. Neither establishes complete observation coverage for flood-free labels.
- Four records remain geographically inconsistent: `UEI-IMD-FL-2003-0077`, `UEI-IMD-FL-2006-0088`, `UEI-IMD-FL-2006-0089`, and `UEI-IMD-FL-2018-0067` list Nagpur/LGD 484 but Odisha/state code 21. The v1 CSV contains them as positive rows; all are in its training period. The v2 and v3 CSVs contain corresponding Nagpur date rows as zero. These v2/v3 values are not evidence that the records are valid non-matches. The source conflict is unresolved, so these rows must be unknown/ineligible pending authoritative clarification.
- Same-day and forward-window targets are distinct. The v3 table retains `flood_risk` (event start at *t*, *t+1*, or *t+2*) and `same_day_flood_risk` separately; 511 null same-day values must remain unknown, not be converted to zero.

The Phase 12 contract requires explicit target specification, inventory snapshot, matching-rule version, evidence, district identity, label status, and independent training/evaluation eligibility. The legacy v1/v2/v3 CSV schemas do not provide those fields. Existing tests confirm that `flood_risk` and `event_ueis` cannot substitute for the contract. Training is therefore blocked; do not infer provenance or alter labels to pass the gate.

## Leakage and split findings

### Corrected in the current training code

- `FoldAwareRainfallAnomaly` replaces the stored anomaly feature inside each estimator pipeline. Its monthly reference is fit on that fold's training rows only; validation-period rainfall cannot alter the fitted means. Months with fewer than two finite training observations use the fold-wide training mean; if no finite training rainfall exists, fitting fails. This is a row-based reference, not a new full-series climate normal; the v1 balanced sample is especially unsuitable for estimating climatology and remains blocked by the label contract.
- The anomaly is now defined as previous-day (`t-1`) rainfall minus the climatology for the observation month. This preserves the monthly anomaly interpretation but, on the first day of a month, intentionally uses the observation-month climatology rather than the previous calendar month's climatology. It avoids adding date or split identifiers to the model feature matrix.
- v2 model-selection and threshold OOF splits now use expanding chronological year blocks with four warm-up years; v3 core CV and threshold OOF use the same forward-chaining approach. OOF threshold selection scores only years actually held out after warm-up. v1's existing expanding-window CV also uses the fold-aware anomaly transformer.
- Imputation, scaling, and categorical encoding remain inside the estimator pipeline and are fit separately within each training fold. Rainfall window features continue to use only observations through day *t-1*.

The checked-in v1/v2 reports remain historical reports from the old feature and validation implementation. They were not regenerated, and their results do not reflect these corrections.

### Still guarded or unresolved

- The model feature lists exclude target, event-ID, and split-time identifiers. Both local legacy CSVs have unique `(lgd_code, date)` rows. Event windows are expanded when excluding negative candidates; no selected source event's three-day-buffered interval crossed the 2018/2019 boundary in the local inventory audit.

1. **The final test period is no longer fresh across the project:** 2019–2023 was scored in both v1 and v2 reports (and later reported as a second look in v3). The code's historical test window remains in place, but it must not be treated as new independent evidence.
2. **Only five districts are represented in both train and test:** this tests later-year association within those same districts, not geographic generalization to unseen districts. Grouping complete calendar years is useful for preventing within-year row mixing, but only expanding splits match a future-year forecasting deployment.
3. **The unresolved conflict rows and unsupported negatives undermine the target itself:** correcting preprocessing or model choice cannot repair an ambiguous positive or make an inventory non-match a verified flood absence.

The new fold-aware feature calculation and split helper have unit coverage, but no trainer, builder, or evaluation was run in this phase. These code changes do not validate the labels or refresh the saved metrics.

The training data includes the same selected districts as the test data. The historical year split and zero exact district-day/event-ID overlap are useful safeguards, but do not remedy source-label validity or repeated test-period use. The current fold-aware pipeline addresses feature-reference leakage in new validation runs; it does not retroactively correct the old reports.

## Highest-impact actions, ranked

1. **Resolve/replace labels before optimizing:** obtain authoritative IFI field semantics or record-level corrections for the four conflicts; retain them as unknown until resolved. For IFI-association analysis, create a separate target-specific label artifact with snapshot checksum, versioned matching rule, source references, and explicit eligibility. For actual flood prediction, obtain independently observed flood outcomes and defensible negative-coverage evidence.
2. **Use the corrected fold-aware pipeline for future validation:** it replaces existing precomputed anomaly values at fit/transform time and recalculates fold-specific monthly references. Do not score using the historic reports as though they reflect this pipeline.
3. **Use strictly forward-chaining validation and preserve a genuinely unused test:** the current v2/v3 search helpers now form later-year validation blocks. Tune and set thresholds only within training-period folds and validation before the test boundary. Reserve a future period or a predeclared district-held-out set that has not been inspected for model choice; do not reuse 2019–2023 as fresh evidence.
4. **Compare on an identical, explicitly eligible row set:** use the same split, labels, feature set, and missing-row policy for a majority baseline, Logistic Regression, Random Forest, and (XGBoost is installed locally) gradient boosting. Report class prevalence, PR-AUC baseline, confusion matrix, and uncertainty. Do not run this comparison until the contract and scientific target are adequate.

## Tests and reproduction

Ran the focused label-gate, v2 split/leakage, rainfall-feature, and new fold-aware temporal-feature tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q \
  tests/test_label_contract.py \
  tests/test_real_data_v2.py \
  tests/test_real_data_v3.py \
  tests/test_real_data_features.py \
  tests/test_temporal_features.py
```

Result: **97 passed**. These validate the fold-aware feature/split code, contract, and existing safeguards; they do not validate IFI source truth or reproduce either historical model report.

There is **no safe, reproducible command for the saved accuracy reports at present**. The current trainers require metadata absent from the legacy datasets and are training/output-writing commands, not read-only evaluation commands. Do not run the builders or trainers to reproduce the historic figures; do not deserialize the model artifacts for this audit.

## Required evidence before an improvement run

1. An authoritative IFI field definition, erratum, or provider clarification resolving the State/State_Codes versus Districts/District_LGD_Codes conflict; no precedence is assumed here.
2. A separately versioned, target-specific label table bound to a checksummed inventory snapshot and matching-rule version. Unknown/ambiguous records (including the four conflicts until resolved) must remain null and ineligible; event IDs must be target-specific.
3. For an IFI-association experiment, a defensible scope statement that results predict inventory association only. For flood-occurrence prediction, an independent observation source with verified spatial and temporal coverage, observation-quality metadata, and evidence supporting both positive and negative labels.
4. A fold-safe rainfall feature pipeline, strict chronological validation, and a final holdout not previously used in project-level model selection.
5. A reproducibility manifest linking exact dataset/model/report checksums, code revision, target, feature definitions, split indices/years, parameters, and thresholds.

Until these conditions are met, no improved model or before/after performance claim is scientifically justified.
