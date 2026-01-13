# Dagster Orchestration

This directory contains the Dagster orchestration code for the NYC Mobility & Weather Analytics Platform.

## Overview

The orchestration layer provides:
- **Asset Management**: All dbt models loaded as Dagster assets with automatic dependency tracking
- **Scheduling**: Daily pipeline runs at 2 AM UTC
- **Monitoring**: Compute logs and event tracking
- **Lineage**: Full data lineage visualization in Dagster UI

## Project Structure

```
orchestration/
├── __init__.py              # Main Dagster definitions
├── workspace.yaml           # Workspace configuration
├── dagster.yaml            # Instance configuration
├── assets/
│   ├── __init__.py
│   └── dbt_assets.py       # dbt models as Dagster assets
├── resources/
│   └── __init__.py         # Resource configurations (dbt, DuckDB)
└── schedules/
    └── __init__.py         # Schedule definitions
```

## dbt Assets

The dbt project is loaded as a single Dagster asset that includes:

**Staging Models (Bronze Layer)**:
- `stg_citibike__trips`
- `stg_tlc__yellow_taxi`
- `stg_tlc__fhv_taxi`
- `stg_weather__hourly`

**Dimension Tables (Silver Layer)**:
- `dim_date` - Calendar dimension with business flags
- `dim_time` - Time dimension with day parts
- `dim_weather` - Weather dimension with categorizations
- `dim_location` - Location dimension based on TLC taxi zones

**Fact Tables (Silver Layer)**:
- `fct_trips` - Trip-level fact table with weather enrichment
- `fct_hourly_mobility` - Hourly aggregated mobility metrics

**Semantic Layer (Gold Layer)**:
- `metricflow_time_spine` - Time spine for MetricFlow
- 50 governed metrics across 4 categories

## Usage

### Start Dagster UI

```bash
# From the project root
poetry run dagster dev -w orchestration/workspace.yaml
```

Then open http://localhost:3000 to access the Dagster UI.

### Run the Pipeline Manually

In the Dagster UI:
1. Navigate to the "Assets" tab
2. Click on the `dbt_analytics_assets` asset
3. Click "Materialize" to run all dbt models

Alternatively, use the CLI:
```bash
poetry run dagster asset materialize -m orchestration --select dbt_analytics_assets
```

### View Asset Lineage

The Dagster UI provides a visual graph of all dbt models and their dependencies:
1. Go to the "Asset Lineage" view
2. See how staging models flow through dimensions and facts
3. Track data freshness and last materialization times

### Monitor Pipeline Runs

1. Navigate to the "Runs" tab to see all pipeline executions
2. Click on a run to see:
   - Execution timeline
   - Compute logs from dbt
   - Asset materialization events
   - Any errors or warnings

## Schedules

### Daily dbt Build

- **Schedule**: `daily_dbt_build`
- **Cron**: `0 2 * * *` (2 AM UTC daily)
- **Action**: Runs `dbt build` (all models + tests)

To enable the schedule:
1. Go to the "Schedules" tab in Dagster UI
2. Toggle the `daily_dbt_build` schedule to "Running"

Or use the CLI:
```bash
poetry run dagster schedule start daily_dbt_build -m orchestration
```

## Resources

### dbt Resource

The `dbt` resource is configured to:
- Point to the `dbt/` directory in the project root
- Use the `dev` target from `profiles.yml`
- Execute dbt commands via the CLI

### DuckDB Connection

DuckDB is managed by dbt through the `dbt-duckdb` adapter. The connection settings are in `dbt/profiles.yml`.

## Logging and Storage

- **Compute Logs**: Stored in `logs/dagster_compute/`
- **Event Logs**: Stored in `data/dagster_storage/` (SQLite)
- **Run History**: Stored in `data/dagster_storage/` (SQLite)
- **Schedule State**: Stored in `data/dagster_storage/` (SQLite)

Logs are retained for 30 days by default (configurable in `dagster.yaml`).

## Development

### Validate Definitions

```bash
poetry run python orchestration/validate_definitions.py
```

### Regenerate dbt Manifest

After making changes to dbt models:

```bash
cd dbt && poetry run dbt parse
```

Then restart Dagster to pick up the changes.

## Backfilling Historical Data

⚠️ **Critical**: The incremental strategy in `fct_trips` and `fct_hourly_mobility` only processes data NEWER than the maximum date already in the table. To backfill historical months, you must use one of the methods below.

### Understanding the Problem

```sql
-- Current incremental filter in fct_trips.sql
WHERE pickup_datetime > (SELECT MAX(pickup_datetime) FROM fct_trips)

-- If your current data: June-November 2025 (max date: 2025-11-30)
-- And you try to load: May 2025
-- Result: May data is EXCLUDED (May < November) ❌
```

