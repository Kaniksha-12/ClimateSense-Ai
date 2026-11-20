# Contributing

Thanks for helping build ClimateSense AI. This project is developed by a four-member team; please keep changes inside your area unless the team agrees otherwise.

## Ownership

- **Member 1** - dataset outputs (`data/`)
- **Member 2** - ML model (`models/`)
- **Member 3** - GIS processing and GeoJSON production (`gis/`)
- **Member 4** - API, dashboard integration, local persistence, and delivery configuration (`backend/`, `frontend/`)

## Setup

See [README.md](README.md) for requirements and local run instructions. No `.env`, Docker, PostgreSQL server, or external service is needed for local development.

## Tests and build

Run these before opening a pull request:

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q

cd ../frontend
npm ci
npm run build
```

## Guidelines

- Keep the existing API contracts stable; the dashboard depends on them.
- Do not commit credentials, `.env` files, or local database files.
- Mark demo or seeded data as demo; do not present it as verified ML output.
