# ClimateSense AI — Backend Foundation (Part 1)

Welcome to **ClimateSense AI**, an AI-powered climate intelligence system designed to ingest environmental data (weather, air quality, remote sensing, and GIS spatial data), analyze risks using Machine Learning / Deep Learning models, and provide early warnings and risk mapping.

> **Note**: This repository currently contains **Part 1: Backend Foundation**. It establishes a scalable, ML-ready FastAPI backend architecture without premature complexity.

---

## Table of Contents

- [Overview](#overview)
- [Project Architecture](#project-architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Clone & Navigate](#2-clone--navigate)
  - [3. Set Up Virtual Environment](#3-set-up-virtual-environment)
  - [4. Install Dependencies](#4-install-dependencies)
  - [5. Environment Configuration](#5-environment-configuration)
- [Running the Backend](#running-the-backend)
- [API Endpoints](#api-endpoints)
  - [Health Check](#health-check)
  - [Interactive Documentation](#interactive-documentation)
- [Running Tests](#running-tests)
- [Future Roadmap](#future-roadmap)

---

## Overview

Part 1 focuses on setting up a robust, modular skeleton for future modules including:
- **Weather & AQI Ingestion pipelines**
- **Data preprocessing & feature engineering**
- **Machine Learning & Deep Learning risk predictors** (flood, air pollution, extreme heat)
- **GIS / Spatial computations & GeoJSON overlays**
- **Early-warning alert dispatchers**

---

## Project Architecture

```text
backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entrypoint
│   │
│   ├── api/                     # API routing layer
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py      # Route aggregator
│   │       └── health.py        # Service health check endpoint
│   │
│   ├── core/                    # Application configuration & core utilities
│   │   ├── __init__.py
│   │   └── config.py            # Pydantic Settings & environment loader
│   │
│   ├── models/                  # Domain and database data models
│   │   └── __init__.py
│   │
│   ├── schemas/                 # Pydantic validation & response schemas
│   │   ├── __init__.py
│   │   └── health.py
│   │
│   ├── services/                # External data fetchers & business services
│   │   └── __init__.py
│   │
│   ├── preprocessing/           # Data cleaning, scaling, and feature pipelines
│   │   └── __init__.py
│   │
│   ├── predictions/             # ML inference routines & model handlers
│   │   └── __init__.py
│   │
│   ├── gis/                     # Spatial analysis & GeoJSON generators
│   │   └── __init__.py
│   │
│   └── utils/                   # Shared helpers & common utilities
│       └── __init__.py
│
├── datasets/                    # Data storage organized by lifecycle
│   ├── raw/                     # Original, unprocessed data
│   ├── processed/               # Cleaned, ready-for-training data
│   └── sample/                  # Small lightweight sample datasets
│
├── models/
│   └── trained/                 # Serialized ML model weights (.pkl, .pt, etc.)
│
├── notebooks/                   # Jupyter notebooks for experiments & EDA
│
├── tests/                       # Automated test suite
│   ├── __init__.py
│   └── test_health.py
│
├── .env.example                 # Example environment variables template
├── .gitignore                   # Standard Python/FastAPI git ignore
├── requirements.txt             # Required Python package dependencies
└── README.md                    # Project documentation
```

---

## Tech Stack

- **Python**: 3.11+ (Python 3.11, 3.12, 3.13, 3.14 supported)
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **Configuration & Validation**: [Pydantic v2](https://docs.pydantic.dev/) & [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Data Processing**: [pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/)
- **Testing**: [pytest](https://docs.pytest.org/) & [HTTPX](https://www.python-httpx.org/)

---

## Getting Started

### 1. Prerequisites

Ensure you have Python 3.11 or higher installed on your system:

```bash
python --version
```

### 2. Clone & Navigate

Navigate to the `backend` directory:

```bash
cd backend
```

### 3. Set Up Virtual Environment

It is recommended to use a virtual environment:

**Windows (PowerShell / Command Prompt):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies

Install the core dependencies:

```bash
pip install -r requirements.txt
```

### 5. Environment Configuration

Copy `.env.example` to create your local `.env` file:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Contents of `.env`:
```env
APP_NAME="ClimateSense AI Backend"
APP_VERSION="0.1.0"
ENVIRONMENT="development"
DEBUG=True
```

---

## Running the Backend

Start the development server with live reload:

```bash
uvicorn app.main:app --reload
```

Once running, the server is available at:
`http://127.0.0.1:8000`

---

## API Endpoints

### Health Check

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/api/v1/health`
- **Response**:
```json
{
  "status": "ok",
  "service": "ClimateSense AI Backend",
  "version": "0.1.0"
}
```

### Interactive Documentation

FastAPI provides automatic interactive API documentation:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## Running Tests

Execute the automated test suite using `pytest`:

```bash
pytest
```

To run with verbose output:

```bash
pytest -v
```

---

## System Architecture Flow

```text
React Frontend (Vite)
       ↓
FastAPI Backend (/api/v1)
       ↓
Integration Layer (Services & Providers)
       ↓
Data / ML / GIS Providers (Member 1, Member 2, Member 3)
```

## Running the Complete System

- **Backend**:
  ```bash
  cd backend
  uvicorn app.main:app --host 127.0.0.1 --port 8000
  ```
- **Frontend**:
  ```bash
  cd frontend
  npm.cmd run dev
  ```

---

## Integration Layer (Member 1, Member 2, Member 3)

The backend provides clean, decoupled provider and registry interfaces:

- **Member 1 (Data Collection & Preprocessing)**:
  - Implement or subclass `BaseDataProvider` in `app/preprocessing/` or `app/services/data_provider.py`.
  - Swappable via `set_data_provider(...)` for live or cleaned weather/AQI streams.
- **Member 2 (AI/ML Prediction Models)**:
  - Implement or subclass `BaseClimateModel` in `app/predictions/model_interface.py`.
  - Register trained models (Random Forest, XGBoost, LSTM) into `model_registry` without modifying API controllers.
- **Member 3 (GIS & Risk Visualization)**:
  - Implement or subclass `BaseGISProvider` in `app/gis/gis_provider.py`.
  - Inject spatial zones, shapefiles, or raster matrices via `SpatialRiskRecord` or GeoJSON FeatureCollection.

### Important Note on Risk Aggregation & Modeling
> **Notice**: The multi-hazard aggregation logic in `app/services/risk_service.py` is an **application-level aggregation layer** designed for integration testing and API delivery. It is **not** scientifically validated climate risk modeling. When Member 2 (ML) and Member 3 (GIS) deliver calibrated models and regional vulnerability matrices, this layer will be calibrated accordingly.

---

## Future Roadmap

- **Part 2**: Weather & Air Quality API Ingestion
- **Part 3**: Data Cleaning, Preprocessing & Feature Engineering
- **Part 4**: Flood & Air Quality Prediction ML Models
- **Part 5**: Explainable AI (SHAP) & Early-Warning Triggers
- **Part 6**: GIS Mapping & Spatial Visualization APIs

