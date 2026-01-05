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

## Next Steps

- **Phase 9**: Add Great Expectations for data quality checks
- **Phase 10**: Enhance documentation and add usage examples
- **Future**: Add sensors for event-driven pipeline triggers
- **Future**: Add alerting for pipeline failures
