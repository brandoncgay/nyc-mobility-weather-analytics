# 🚦 NYC Mobility & Weather Analytics

Analyze how weather affects NYC transportation patterns across 14M+ trips from Yellow Taxi, FHV (Uber/Lyft), and CitiBike.

**Status**: ✅ Cloud Native Upgrade - MotherDuck, GCS, & Elementary Integration

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- **MotherDuck Token**: [Get one here](https://app.motherduck.com/)
- **GCP Service Account**: [Create one here](https://console.cloud.google.com/iam-admin/serviceaccounts)

### Get Running in 4 Commands

```bash
# 1. Install Dependencies
uv sync

# 2. Configure Environment
cp .env.template .env
# Edit .env and add MOTHERDUCK_TOKEN and GCP credentials

# 3. Runs the full End-to-End Pipeline
# Ingests to GCS Staging -> Loads to MotherDuck -> Transforms with dbt -> Validates
uv run dagster asset materialize --select \* -m orchestration

# 4. Explore Data
uv run marimo edit notebooks/marimo/01_exploration.py
```

---

## 🏗️ Architecture Overview

The platform has been upgraded to a **"Small Big Data"** cloud-native architecture:

```
Sources (NYC TLC, CitiBike, Open-Meteo)
           ↓
    dlt Ingestion
           ↓
  GCS Staging (Parquet)
           ↓
MotherDuck Data Warehouse (Cloud DuckDB)
           ↓
       dbt Core
   (Silver/Gold Layers)
           ↓
   ┌───────┴────────┬───────────────┐
   ↓                ↓               ↓
Marimo         Elementary       Streamlit
Notebooks     Observability     Dashboard
```

### Key Components
- **Ingestion**: `dlt` pipeline loading raw data into **Google Cloud Storage (GCS)** buckets.
- **Warehouse**: **MotherDuck** (Serverless DuckDB) for high-performance analytics.
- **Transformation**: `dbt` models with medallion architecture (Bronze → Silver → Gold).
- **Semantics**: `MetricFlow` (dbt Semantic Layer) for defining governed metrics like `total_trips` and `revenue`.
- **Observability**: **Elementary** for data anomaly detection and automated reporting.
- **Orchestration**: **Dagster** managing the entire lineage from GCS to Documentation.

---

## 📊 Observability & Docs

We use **Elementary** and **dbt Docs** hosted on GCS to ensure data quality and transparency.

### Generate & Upload Docs
The Dagster pipeline includes a `documentation` asset that runs:
1. `dbt docs generate`
2. `edr report` (Elementary)
3. Uploads the static sites to your GCS bucket.

Access them at your GCS bucket URL (e.g., `https://storage.googleapis.com/<bucket>/dbt-docs/index.html`).

---

## 🔧 Developer Guide

### Running Specific Components

**Run Ingestion (Local Dev)**
```bash
uv run python src/ingestion/run_pipeline.py --year 2024 --months 1 --sources taxi
```

**Run dbt Models**
```bash
cd dbt
uv run dbt build --target prod
```

**Run Observability Report**
```bash
cd dbt
uv run edr report
```

**Start Dagster UI**
```bash
uv run dagster dev -m orchestration
```

---

## 📝 Project Structure

```
nyc-mobility-weather-analytics/
├── src/ingestion/          # dlt pipelines (Taxi, CitiBike, Weather)
├── dbt/                    # dbt project
│   ├── models/             # SQL transformations
│   └── semantic_models/    # MetricFlow definitions
├── orchestration/          # Dagster assets & jobs
├── notebooks/marimo/       # Reactive Marimo notebooks
├── dashboard.py            # Streamlit dashboard
└── config/                 # Pipeline configuration
```

---

## 🤝 Contributing

1. **MotherDuck**: Ensure you have a valid token in `.env`.
2. **GCS**: Ensure your Service Account has `Storage Object Admin` permissions.
3. **Marimo**: Use `marimo edit` instead of Jupyter for notebooks.

---

**Built with**: Python • uv • dlt • MotherDuck • dbt • Dagster • Elementary • Marimo
