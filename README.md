# ClimateSense AI

ClimateSense AI is an AI-powered climate-risk assessment platform. This repository contains the Member 1 data collection, validation, and preprocessing workflow for the initial flood-risk MVP.

## Data preprocessing branch
This branch is dedicated to the data pipeline work for the preprocessing module.

## Reproduce the preprocessing pipeline

```bash
python -m src.prepare_data
```

This command downloads the climate data from NASA POWER, validates it, cleans it, engineers rainfall features, and writes the final processed dataset to `data/processed/delhi_climate_daily_processed.csv`.

## Key outputs
- Raw data: `data/raw/nasa_power_delhi_daily.csv`
- Processed dataset: `data/processed/delhi_climate_daily_processed.csv`
- Metadata: `data/metadata/`
- Quality report: `reports/climate_data_quality_report.md`

## Important scientific note
The MVP climate dataset contains validated weather and climate observations, but no authoritative flood-event target dataset was identified within the selected data sources. The target remains unavailable, and no flood labels were fabricated.
