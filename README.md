# 🚦 NYC Mobility & Weather Analytics

Analyze how weather affects NYC transportation patterns across 14M+ trips from Yellow Taxi, FHV (Uber/Lyft), and CitiBike.

**Status**: ✅ MVP 3 Complete - Production-ready with automatic retry logic

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Poetry

### Get Running in 4 Commands

```bash
# 1. Install
poetry install

# 2. Ingest data (5-10 minutes for Oct-Nov 2025)
poetry run python src/ingestion/run_pipeline.py

# 3. Transform data
cd dbt && poetry run dbt build

# 4. Start dashboard
cd .. && poetry run streamlit run dashboard.py
```

**Dashboard opens at**: http://localhost:8501

**Note**: First-time setup takes ~15 minutes (mostly data download). Subsequent runs are much faster.

---

## 📊 Interactive Dashboard

The Streamlit dashboard provides visual analytics across:

- **Key Metrics**: Trip volume, distance, revenue, duration
- **Daily Trends**: Volume and patterns by transportation mode
- **Hourly Patterns**: Rush hour analysis and duration trends
- **Weather Impact**: Temperature and precipitation effects
- **Mode Comparison**: Taxi vs FHV vs CitiBike breakdown
- **Time Patterns**: Weekend vs weekday, day part analysis

**Features**:
- Date range filtering
- Transportation mode selection
- Interactive Plotly charts
- Real-time query performance (<1s with caching)

---

## 🔧 Running the Pipeline

**First time?** Run data ingestion first (see Quick Start above)

### Option 1: Dashboard (Recommended)
```bash
poetry run streamlit run dashboard.py
```
Opens interactive dashboard at http://localhost:8501

### Option 2: dbt Directly
```bash
cd dbt
poetry run dbt build  # Run all models + tests (30 seconds)
```

### Option 3: Dagster Orchestration
```bash
poetry run dagster dev -w orchestration/workspace.yaml
```
Opens Dagster UI at http://localhost:3000 with full lineage visualization

### Option 4: Complete Pipeline (Ingestion + Transformation)
```bash
# Run everything from scratch
poetry run python src/ingestion/run_pipeline.py  # DLT ingestion
cd dbt && poetry run dbt build                    # dbt transformations
cd .. && poetry run streamlit run dashboard.py    # Dashboard
```

---

## 🔍 Querying Data

### MetricFlow (50 Governed Metrics)

```bash
cd dbt

# List all metrics
poetry run mf list metrics

# Query total trips by mode
poetry run mf query \
  --metrics total_trips \
  --group-by trip__trip_type

# Weather impact analysis
poetry run mf query \
  --metrics trips_in_adverse_weather,trips_in_pleasant_weather \
  --group-by metric_time__month

# Revenue efficiency
poetry run mf query \
  --metrics revenue_per_mile \
  --group-by trip__trip_type
```

### SQL (Direct DuckDB Access)

```bash
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb')

# Query trips
print(conn.execute('''
    SELECT trip_type, COUNT(*) as trips
    FROM core_core.fct_trips
    GROUP BY trip_type
''').df())

# Weather correlation
print(conn.execute('''
    SELECT
        weather_condition,
        COUNT(*) as trips,
        AVG(trip_distance) as avg_distance
    FROM core_core.fct_trips
    WHERE weather_condition IS NOT NULL
    GROUP BY weather_condition
    ORDER BY trips DESC
''').df())
"
```

---

## ⚙️ Common Operations

### Add Data from Previous Months

```bash
# 1. Run DLT ingestion for new months
poetry run python src/ingestion/run_pipeline.py --year 2024 --months 1,2,3

# 2. Rebuild dbt models (dim_date automatically adjusts!)
cd dbt && poetry run dbt build
```

### Run Tests

```bash
cd dbt
poetry run dbt test  # 106/107 passing (99%)
```

### View dbt Documentation

```bash
cd dbt
poetry run dbt docs generate
poetry run dbt docs serve  # Opens at http://localhost:8080
```

### Run Data Quality Checks

```bash
poetry run python great_expectations/run_validations.py
```

### Materialize Specific Models

