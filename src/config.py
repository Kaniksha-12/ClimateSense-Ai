from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
MODELS_DIR = ROOT_DIR / "models"
REPORTS_DIR = ROOT_DIR / "reports"
DEMO_DIR = DATA_DIR / "demo"

DEFAULT_RAW_DATASET = RAW_DIR / "nasa_power_delhi_daily.csv"
DEFAULT_PROCESSED_DATASET = PROCESSED_DIR / "delhi_climate_daily_processed.csv"
DEFAULT_SCHEMA_PATH = METADATA_DIR / "final_schema.json"
DEFAULT_REPORT_PATH = REPORTS_DIR / "climate_data_quality_report.md"
DEFAULT_DEMO_DATASET = DEMO_DIR / "synthetic_flood_demo.csv"
DEFAULT_MODEL_PATH = MODELS_DIR / "demo_flood_model.joblib"
DEFAULT_REPORTS_DIR = REPORTS_DIR
RANDOM_STATE = 42
DEFAULT_LOW_RISK_THRESHOLD = 0.35
DEFAULT_HIGH_RISK_THRESHOLD = 0.7
