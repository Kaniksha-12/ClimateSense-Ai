# ClimateSense AI Backend

FastAPI REST layer for the Member 4 dashboard. Conditions and risk overview data remain static examples. Prediction and alert records are stored locally in SQLite; the initial prediction and its alert are explicitly seeded demo data, not model output or live monitoring.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run from `backend/`. The API listens at `http://localhost:8000`; interactive OpenAPI documentation is at `/docs`.

For local development, CORS permits the Vite dev/preview origins. For a deployed frontend, set `CORS_ORIGINS` to a comma-separated list of exact origins, such as `https://dashboard.example`. Wildcard origins are rejected; credentials are not enabled. No CORS environment variable is needed locally.

An ASGI deployment can use `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `DATABASE_URL` and `CORS_ORIGINS` in the hosting environment. `/api/health` reports process availability and does not depend on GIS or ML sources.

For tests, install `pip install -r requirements-dev.txt` and run `python -m pytest` from this directory.

## API contracts

| Method | Path | Purpose | Status |
| --- | --- | --- | --- |
| `GET` | `/api/health` | Service health | Real service status |
| `GET` | `/api/conditions` | Current-conditions contract | Demo values |
| `GET` | `/api/predictions` | Persisted prediction records | SQLite; includes seed demo record on first startup |
| `POST` | `/api/predictions` | Validate and persist prediction records supplied by an integration | `202` accepted and persisted |
| `GET` | `/api/gis` | Member 3 GeoJSON integration status/output | Unavailable; no GIS artifact is present on this branch |
| `GET` | `/api/risks` | Dashboard risk overview records | Demo values |
| `GET` | `/api/alerts` | Active persisted alert feed | SQLite; rule-based, not live monitoring |

### Health

`GET /api/health` returns `200`:

```json
{"status":"ok"}
```

### Conditions

`GET /api/conditions` returns `200`:

```json
{
	"location": "Pune",
	"temperature": 28.5,
	"humidity": 72,
	"rainfall": 12.4,
	"air_quality": 86,
	"updated_at": null,
	"demo": true,
	"source": "Static demonstration values; not live conditions."
}
```

`updated_at` is null until a dataset supplies an observation timestamp.

### Predictions

`GET /api/predictions` returns `200` with persisted records in the existing item contract:

```json
{
	"demo": true,
	"source": "Includes the seeded demo prediction; no ML model is connected.",
	"items": [{
		"location": "Pune",
		"latitude": 18.5204,
		"longitude": 73.8567,
		"risk_type": "flood",
		"risk_score": 0.82,
		"risk_level": "HIGH"
	}]
}
```

`POST /api/predictions` accepts `{"items": [<Prediction>, ...]}` using that record shape. A valid request returns `202` with `accepted: true` and `persisted: true`. Existing response item fields remain unchanged; database ids and timestamps are internal.

Example request:

```json
{"items":[{"location":"Pune","latitude":18.5204,"longitude":73.8567,"risk_type":"flood","risk_score":0.82,"risk_level":"HIGH"}]}
```

Example response (`202 Accepted`):

```json
{"accepted":true,"persisted":true,"message":"Prediction records were persisted.","items":[{"location":"Pune","latitude":18.5204,"longitude":73.8567,"risk_type":"flood","risk_score":0.82,"risk_level":"HIGH"}]}
```

Both routes use `app/services/prediction_service.py`. GET reads from the repository; POST persists validated input. The initial seed comes from the existing demo provider and is inserted only if the prediction table is empty. Replace the provider/ingest source with Member 2 ML output without changing the frontend response contract. Submissions are not claimed to be ML predictions.

### GIS

`GET /api/gis` returns `200` with an explicit unavailable status because no GeoJSON or GIS output directory is present on this branch:

```json
{"status":"unavailable","source":"gis","message":"GIS output is not available yet."}
```

The route delegates to `app/services/gis_service.py`. When Member 3 supplies a GeoJSON artifact and its location/interface is agreed, this adapter can return `{"status":"ok","source":"gis","data":<GeoJSON FeatureCollection>}`. The adapter must validate the source as GeoJSON and preserve its FeatureCollection and feature properties before serving it. GIS processing, transformation, and aggregation remain owned by Member 3.

### Risks

`GET /api/risks` returns `200` with `demo`, `source`, and `items`. Each item has `location`, `risk_type`, `risk_score`, and `risk_level`. Supported types are `flood`, `drought`, `heatwave`, and `air_quality`; levels are `LOW`, `MEDIUM`, and `HIGH`; scores are inclusive from `0` to `1`. The values are illustrative only, not risk assessments.

Example response:

```json
{"demo":true,"source":"Static examples only; not real risk assessments.","items":[{"location":"Pune","risk_type":"flood","risk_score":0.82,"risk_level":"HIGH"}]}
```

### Alerts

`GET /api/alerts` returns `200` with `demo`, `source`, and active alert items containing `id`, `location`, `risk_type`, `risk_level`, `message`, and `severity`. The response remains compatible with the dashboard; internal `created_at` and `active` fields are not added to the public item shape.

Example response:

```json
{"demo":true,"source":"Includes seeded sample alerts; alerts are not real-time monitoring.","items":[{"id":"alert-001","location":"Pune","risk_type":"flood","risk_level":"HIGH","message":"High flood risk detected in Pune.","severity":"HIGH"}]}
```

If no alerts are active, the endpoint returns `200` with `items: []`. Alert generation is deterministic: only HIGH predictions create alerts; LOW and MEDIUM do not. An existing active alert with the same location, risk type, and risk level prevents another active duplicate. The database also enforces that active identity with a partial unique index. A future acknowledgement operation can set `active` false; no alert-management route is included in M5.

## Validation and errors

Prediction input validates required fields, latitude `[-90, 90]`, longitude `[-180, 180]`, risk score `[0, 1]`, supported risk types, and risk/severity levels. Invalid request bodies return `422` JSON with `detail: "Invalid request data"` and field-level `errors`.

## M5 Database

SQLAlchemy uses local SQLite by default. The file is `backend/data/climatesense.db`; set `DATABASE_URL` to override it. For example, from `backend/`:

```bash
DATABASE_URL=sqlite:///./data/local-dev.db uvicorn app.main:app --reload
```

No `.env`, Docker, or PostgreSQL server is required. Startup creates missing `predictions` and `alerts` tables and never drops existing data. The prediction table stores id, location, latitude, longitude, risk type, score, level, creation time, and an internal demo marker. The alert table stores id, location, risk type, level, message, severity, creation time, active state, and an internal demo marker.

The existing demo prediction is inserted only when the prediction table is empty. Its HIGH flood risk creates one sample alert. The seed is idempotent across restarts. Submitted records are marked as non-demo, but model provenance is not verified. Tests set `DATABASE_URL` to a temporary SQLite file and clean it up after the test session.

The configured SQLAlchemy URL and ORM layer are replaceable for PostgreSQL. PostgreSQL is not part of this milestone; a future move should add its driver and schema migrations. Current startup uses `create_all`, which creates missing tables but does not migrate altered schemas.

## Dataset, ML, and GIS integration

Replace the conditions demo service with Member 1 dataset outputs and the prediction provider with Member 2 model outputs when their contracts are available. The API is a transport and validation layer only: it does not train models or calculate risks. `/api/gis` reports unavailable until Member 3 supplies a consumable GeoJSON/output interface; GIS boundary processing and aggregation remain outside this repository. Alert rules are deterministic and do not claim live monitoring.
