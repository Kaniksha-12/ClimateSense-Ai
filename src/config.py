from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
REPORTS_DIR = ROOT_DIR / "reports"

DEFAULT_RAW_DATASET = RAW_DIR / "nasa_power_delhi_daily.csv"
DEFAULT_PROCESSED_DATASET = PROCESSED_DIR / "delhi_climate_daily_processed.csv"
DEFAULT_SCHEMA_PATH = METADATA_DIR / "final_schema.json"
DEFAULT_REPORT_PATH = REPORTS_DIR / "climate_data_quality_report.md"
