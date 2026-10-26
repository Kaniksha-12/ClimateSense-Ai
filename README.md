# ClimateSense AI

ClimateSense AI is a research prototype for climate-data processing and flood-related analysis in India. It contains a Delhi climate-only preprocessing workflow, a synthetic/demo classifier, and exploratory Maharashtra rainfall/IFI event-association pipelines. It is **not a validated flood-occurrence prediction system**.

## Current data and label status

The Delhi daily dataset is NASA POWER weather data for one point in 2024. It has no flood target (`data/metadata/final_schema.json` sets `"target": null`), so it supports climate preprocessing only.

The separate Maharashtra research workflow combines ERA5 reanalysis rainfall with the India Flood Inventory-Impacts (IFI-Impacts). Its labels describe **IFI inventory event associations**, not independently observed flood occurrence:

- An IFI match means a source event matched a declared district/date rule.
- An IFI non-match means only that no matching record was found in the selected inventory snapshot and rule. It does not mean the district was flood-free.
- `flood_risk` in v3 is an event-start association on day *t*, *t+1*, or *t+2*. `same_day_flood_risk` is a separate same-day association; its 511 nulls must not be changed to zero without an approved reconstruction.
- Four IFI records conflict geographically: they list Nagpur/LGD 484 while recording Odisha/state code 21. They remain unresolved. See [the project completion and source-readiness report](reports/PROJECT_COMPLETION_REPORT.md).

The versioned, fail-closed validator in `src/label_contract.py` checks supplied target, status, provenance, and eligibility metadata for IFI association records. It does not independently verify source evidence or prove scientific validity. The current legacy CSV schemas do not contain its required metadata, so the v1-v3 real-data trainers reject those files rather than infer eligibility from `flood_risk` or `event_ueis`. Do not run real-data training until a separately reviewed, provenance-aware label artifact exists.

## Repository map

- `src/prepare_data.py`: climate-only NASA POWER download, validation, cleaning, feature generation, and output writing.
- `src/label_contract.py`: metadata consistency gate for target-specific labels.
- `scripts/build_real_dataset.py` and `scripts/build_real_dataset_v2.py`: legacy IFI/ERA5 dataset builders.
- `scripts/build_real_dataset_v3.py`: separate same-day and next-0-to-2-day IFI association targets.
- `scripts/build_real_dataset_v4.py`: expanded-district builder; its generated v4 dataset is not present.
- `src/real_training.py`, `src/real_training_v2.py`, `src/real_training_v3.py`: real-data trainer entry points with the IFI contract gate.
- `tests/`: preprocessing, demo, builder-helper, trainer-helper, prediction, and label-contract tests.
- `data/real/SOURCES.md`, `data/metadata/`, `reports/`: source notes, schemas, limitations, and historical evaluations.

The v1 and v3 processed real-data CSVs and several reports/models may exist as local untracked files. They are not necessarily part of the commit or a reproducible release. The v2 CSV and source inventory are tracked. Check `git status` before working with any local artifact.

## Sources and limitations

