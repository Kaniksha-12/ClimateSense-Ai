# ClimateSense AI Dashboard

React + Vite dashboard for the Member 4 integration foundation. It requests health, conditions, predictions, risks, alerts, and GIS status from FastAPI through the Vite `/api` development proxy. Prediction and alert values are displayed from their existing response contracts; sample rows are identified by backend-provided source text. The map panel displays the GIS API's unavailable state until Member 3 output is provided.

## Run

```bash
npm install
npm run dev
```

Start the backend separately on `http://127.0.0.1:8000`. Vite serves the dashboard at `http://localhost:5173` and forwards `/api` requests to FastAPI. Override the development proxy with `VITE_BACKEND_URL` if FastAPI uses another local URL.

The centralized API service uses an empty `VITE_API_BASE_URL` by default, so browser requests remain relative `/api/...` and work with the Vite proxy. For a production build, set the API origin at build time, for example:

```bash
VITE_API_BASE_URL=https://api.example npm run build
```

The output is written to `dist/`; `npm run preview` serves the built frontend locally. Do not place secrets in Vite variables because they are embedded in client-side assets.