```bash
cd dbt

# Run only staging
poetry run dbt run --select staging

# Run specific model
poetry run dbt run --select dim_weather

# Run model and downstream
poetry run dbt run --select dim_weather+
```

---

## 🔄 Error Handling & Resilience

The pipeline implements production-grade error handling for reliable data ingestion:

### Automatic Retry Logic

Network errors and API rate limits trigger automatic retries with exponential backoff:

- **Max attempts**: 3 retries per failed request
- **Wait time**: 1-60 seconds with exponential backoff
- **Smart error classification**:
  - **Transient errors** (retry automatically): Timeouts, connection errors, HTTP 429/5xx
  - **Permanent errors** (fail fast): HTTP 404, 401/403, data validation errors

### Failed Month Tracking

If some months fail during ingestion, the pipeline continues processing remaining months and logs failures:

```bash
# Check logs for failed months
grep "failed months" logs/ingestion.log
```

Failed months don't stop the pipeline. Simply re-run ingestion to retry failed months:

```bash
poetry run python src/ingestion/run_pipeline.py --year 2025 --months 10,11
```

### Monitoring Ingestion

Watch for these success indicators in logs:

```
✓ Downloaded CitiBike ZIP for 2025-10
✓ Loaded 2,145,678 yellow taxi records for 2025-10
✓ Fetched 744 hourly records for 2025-10
```

### Retry Configuration

Default settings (configurable in `src/utils/retry.py`):

- Max attempts: 3
- Min wait: 2 seconds
- Max wait: 60 seconds
- Retryable errors: TransientError (network, rate limits, server errors)

---

## 🐛 Troubleshooting

### Database Locked
```bash
pkill -f duckdb  # Close all connections
```

### Tests Failing
```bash
cd dbt
poetry run dbt test --store-failures
# Check target/compiled/ for SQL of failed tests
```

### Dagster Can't Find Assets
```bash
cd dbt && poetry run dbt parse  # Regenerate manifest
poetry run dagster dev -w orchestration/workspace.yaml
```

### Dashboard Not Loading
```bash
# Check database exists
ls -lh data/nyc_mobility.duckdb  # Should be ~2.5GB

# If database missing or empty, run ingestion first
poetry run python src/ingestion/run_pipeline.py

# Then rebuild transformations
cd dbt && poetry run dbt build
```

### No Data / Empty Database
```bash
# Run the complete pipeline from scratch
poetry run python src/ingestion/run_pipeline.py  # Download data (5-10 min)
cd dbt && poetry run dbt build                    # Transform data (30 sec)
```

---

## 📊 What's Inside

### Data Pipeline
- **12 dbt models** (Bronze → Silver → Gold medallion architecture)
- **14M+ records** (Yellow Taxi, FHV, CitiBike, Weather)
- **50 metrics** across 4 categories (core, weather, mode share, time patterns)
- **106/107 tests passing** (99% data quality)
- **99.9996% weather coverage** (12.4M trips with weather data)

### Tech Stack
- **Ingestion**: DLT (Data Load Tool)
- **Storage**: DuckDB (~2.5GB)
- **Transformations**: dbt (Medallion + Kimball)
- **Orchestration**: Dagster
- **Metrics**: MetricFlow (semantic layer)
- **Quality**: Great Expectations + dbt tests
- **Dashboard**: Streamlit + Plotly

### Date Range
June 30 - November 30, 2025 (154 days)
- Dynamically adjusts when you add more data
- No hardcoded date limits

---

## 📚 Documentation

### Essential Docs (Start Here)
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and technical decisions
- **[data_model.md](docs/data_model.md)** - ERD and table relationships
- **[data_dictionary.md](docs/data_dictionary.md)** - Column definitions

### Component Docs
- **[orchestration/README.md](orchestration/README.md)** - Dagster orchestration guide
- **[great_expectations/README.md](great_expectations/README.md)** - Data quality validation
- **[notebooks/README.md](notebooks/README.md)** - Jupyter notebooks

### Project History & Migration Guides
- **[MVP3_CHANGES.md](docs/MVP3_CHANGES.md)** - MVP 3 production readiness improvements & upgrade guide
- **[MVP2_COMPLETION_SUMMARY.md](docs/MVP2_COMPLETION_SUMMARY.md)** - What was built in MVP 2

