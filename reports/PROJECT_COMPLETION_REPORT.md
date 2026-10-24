# ClimateSense AI — Completion and Data-Readiness Report

**Status: PARTIALLY COMPLETE; flood-occurrence training is blocked.**

This report records the repository inspection and validation completed on 2026-10-24. It does not certify scientific validity or a deployed flood-prediction model.

## What the project can demonstrate

- A climate-only preprocessing workflow for daily NASA POWER observations at one Delhi point. Its schema explicitly has no target (`data/metadata/final_schema.json`).
- A synthetic/demo ML pipeline. Demo metrics are not real Indian flood-prediction results.
- Exploratory Maharashtra rainfall/IFI event-association builders and historical evaluation artifacts.
- A fail-closed, versioned IFI-association metadata validator used at the v1-v3 trainer input boundaries.

The Phase 12 validator checks metadata consistency and caller-provided eligibility. It does not verify that referenced source records are authentic, that an inventory is complete, or that a label is scientifically valid. Existing legacy CSVs do not have the required contract fields and must not be made eligible by deriving provenance from `flood_risk` or blank event IDs.

## Data readiness and label decision

IFI-Impacts is available locally at `data/real/ifi/India_Flood_Inventory_v3.csv`. `data/real/SOURCES.md` records Zenodo record 16994648, file checksums, and CC BY-NC 4.0. Its inventory supports source-event association when a declared rule matches a record; a non-match does not establish that no flood occurred.

Four source records remain geographically conflicting:

| UEI | Start date | District/code fields | State fields |
|---|---|---|---|
| `UEI-IMD-FL-2003-0077` | 2003-09-01 | Nagpur / LGD 484 | Odisha / 21 |
| `UEI-IMD-FL-2006-0088` | 2006-08-01 | Nagpur / LGD 484 | Odisha / 21 |
| `UEI-IMD-FL-2006-0089` | 2006-09-01 | Nagpur / LGD 484 | Odisha / 21 |
| `UEI-IMD-FL-2018-0067` | 2018-08-14 | Nagpur / LGD 484 | Odisha / 21 |

The v2/v3 builder filters to Maharashtra-only events; v1 does not apply that same filter. This explains historical disagreement but is not authoritative evidence about which field is correct. Do not promote these four rows to positive or negative eligible labels until the IFI provider’s field semantics or a traceable correction resolves the conflict.

V3 keeps two proxy targets distinct:

- `same_day_flood_risk`: an IFI event start on date *t*.
- `flood_risk`: an IFI event start on date *t*, *t+1*, or *t+2*.

The 511 null same-day values represent rows positive for the forward-window target but not a same-day positive under the builder logic. They are not zeros. `event_ueis` may contain events from the full forward window; re-derive target-specific IDs from the pinned IFI source before using them as evidence.

### Local dataset inventory

| Artifact | Availability | Readiness |
|---|---|---|
| `data/processed/delhi_climate_daily_processed.csv` | Tracked climate-only dataset | No flood target. |
| `data/processed/real_flood_dataset_v2.csv` | Tracked legacy IFI/ERA5 dataset | Binary proxy labels; missing Phase 12 contract fields. |
| `data/processed/real_flood_dataset.csv` (v1) | Present as an untracked local artifact at inspection | Preserve as user work; not a verified release artifact; missing contract fields. |
| `data/processed/real_flood_dataset_v3.csv` | Present as an untracked local artifact at inspection | Preserve as user work; includes separate legacy targets and 511 same-day nulls; missing contract fields. |
| `data/processed/real_flood_dataset_v4.csv` | Absent | The builder exists, but no generated v4 output was found. |
| `data/real/era5/three_point/district_daily_rainfall.csv` and manifest | Present locally; ignored by Git | Weather/reanalysis inputs only, not flood observations. |

The local untracked status can change; check `git status` before relying on these files.

## Alternative source investigation

Landing-page/catalogue documentation was inspected on 2026-10-24. No external dataset files were downloaded and no API was called.

