# ClimateSense AI

ClimateSense AI is a climate-risk dashboard foundation that brings conditions, prediction records, risk summaries, GIS status, and alerts into one interface. Conditions and risk summaries are demonstration data. The seeded prediction/alert are also explicitly identified as demo data; submitted predictions are persisted but are not represented as verified ML output.

## Architecture

- `frontend/`: React + Vite dashboard; one API service calls the FastAPI endpoints.
- `backend/app/routes/`: modular health, conditions, prediction, risk, alert, and GIS routes.
- `backend/app/models/`: shared Pydantic request/response contracts.
- `backend/app/db/`: SQLAlchemy engine, session dependency, and SQLite ORM records.
- `backend/app/services/`: prediction persistence, deterministic alerts, conditions/risk demos, and GIS boundary adapter.
- `backend/tests/`: API, database, alert, validation, CORS, and M1–M4 regression tests.

Member 4 owns the API, dashboard integration, local persistence, and delivery configuration. ML model work belongs to Member 2; GIS processing and GeoJSON production belong to Member 3.

## Requirements and local run

Requirements: Python 3.10+ and Node.js 20+ with npm. No `.env`, Docker, PostgreSQL server, authentication setup, or external service is needed for local development.

Start the backend in one terminal:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Start the frontend in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open the Vite URL printed in the terminal (default `http://localhost:5173`). The development proxy forwards `/api` to FastAPI at `http://127.0.0.1:8000` by default. FastAPI's OpenAPI UI and schema are at `/docs` and `/openapi.json`.

## Environment configuration

The backend works without environment variables. Optional settings:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | SQLite file at `backend/data/climatesense.db` | SQLAlchemy database URL |
| `CORS_ORIGINS` | Local Vite dev/preview origins | Comma-separated explicit browser origins; `*` is rejected |
| `VITE_BACKEND_URL` | `http://127.0.0.1:8000` | Vite development proxy target only |
| `VITE_API_BASE_URL` | Empty string (same-origin `/api`) | Browser API base for a deployed frontend/API pair |

Example production environment values (set by the hosting environment, not committed): `CORS_ORIGINS=https://dashboard.example` for FastAPI and `VITE_API_BASE_URL=https://api.example` when building the frontend. Keep origins explicit and do not place credentials in frontend variables.

## API contracts

All responses are JSON. Validation errors return HTTP `422` with `detail` and field-level `errors`.

| Method | Path | Behavior and data status |
| --- | --- | --- |
| `GET` | `/api/health` | `{"status":"ok"}`; backend process status, independent of GIS/ML availability |
| `GET` | `/api/conditions` | Existing conditions contract; static sample values, `demo: true` |
| `GET` | `/api/predictions` | Existing collection/item shape backed by SQLite; initial item is seeded demo data |
| `POST` | `/api/predictions` | Validates and persists `{ "items": [Prediction, ...] }`; returns `202`, `accepted: true`, `persisted: true` |
| `GET` | `/api/risks` | Existing risk summary shape; illustrative demo records |
| `GET` | `/api/alerts` | Active persisted alerts in the dashboard-compatible collection/item shape |
| `GET` | `/api/gis` | GeoJSON status; currently returns `status: unavailable` because no GIS artifact is present on this branch |

Prediction items contain `location`, `latitude`, `longitude`, `risk_type`, `risk_score`, and `risk_level`. Existing risk types and levels are validated; coordinates and scores are range-checked. Full examples are in [backend/README.md](backend/README.md).

## Database and alert rules

SQLAlchemy initializes missing tables at startup and does not delete existing rows. SQLite defaults to `backend/data/climatesense.db`, which is Git-ignored. An empty prediction store is seeded once from the existing demo record; the seed is not repeated when rows exist. Tests override `DATABASE_URL` to a temporary database and clean it up after the test session.

HIGH predictions create an active alert. MEDIUM and LOW predictions do not. An active alert with the same location, risk type, and risk level prevents duplicates; a partial unique index reinforces this rule. Alerts are deterministic application rules, not AI-generated or real-time notifications. There is no acknowledgement route in this milestone.

For PostgreSQL, configure a SQLAlchemy URL and install an appropriate driver in the deployment environment. PostgreSQL is not required locally. Before production schema evolution, add database migrations; startup `create_all` only creates missing tables.

## ML and GIS integration

The prediction service is the adapter point for future Member 2 output; keep the current Pydantic/API item contract stable when replacing its input source. The API does not train or run an ML model, and persisted submissions do not prove model provenance.

Member 4 only transports Member 3's GIS output. `GET /api/gis` reports unavailable until a GeoJSON artifact and its location are agreed. No geographic features are fabricated and no GIS processing, spatial joins, or aggregation are performed here.

## Tests and build

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q

cd ../frontend
npm ci
npm run build
```

The backend suite uses an isolated SQLite file. The frontend build emits deployable static assets into `frontend/dist/`.

## Deployment preparation and security

The backend can be started by an ASGI host with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`; configure `DATABASE_URL` and explicit `CORS_ORIGINS` in the host environment. Build the frontend with `VITE_API_BASE_URL` set to the API origin, then serve `frontend/dist/` from a static web host. A future PostgreSQL service and migration process should be configured separately. This project has not been deployed.

No credentials or API keys are required or included. Environment files and local databases are ignored. CORS is limited to local development/preview origins by default and rejects wildcard origins; production must set the exact frontend origins. There is no authentication, external notification channel, or real-time feed.

## Current limitations

Conditions and risks remain static examples. Prediction storage accepts validated records but does not call an ML model. GIS is unavailable until Member 3 supplies output. The local schema initializer is not a migration tool; production PostgreSQL migrations and operational monitoring remain future work.

## Data Preprocessing

The data preprocessing pipeline provides the initial climate-data foundation for the project.

- Raw climate data is stored under `data/raw/`
- Processed datasets are stored under `data/processed/`
- Dataset metadata and schemas are available under `data/metadata/`
- Data quality and analysis reports are available under `reports/`

The initial MVP uses validated climate observations and does not fabricate flood-event labels when authoritative target data is unavailable.

The preprocessing pipeline can be reproduced with:

```bash
python -m src.prepare_data