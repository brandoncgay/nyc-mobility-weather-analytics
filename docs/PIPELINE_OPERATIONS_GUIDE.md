# Pipeline Operations Guide

Complete guide for running, testing, and backfilling the NYC Mobility & Weather Analytics pipeline.

## Table of Contents
1. [Pipeline Architecture](#pipeline-architecture)
2. [Initial Setup & Verification](#initial-setup--verification)
3. [Running the Pipeline](#running-the-pipeline)
4. [Testing the Pipeline](#testing-the-pipeline)
5. [Backfills & Historical Data](#backfills--historical-data)
6. [Validating Results](#validating-results)
7. [Troubleshooting](#troubleshooting)

---

## Pipeline Architecture

The complete pipeline consists of three main stages orchestrated by Dagster:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DLT Ingestion (Bronze)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Yellow Taxi  │  │   CitiBike   │  │   Weather    │         │
│  │   (~8.6M)    │  │   (~1.4M)    │  │   (~1.5K)    │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                  │
│                            ▼                                     │
│                 ┌─────────────────────┐                          │
│                 │ DLT Ingestion       │                          │
│                 │ Complete Marker     │                          │
│                 └──────────┬──────────┘                          │
└────────────────────────────┼───────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  dbt Transformation (Silver)                    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Staging    │  │ Dimensions   │  │    Facts     │         │
│  │  (4 models)  │  │  (4 models)  │  │  (2 models)  │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                  │
│                            ▼                                     │
│                 ┌─────────────────────┐                          │
│                 │  Semantic Layer     │                          │
│                 │   (50 metrics)      │                          │
│                 └─────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Great Expectations Validation (Gold)               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Data Quality │  │  Completeness│  │ Consistency  │         │
│  │   Checks     │  │    Checks    │  │   Checks     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

**Key Components:**

1. **DLT Ingestion (Bronze Layer)**
   - Ingests raw data from external sources
   - 3 parallel assets: yellow_taxi, citibike, weather
   - Loads into DuckDB `raw_data` schema
   - Managed by `src/ingestion/run_pipeline.py`

2. **dbt Transformation (Silver Layer)**
   - Depends on DLT ingestion completion
   - 12 models: staging → intermediate → marts
   - 108 tests for data quality
   - Managed by `dbt/` directory

3. **Great Expectations Validation (Gold Layer)**
   - 10 validation suites
   - 56 data quality checks
   - Managed by `great_expectations/` directory

**Orchestration:**

All stages are orchestrated by Dagster, which:
- Tracks asset dependencies
- Provides visual lineage graph
- Enables selective materialization
- Logs execution history

---

## Initial Setup & Verification

### 1. Verify Environment

```bash
# Check Poetry environment
poetry --version

# Install dependencies (if not already done)
poetry install

# Verify Python version (should be 3.11 or 3.12)
poetry run python --version
```

### 2. Verify Data is Loaded

```bash
# Check if DuckDB database exists
ls -lh data/nyc_mobility.duckdb

# Connect to DuckDB and verify raw data
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb')
print('Raw Data Tables:')
print(conn.execute(\"\"\"
    SELECT table_schema, table_name,
           COUNT(*) as row_count
    FROM information_schema.tables
    WHERE table_schema = 'raw_data'
    GROUP BY table_schema, table_name
\"\"\").fetchall())
conn.close()
"
```

Expected output:
- `raw_data.yellow_taxi` - ~8.6M rows
- `raw_data.fhv_taxi` - ~2.4M rows
- `raw_data.trips` (CitiBike) - ~1.4M rows
- `raw_data.hourly_weather` - ~1,464 rows

### 3. Verify dbt Connection

```bash
cd dbt
poetry run dbt debug

# Should show all connections green
# ✅ Connection test: [OK]
```

---

## Running the Pipeline

### Option 1: Full Manual Pipeline Run

This runs everything step-by-step so you can see each stage.

```bash
# 1. Clean previous build (optional - full refresh)
cd dbt
rm -rf target/
rm -rf dbt_packages/

# 2. Install dbt packages
poetry run dbt deps

# 3. Parse and compile
poetry run dbt parse

# 4. Run staging models only (Bronze layer)
poetry run dbt run --select staging

# 5. Run dimension tables (Silver layer)
poetry run dbt run --select marts.core.dim_*

# 6. Run fact tables (Silver layer)
poetry run dbt run --select marts.core.fct_*

# 7. Build semantic layer (Gold layer)
poetry run dbt run --select marts.core.metricflow_time_spine

# 8. Run all tests
poetry run dbt test

# 9. Generate documentation
poetry run dbt docs generate
```

### Option 2: Single Command - Full Build

The simplest way to run everything:

```bash
cd dbt

# Build everything: models + seeds + tests
poetry run dbt build

# This runs in dependency order:
# 1. Seeds (tlc_taxi_zones)
# 2. Staging models
# 3. Intermediate models
# 4. Dimension tables
# 5. Fact tables
# 6. Semantic models
# 7. All tests
```

### Option 3: Run Through Dagster (Recommended for Production)

This is the **recommended approach** for running the complete end-to-end pipeline.

```bash
# Start Dagster UI
cd /path/to/nyc-mobility-weather-analytics
poetry run dagster dev -w orchestration/workspace.yaml

# Open browser to: http://localhost:3000
```

**In the Dagster UI:**

1. **Run Full Pipeline (DLT + dbt + GE):**
   - Go to "Jobs" tab → Select "full_pipeline"
   - Click "Launch Run"
   - Watch real-time logs as each asset materializes

2. **Run Specific Stages:**
   - **Ingestion only**: Jobs → "dlt_ingestion" → Launch Run
   - **Transformation only**: Jobs → "dbt_transformation" → Launch Run

3. **Selective Asset Materialization:**
   - Go to "Assets" tab
   - Click asset graph to visualize dependencies
   - Select specific assets (e.g., just yellow_taxi + dbt models)
   - Click "Materialize selected"

**Benefits of Dagster:**
- **Visual lineage**: See complete data flow from ingestion → transformation → validation
- **Dependency tracking**: Dagster ensures DLT completes before dbt runs
- **Real-time logs**: Monitor progress of long-running ingestion
- **Asset versioning**: Track when each asset was last materialized
- **Selective runs**: Re-run only failed assets
- **Scheduling**: Enable daily_dbt_schedule for automated runs

**Dagster Jobs Available:**

| Job Name | Description | Assets Included |
|----------|-------------|-----------------|
| `full_pipeline` | Complete end-to-end pipeline | All DLT + all dbt + validation |
| `dlt_ingestion` | Data ingestion only | yellow_taxi, citibike, weather |
| `dbt_transformation` | dbt models only | All dbt staging, marts, metrics |

### Option 4: Using the Pipeline Script (Quickest)

For quick local development and testing:

```bash
# Run complete pipeline (DLT + dbt + validation)
./scripts/run_pipeline.sh full

# Run only ingestion
./scripts/run_pipeline.sh ingestion

# Run only transformations (requires data to exist)
./scripts/run_pipeline.sh quick
```

**Available Commands:**
- `full` - Complete pipeline (DLT → dbt → GE)
- `ingestion` - Run DLT data ingestion only
- `quick` - Quick smoke test (staging + 1 dim + 1 fact)
- `test` - Run all tests
- `validate` - Validate data quality
- `backfill` - Full refresh all models

---

## Testing the Pipeline

### Quick Smoke Test

Run this after any code changes to verify everything works:

```bash
#!/bin/bash
# File: scripts/smoke_test.sh

echo "🔍 Running pipeline smoke test..."

# 1. Parse dbt project
echo "Step 1: Parsing dbt project..."
cd dbt && poetry run dbt parse || exit 1

# 2. Run a single staging model
echo "Step 2: Running staging model..."
poetry run dbt run --select stg_weather__hourly || exit 1

# 3. Run a single dimension
echo "Step 3: Running dimension..."
poetry run dbt run --select dim_date || exit 1

# 4. Run a single fact
echo "Step 4: Running fact..."
poetry run dbt run --select fct_trips --limit 10000 || exit 1

# 5. Run tests on that fact
echo "Step 5: Running tests..."
poetry run dbt test --select fct_trips || exit 1

echo "✅ Smoke test passed!"
```

### Full Test Suite

```bash
# Run all dbt tests
cd dbt
poetry run dbt test

# Run Great Expectations validations
cd ..
poetry run python great_expectations/run_validations.py

# Expected: 108 dbt tests passing, 10 GE validations executed
```

### Test Specific Models

```bash
cd dbt

# Test specific model
poetry run dbt test --select dim_weather

# Test specific fact table
poetry run dbt test --select fct_trips

# Test all models that depend on a source
poetry run dbt test --select source:tlc+

# Test modified models only
poetry run dbt test --select state:modified+
```

### Validate Data Quality

```bash
# Check row counts
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb')

print('Data Quality Checks:')
print('\nRow Counts:')
print(conn.execute('SELECT COUNT(*) as trips FROM core_core.fct_trips').fetchone())
print(conn.execute('SELECT COUNT(*) as dates FROM core_core.dim_date').fetchone())
print(conn.execute('SELECT COUNT(*) as locations FROM core_core.dim_location').fetchone())

print('\nWeather Join Coverage:')
print(conn.execute('''
    SELECT
        COUNT(*) as total_trips,
        SUM(CASE WHEN weather_key IS NOT NULL THEN 1 ELSE 0 END) as trips_with_weather,
        ROUND(100.0 * SUM(CASE WHEN weather_key IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 4) as coverage_pct
    FROM core_core.fct_trips
''').fetchone())

conn.close()
"
```

---

## Backfills & Historical Data

### Understanding Backfills in This Pipeline

Since the pipeline uses **full-refresh** models (not incremental), a "backfill" means:
1. Re-running the entire pipeline on existing data
2. Running the pipeline on a different time period
3. Testing the pipeline on subsets of data

### Full Pipeline Backfill (Complete Refresh)

```bash
# This re-processes ALL data from scratch
cd dbt

# Option 1: Full refresh all models
poetry run dbt build --full-refresh

# Option 2: Full refresh specific models
poetry run dbt run --select fct_trips --full-refresh
```

### Backfill Specific Date Range

To backfill a specific date range, you need to filter the source data:

**Method 1: Using dbt Variables**

```bash
# Run for specific month
poetry run dbt build --vars '{"start_date": "2025-10-01", "end_date": "2025-10-31"}'
```

To enable this, add to your models:

```sql
-- In staging models
{% if var("start_date", None) and var("end_date", None) %}
WHERE pickup_datetime >= '{{ var("start_date") }}'
  AND pickup_datetime < '{{ var("end_date") }}'
{% endif %}
```

**Method 2: Subset Testing**

Test pipeline on a smaller dataset:

```bash
# Run staging with LIMIT
poetry run dbt run --select staging --vars '{"limit": 100000}'

# Then run downstream models
poetry run dbt run --select marts
```

### Backfill Through Dagster

Dagster provides built-in backfill capabilities:

```bash
# Start Dagster
poetry run dagster dev -w orchestration/workspace.yaml

# In UI:
# 1. Go to Assets → dbt_analytics_assets
# 2. Click "Materialize" dropdown
# 3. Select "Backfill"
# 4. Choose partition range (if using partitioned assets)
```

**To enable partitioned backfills, update Dagster asset:**

```python
# In orchestration/assets/dbt_assets.py
from dagster import DailyPartitionsDefinition

daily_partition = DailyPartitionsDefinition(start_date="2025-09-01")

@dbt_assets(
    manifest=DBT_PROJECT_DIR / "target" / "manifest.json",
    partitions_def=daily_partition,  # Add partitioning
)
def dbt_analytics_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    partition_date = context.partition_key
    # Run dbt with date filter
    yield from dbt.cli(
        ["build", "--vars", f'{{"run_date": "{partition_date}"}}'],
        context=context
    ).stream()
```

### Incremental Backfill Strategy

For future incremental models:

```sql
-- Example: incremental fact table
{{ config(
    materialized='incremental',
    unique_key='trip_key',
    on_schema_change='fail'
) }}

SELECT * FROM {{ ref('int_trips__unioned') }}

{% if is_incremental() %}
    -- Only process new data
    WHERE pickup_datetime > (SELECT MAX(pickup_datetime) FROM {{ this }})
{% endif %}
```

Then backfill:

```bash
# Initial load: full refresh
poetry run dbt run --select fct_trips --full-refresh

# Incremental updates
poetry run dbt run --select fct_trips

# Re-process specific period
poetry run dbt run --select fct_trips --full-refresh \
    --vars '{"start_date": "2025-11-01", "end_date": "2025-11-30"}'
```

---

## Validating Results

### 1. Check Model Execution

```bash
# View dbt run results
cat dbt/target/run_results.json | jq '.results[] | {node: .unique_id, status: .status, rows: .adapter_response.rows_affected}'

# Check for failures
cat dbt/target/run_results.json | jq '.results[] | select(.status != "success")'
```

### 2. Validate Row Counts

```bash
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb')

# Expected row counts
checks = [
    ('Staging - Yellow Taxi', 'SELECT COUNT(*) FROM core.stg_tlc__yellow_taxi', 8_600_000),
    ('Staging - FHV', 'SELECT COUNT(*) FROM core.stg_tlc__fhv_taxi', 2_400_000),
    ('Staging - CitiBike', 'SELECT COUNT(*) FROM core.stg_citibike__trips', 1_400_000),
    ('Dimension - Date', 'SELECT COUNT(*) FROM core_core.dim_date', 122),
    ('Dimension - Time', 'SELECT COUNT(*) FROM core_core.dim_time', 24),
    ('Fact - Trips', 'SELECT COUNT(*) FROM core_core.fct_trips', 12_400_000),
]

print('Row Count Validation:')
for name, query, expected in checks:
    actual = conn.execute(query).fetchone()[0]
    status = '✅' if actual >= expected * 0.95 else '❌'  # Allow 5% variance
    print(f'{status} {name}: {actual:,} (expected ~{expected:,})')

conn.close()
"
```

### 3. Validate Metrics

```bash
cd dbt

# Test metric queries
poetry run mf query --metrics total_trips --group-by trip__trip_type

# Expected output:
# ┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
# ┃ trip__trip_type ┃ total_trips ┃
# ┣━━━━━━━━━━━━━━╋━━━━━━━━━━━━━┫
# ┃ yellow_taxi  ┃ 8,600,000   ┃
# ┃ fhv          ┃ 2,400,000   ┃
# ┃ citibike     ┃ 1,400,000   ┃
# ┗━━━━━━━━━━━━━━┻━━━━━━━━━━━━━┛
```

### 4. Validate Data Quality

```bash
# Run Great Expectations
poetry run python great_expectations/run_validations.py

# Check results
open great_expectations/uncommitted/data_docs/local_site/index.html
```

### 5. Visual Validation in Dagster

```bash
# Start Dagster
poetry run dagster dev -w orchestration/workspace.yaml

# Check:
# 1. Asset materialization status (all green)
# 2. Execution time (should be ~30-60 seconds)
# 3. Row counts in asset metadata
# 4. No failed runs
```

---

## Troubleshooting

### Common Issues

**1. "Database locked" error**

```bash
# Close all DuckDB connections
pkill -f duckdb

# Or restart with a fresh database
rm data/nyc_mobility.duckdb
# Re-run ingestion pipeline
poetry run python src/ingestion/run_pipeline.py
```

**2. "Compilation Error: depends on a node not found"**

```bash
# Clean and rebuild
cd dbt
rm -rf target/ dbt_packages/
poetry run dbt deps
poetry run dbt compile
```

**3. "Schema does not exist"**

```bash
# Run seeds first
cd dbt
poetry run dbt seed

# Then run models
poetry run dbt run
```

**4. Tests failing**

```bash
# Run tests with debug output
poetry run dbt test --select dim_date --store-failures

# Check failed test results
poetry run dbt show --select test_name
```

**5. Dagster can't find assets**

```bash
# Regenerate dbt manifest
cd dbt
poetry run dbt parse

# Restart Dagster
poetry run dagster dev -w orchestration/workspace.yaml
```

### Performance Optimization

```bash
# Run with more threads (faster)
cd dbt
poetry run dbt run --threads 8

# Run specific model group
poetry run dbt run --select marts.core.dim_* --threads 4

# Skip tests during development
poetry run dbt run --exclude test_type:data
```

### Debug Mode

```bash
# Run with debug logging
cd dbt
poetry run dbt --debug run --select fct_trips

# Show compiled SQL
poetry run dbt compile --select fct_trips
cat target/compiled/nyc_mobility_analytics/models/marts/core/fct_trips.sql
```

---

## Advanced Operations

### 1. Dry Run (Compile Only)

```bash
# See what would run without executing
cd dbt
poetry run dbt compile --select fct_trips

# View compiled SQL
cat target/compiled/nyc_mobility_analytics/models/marts/core/fct_trips.sql
```

### 2. Parallel Execution

```bash
# Run multiple models in parallel
cd dbt
poetry run dbt run --threads 8 --select marts

# Run tests in parallel
poetry run dbt test --threads 8
```

### 3. Selective Refresh

```bash
# Only refresh models that changed
poetry run dbt run --select state:modified+

# Only refresh downstream of a specific model
poetry run dbt run --select stg_weather__hourly+

# Only refresh a specific path
poetry run dbt run --select stg_weather__hourly+dim_weather+fct_trips
```

### 4. Schedule Automation

**Using Dagster Schedules:**

```bash
# Enable daily schedule
poetry run dagster dev -w orchestration/workspace.yaml

# In UI: Schedules → daily_dbt_build → Toggle to "Running"
```

**Using Cron (Alternative):**

```bash
# Add to crontab
crontab -e

# Run daily at 2 AM
0 2 * * * cd /path/to/project && poetry run python -c "from orchestration.schedules import dbt_build_job; dbt_build_job.execute_in_process()"
```

---

## Example Workflows

### Development Workflow

```bash
# 1. Make changes to dbt model
vim dbt/models/marts/core/dim_weather.sql

# 2. Compile to check SQL
poetry run dbt compile --select dim_weather

# 3. Run just that model
poetry run dbt run --select dim_weather

# 4. Test it
poetry run dbt test --select dim_weather

# 5. Run downstream models
poetry run dbt run --select dim_weather+

# 6. Full test
poetry run dbt test
```

### Production Deployment Workflow

```bash
# 1. Full clean build
cd dbt
rm -rf target/
poetry run dbt deps
poetry run dbt build --full-refresh

# 2. Run quality checks
cd ..
poetry run python great_expectations/run_validations.py

# 3. Generate documentation
cd dbt
poetry run dbt docs generate

# 4. Deploy to Dagster
poetry run dagster dev -w orchestration/workspace.yaml

# 5. Enable schedule
# (In UI: Schedules → daily_dbt_build → Running)
```

### Monitoring Workflow

```bash
# Check last run status
poetry run python -c "
import json
with open('dbt/target/run_results.json') as f:
    results = json.load(f)
    print(f\"Success: {results['success']}\")
    print(f\"Total: {len(results['results'])}\")
    print(f\"Failures: {sum(1 for r in results['results'] if r['status'] != 'success')}\")
"

# View logs
tail -f logs/dagster_compute/*.log

# Check Dagster runs
poetry run dagster run list -m orchestration --limit 10
```

---

## Next Steps

1. **Set up automated backfills** - Use Dagster partitions for historical data
2. **Add monitoring** - Set up alerts for failed runs
3. **Optimize performance** - Add incremental models for large tables
4. **Add CI/CD** - Automate testing in GitHub Actions
5. **Production deployment** - Move to Snowflake (MVP 3)

---

For more details, see:
- [MVP 2 Completion Summary](MVP2_COMPLETION_SUMMARY.md)
- [dbt Documentation](../dbt/target/index.html)
- [Dagster Guide](../orchestration/README.md)
- [Great Expectations Guide](../great_expectations/README.md)
