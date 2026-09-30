# ClimateSense AI — Frontend Dashboard

**AI-Powered Climate Intelligence & Early Warning System**

This directory contains the React + Vite frontend dashboard for the ClimateSense AI platform.

---

## Architecture Flow

```text
React Frontend (Vite)
       ↓
FastAPI Backend (/api/v1)
       ↓
Integration Layer (Services & Providers)
       ↓
Data / ML / GIS Providers (Member 1, Member 2, Member 3)
```

> **Note on Integration Providers**:
> Currently, the backend integration layer provides baseline development/test fixtures. These will be seamlessly replaced by:
> - **Member 1**: Processed weather & AQI datasets (`BaseDataProvider`)
> - **Member 2**: Trained Random Forest, XGBoost & LSTM models (`BaseClimateModel`)
> - **Member 3**: GIS spatial layers & GeoJSON shapefiles (`BaseGISProvider`)

---

## Project Structure

```text
frontend/
├── public/
├── src/
│   ├── components/         # Reusable UI components (Header, RiskCard, PredictionCard, etc.)
│   ├── pages/              # DashboardOverview
│   ├── map/                # GeoJSON parser & GIS coordinate configs
│   ├── services/           # api.js client layer with DEV_DATA fallback
│   ├── utils/              # constants.js, color mappings, baseline test fixtures
│   ├── App.jsx             # Root component with status coordination
│   ├── main.jsx            # Application entrypoint
│   └── index.css           # Global design system & responsive console styling
├── index.html              # HTML template
├── package.json            # Project dependencies & scripts
├── vite.config.js          # Vite configuration
└── README.md
```

---

## Running the Application

### 1. Start the Backend (Terminal 1)
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2. Start the Frontend (Terminal 2)
```bash
cd frontend
npm.cmd run dev
```

The dashboard will be available at `http://127.0.0.1:5173/`.

### 3. Build for Production
```bash
cd frontend
npm.cmd run build
```
The compiled static assets will be output to `dist/`.

---

## Available Scripts

- `npm.cmd run dev`: Starts the local Vite development server with Hot Module Replacement (HMR).
- `npm.cmd run build`: Compiles and bundles production-ready static assets into `dist/`.
- `npm.cmd run preview`: Locally previews the production build.