### Method 1: Using the Backfill Job (Recommended)

The `backfill_monthly_data` job automatically handles full refresh for you:

```bash
# Backfill a single month (e.g., May 2025)
poetry run dagster job launch backfill_monthly_data \
  --config '{
    "ops": {
      "monthly_dlt_ingestion": {
        "config": {
          "year": 2025,
          "month": 5,
          "sources": "taxi,citibike,weather"
        }
      }
    }
  }'
```

This job:
1. Ingests May data via DLT (idempotent - safe to rerun)
2. Runs dbt with `--full-refresh` to rebuild fact tables (~30 seconds)
3. Validates that data loaded correctly

### Method 2: Manual Backfill with Full Refresh

```bash
# Step 1: Ingest the historical month
poetry run python src/ingestion/run_pipeline.py \
  --year 2025 \
  --months 5 \
  --sources taxi,citibike,weather

# Step 2: Full refresh fact tables to reprocess all data
cd dbt && poetry run dbt run \
  --full-refresh \
  --select fct_trips fct_hourly_mobility
```

**Why this works:**
- `--full-refresh` ignores incremental logic and rebuilds entire table
- Processes ALL data from source (not just new data)
- Takes ~30 seconds for 32M trips in DuckDB

### Method 3: Targeted Backfill with Date Range (Faster)

If you want to avoid full refresh for large datasets:

```bash
# Step 1: Ingest the historical month
poetry run python src/ingestion/run_pipeline.py \
  --year 2025 \
  --months 5 \
  --sources taxi,citibike,weather

# Step 2: Use date range variable for targeted backfill
cd dbt && poetry run dbt run \
  --select fct_trips fct_hourly_mobility \
  --vars '{"backfill_start_date": "2025-05-01"}'
```

**Why this is faster:**
- Only processes data from May onwards (not entire history)
- Still slower than normal incremental, but faster than full refresh
- Useful for large datasets where full refresh takes too long

### Method 4: Forward-Loading (No Special Action Needed)

If you're loading months AFTER your current max date, use the regular job:

```bash
# Load December 2025 (after current max date of November 2025)
poetry run dagster job launch monthly_ingestion \
  --config '{
    "ops": {
      "monthly_dlt_ingestion": {
        "config": {
          "year": 2025,
          "month": 12
        }
      }
    }
  }'
```

**This works normally** because December > November (no special handling needed).

### Backfill Multiple Months

To backfill several historical months (e.g., Jan-May 2025):

```bash
# Option A: Backfill all at once
poetry run python src/ingestion/run_pipeline.py \
  --year 2025 \
  --months 1,2,3,4,5 \
  --sources taxi,citibike,weather

cd dbt && poetry run dbt run --full-refresh --select fct_trips fct_hourly_mobility

# Option B: Backfill one month at a time (safer, easier to monitor)
for month in 1 2 3 4 5; do
  echo "Backfilling month $month..."
  poetry run dagster job launch backfill_monthly_data \
    --config "{\"ops\": {\"monthly_dlt_ingestion\": {\"config\": {\"year\": 2025, \"month\": $month}}}}"
  sleep 60  # Wait for previous job to complete
done
```

### Verifying Backfill Success

After backfilling, verify the data loaded:

```bash
# Check trip counts by month
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb', read_only=True)
result = conn.execute('''
  SELECT
    DATE_TRUNC('month', pickup_datetime) as month,
    COUNT(*) as trips
  FROM core_core.fct_trips
  GROUP BY DATE_TRUNC('month', pickup_datetime)
  ORDER BY month
''').fetchdf()
print(result)
"
```

Expected output should show trips for the backfilled months.

### Performance Notes

| Method | Time (32M trips) | When to Use |
|--------|------------------|-------------|
| Full Refresh | ~30 seconds | Backfilling any historical month |
| Date Range | ~10-15 seconds | Backfilling recent months (within 3 months) |
| Normal Incremental | ~3-5 seconds | Loading new months (forward-loading) |

Times are for DuckDB. Snowflake/BigQuery will be slower but relative speedup is similar.

### Common Errors

**Error: "No trips found for YYYY-MM"**
```
❌ No trips found for 2025-05 in fct_trips!

This usually means:
1. You are backfilling a historical month (month < current max date)
2. The incremental filter excluded the data

Solution: Re-run with full_refresh=True or use the backfill_monthly_data job.
```

**Solution:** Use the backfill job or add `--full-refresh` flag.

## Next Steps

- **Phase 9**: Add Great Expectations for data quality checks
- **Phase 10**: Enhance documentation and add usage examples
- **Future**: Add sensors for event-driven pipeline triggers
- **Future**: Add alerting for pipeline failures