---

## 🏗️ Architecture Overview

```
NYC TLC + CitiBike + Weather API
           ↓
    DLT Ingestion (Bronze)
           ↓
    DuckDB Storage (~2.5GB)
           ↓
   dbt Transformations (Silver/Gold)
   • 4 Staging models
   • 4 Dimensions (date, time, weather, location)
   • 2 Facts (trips, hourly aggregates)
   • 50 Metrics (MetricFlow)
           ↓
   Dagster Orchestration
           ↓
   ┌──────┴──────┬──────────┐
   ↓             ↓          ↓
Streamlit    MetricFlow   dbt docs
Dashboard       CLI      (lineage)
```

For detailed architecture, see [ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 🎯 Key Features

### For Analysts
- 50 pre-defined metrics via MetricFlow CLI
- Interactive Streamlit analytics dashboard
- Data completeness monitoring dashboard (NEW!)
- SQL access to 32.5M enriched trips
- Weather impact analysis
- Mode comparison (taxi/FHV/bike)

### For Engineers
- Full lineage tracking in Dagster
- 109 automated tests (dbt + Great Expectations)
- Backfill support with 4 methods
- Data quality monitoring dashboard
- Medallion architecture (Bronze/Silver/Gold)
- Kimball star schema
- Dynamic date dimension (auto-adjusts to data)

### For Data Scientists
- 14M+ trips with weather correlations
- Hourly granularity
- 29 weather attributes
- Trip-level facts (distance, duration, speed)
- Jupyter notebooks for exploration

---

## 📈 Performance

- **Pipeline build time**: ~30 seconds
- **Test execution**: ~8 seconds (107 tests)
- **Dashboard load**: <3 seconds
- **Metric queries**: <1 second
- **Database size**: 2.5 GB

---

## 🔮 Roadmap

### ✅ MVP 3 Complete
- Production-grade error handling with automatic retries
- Environment-based configuration management
- Security cleanup (removed unused API references)
- Comprehensive retry behavior testing

### Next: Snowflake Migration
- SQL dialect conversion (DuckDB → Snowflake compatibility)
- Multi-database support (DuckDB + Snowflake)
- Cloud deployment infrastructure
- Incremental models for scalability

### Future Enhancements
- CI/CD pipeline (GitHub Actions)
- Real-time streaming (Kafka)
- ML forecasting models
- Enhanced dashboard (Hex or modern alternative)
- API layer (FastAPI)
- Public web interface

---

## 📝 Project Structure

```
nyc-mobility-weather-analytics/
├── README.md                    # This file
├── dashboard.py                 # Streamlit dashboard
├── data/
│   └── nyc_mobility.duckdb     # DuckDB database (2.5GB)
├── dbt/                         # dbt transformations
│   ├── models/                  # 12 dbt models
│   └── target/                  # Documentation site
├── docs/                        # Technical documentation
│   ├── ARCHITECTURE.md         # System design
│   ├── data_model.md           # ERD
│   └── data_dictionary.md      # Column reference
├── orchestration/               # Dagster orchestration
├── great_expectations/          # Data quality checks
├── src/ingestion/              # DLT pipelines
└── notebooks/                   # Jupyter notebooks
```

---

## 🤝 Contributing

This is a portfolio project demonstrating modern data engineering practices. For technical review:

1. Review [ARCHITECTURE.md](docs/ARCHITECTURE.md) for design decisions
2. Check [data_model.md](docs/data_model.md) for data structure
3. Run the pipeline and explore the dashboard
4. Review [MVP2_COMPLETION_SUMMARY.md](docs/MVP2_COMPLETION_SUMMARY.md) for implementation details

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙋 Questions?

- **Architecture**: See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Data Model**: See [docs/data_model.md](docs/data_model.md)
- **Issues**: Open an issue in GitHub
- **Contact**: [Your contact info]

---

**Built with**: Python • dbt • DuckDB • Dagster • Streamlit • MetricFlow

*Last Updated: January 10, 2026 - MVP 3*