| Source | What its public page documents | Readiness for this project |
|---|---|---|
| [IFI-Impacts, Zenodo 16994648](https://zenodo.org/records/16994648) | IFI event inventory sourced from IMD, 1967–2023; release description mentions LGD codes; CSV assets and release history are listed. The local source notes report CC BY-NC 4.0. | Available locally for association reconstruction, but not complete daily flood/no-flood coverage; four geographic conflicts remain unresolved. |
| [INDOFLOODS, Zenodo 14584655](https://zenodo.org/records/14584655) | Landing page describes station discharge, flood thresholds, event times, peak level/discharge, catchments and associated files. It states Ganga and Brahmaputra basin data are not included and describes access for academic/research use. | Not present locally. No files were downloaded. Confirm the precise license, station/time coverage, data quality/completeness, and threshold semantics before reuse. Potentially relevant to a carefully scoped station-level target, not automatically a district target. |
| [CWC hourly water-level dataset](https://nwdp.nwic.gov.in/en/dataset/river-water-level-telemetry-hourly-central-water-commission-cwc) | The page response inspected exposed only NWIC contact information, not usable resource metadata. | Local data, license, stations, historical coverage, observation quality, and thresholds remain unverified. |
| [CWC hourly discharge dataset](https://nwdp.nwic.gov.in/dataset/river-discharge-telemetry-hourly-central-water-commission-cwc) | Landing page describes hourly station discharge observations and CSV/API resources. The visible list names Arunachal Pradesh, Jammu and Kashmir, Ladakh, Odisha, Sikkim, Uttarakhand, and West Bengal, with resource labels including 1970–2025 and 2026–2030; it does not show Maharashtra. | No data downloaded. The page does not establish station-level historical availability, data quality/completeness, thresholds, or license. Discharge exceedance is station-specific and cannot be generalized to district inundation. |
| [Global Flood Database v1](https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1) | Earth Engine catalog describes 913 selected flood events from 2000–2018, event extent/duration and clear-observation bands. | Not present locally and not downloaded. Event maps can inform case studies but do not establish complete daily negative coverage. Check Earth Engine access and reuse terms before use. |

No inspected local source provides defensible flood-free observations for the target districts and dates. The Delhi satellite notes describe intermittent overpasses and do not establish daily absence; ERA5 rainfall is not flood evidence.

## Validation performed

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q
```

Result: **122 passed in 59.23 seconds** using Python 3.14.2 and pytest 9.1.1. Tests include synthetic demo training and a legacy model prediction path; neither constitutes a new real-data training run or flood-target validation. No dataset builder, real-data trainer, or real-data evaluation was run.

No configured `pyproject.toml`, Ruff, mypy, or other lint/type-check configuration was found. No separate linter was run.

## Reproduction commands

Install declared Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q
```

Run the climate-only pipeline only after reviewing its output paths:

```bash
python -m src.prepare_data
```

That command can call NASA POWER if the raw input is missing or fails checks, and writes the processed climate CSV, schema, and quality report. It does not create a flood target. The real-data builders write datasets (v4 can fetch rainfall); do not run them until the matching rule, source provenance, label table, and output paths are separately approved. Real-data training is not justified with the existing legacy schemas.

## Files changed in this completion phase

- `README.md` — documents actual architecture, setup/tests, data/label limits, and safe commands.
- `reports/PROJECT_COMPLETION_REPORT.md` — records current readiness, sources, validation, and next steps.

No code, datasets, models, or prior reports were changed. Existing modified and untracked user files must remain outside any completion commit unless individually reviewed and explicitly requested.

## GitHub and remaining work

This report was drafted before the final documentation commit. Only the two documentation paths are in scope for that commit; pre-existing user changes must remain untouched. The local and upstream branch must be compared before a normal, non-force push.

Prioritized blockers:

1. Obtain authoritative IFI field definitions or provider clarification for `State`/`State_Codes` versus `Districts`/`District_LGD_Codes`; preserve the four records as unresolved meanwhile.
2. Define and version the exact IFI association rule, bind a new separate label artifact to a source snapshot/checksum, and reconstruct each target’s event references. Keep unknown/ambiguous records null and ineligible.
3. For a true flood-occurrence or flood-absence target, obtain independent observations and adequate spatial/temporal coverage; for gauge experiments, approve a station-specific threshold and verify station data quality/completeness and reuse terms.
4. Recompute splits and metrics only after the target and eligibility artifact pass review. Label any IFI-association results as exploratory association analysis, never verified flood-prediction accuracy.