| Source | Local status | Scope and limitation |
|---|---|---|
| [IFI-Impacts, Zenodo record 16994648](https://zenodo.org/records/16994648) | Source CSV and record metadata are present under `data/real/ifi/`; [source notes](data/real/SOURCES.md) record checksums and CC BY-NC 4.0. | Inventory events are not a complete calendar of observed flood and non-flood days. Field precedence for the four conflicting records is unresolved. |
| [INDOFLOODS, Zenodo record 14584655](https://zenodo.org/records/14584655) | Not present locally; landing-page metadata was inspected, no data files downloaded. | Describes station discharge, official flood thresholds, events, and catchment attributes, but coverage is incomplete (the record says Ganga and Brahmaputra basins are not included). Confirm the applicable license, station/date coverage, quality/completeness, thresholds, and intended target before use. |
| [CWC hourly water-level dataset](https://nwdp.nwic.gov.in/en/dataset/river-water-level-telemetry-hourly-central-water-commission-cwc) | No observations or station metadata present locally; the page response inspected did not expose dataset details. | Station history, observed-vs-forecast meaning, quality flags, thresholds, coverage, and reuse terms remain unverified. |
| [CWC hourly discharge dataset](https://nwdp.nwic.gov.in/dataset/river-discharge-telemetry-hourly-central-water-commission-cwc) | No observations present locally; landing-page information was inspected, no data files downloaded. Its visible resource list names selected jurisdictions, not Maharashtra. | A gauge-stage or discharge target would be station-specific, not district-wide inundation. Verify station availability, observed date coverage, quality, thresholds, and reuse terms. |
| [Global Flood Database v1](https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1) | Not present locally; catalog documentation was inspected, no data downloaded. | Event maps cover selected events from 2000–2018 with water extent, duration, and clear-observation information. They do not provide complete daily negative coverage. |
| ERA5 via Open-Meteo | Rainfall caches and manifests are present locally; details are in [source notes](data/real/SOURCES.md). | Reanalysis rainfall is not observed station rainfall and cannot itself provide flood labels. |

The existing [Delhi flood-data research note](data/metadata/FLOOD_DATASET_INFO.md) describes intermittent satellite observations; they do not establish daily flood-free periods. No locally available source currently supports defensible nationwide or district-level flood-absence labels. A gauge-level threshold experiment may be considered only after station metadata, an approved threshold, observed values, quality/coverage, provenance, and reuse terms are verified.

## Setup

Use Python and the dependencies listed in `requirements.txt`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

No Python version range or lockfile is currently declared. The test suite was run in this workspace with Python 3.14.2.

## Tests

Run the repository test suite without writing bytecode or pytest cache files:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q
```

The suite includes synthetic demo tests. Passing tests validates implemented code paths; it does not verify IFI source truth, flood occurrence, or flood absence.

## Reproducible climate-only preprocessing

After reviewing the default output paths, run:

```bash
python -m src.prepare_data
```

This command may access NASA POWER when the raw file is missing or fails its checks. It writes the raw and processed climate CSVs, `data/metadata/final_schema.json`, and `reports/climate_data_quality_report.md`. It does **not** produce a flood target.

The IFI/ERA5 builders and real-data trainers are intentionally not presented as a currently validated end-to-end training workflow. Builders write dataset files, and v4 may fetch rainfall with `--fetch`; do not run them until output paths, source/rule provenance, the four conflicts, and label eligibility are reviewed. The real-data trainers require Phase 12 contract fields absent from the legacy CSVs.

## Reports and generated artifacts

- [Project completion and data-readiness report](reports/PROJECT_COMPLETION_REPORT.md)
- [Model improvement audit: label quality, leakage, and experiment readiness](reports/MODEL_IMPROVEMENT_AUDIT.md)
- [Data limitation report](reports/DATA_LIMITATION.md)
- [Flood data compatibility research](reports/flood_data_compatibility.md)
- Historical IFI/ERA5 evaluations: `reports/real_data_evaluation*.md` and `.json`. They describe legacy proxy-label experiments and must not be presented as verified flood-prediction performance.
- Generated datasets, models, caches, and reports are stored under `data/`, `models/`, and `reports/`; their presence does not imply that they are tracked or reproducible.

## Current decision and next steps

1. Keep legacy datasets unchanged and describe their targets only as IFI event associations.
2. Obtain authoritative IFI documentation or a traceable correction explaining how to handle the four state/district conflicts.
3. Approve a versioned association rule, bind a new separate label table to an exact IFI source snapshot, and reconstruct target-specific event references. Unknown or conflicting rows stay null and ineligible.
4. Consider observed-inundation or gauge-threshold targets only with suitable source evidence, quality information, coverage, and permitted use.
5. Reassess training eligibility and evaluation splits before any authorized model run. Do not report the existing proxy-label metrics as validated flood-occurrence prediction.
