# Monthly Data Loading - Quick Start Guide

**Load and test historical data one month at a time using Dagster**

## ✓ Setup Complete

Your Dagster orchestration is now configured with:
- ✅ 4 monthly ingestion assets (DLT → dbt → Validation → Great Expectations)
- ✅ monthly_ingestion job
- ✅ Configurable year/month parameters
- ✅ Automatic incremental transformations
- ✅ Comprehensive data quality validation with Great Expectations

## ⚠️ Important: Stop the Dashboard First

**Before running Dagster jobs, you must stop the Streamlit dashboard if it's running.**

DuckDB only allows one write connection at a time. If the dashboard is running, data ingestion will fail with a database lock error.

```bash
# Stop the dashboard (Ctrl+C in the terminal where it's running)
# Or find and kill the process:
pkill -f "streamlit run dashboard.py"
```

## Method 1: Dagster UI (Recommended for First Use)

### Start Dagster

```bash
poetry run dagster dev -w orchestration/workspace.yaml
```

Open http://localhost:3000

### Load a Single Month

1. Navigate to **Jobs** tab → **monthly_ingestion**
2. Click **Launchpad**
3. Configure the month:

```yaml
ops:
  monthly_dlt_ingestion:
    config:
      year: 2025
      month: 10  # October
      sources: "taxi,citibike,weather"
```

4. Click **Launch Run**
5. Watch progress in real-time

### Load Multiple Months

Repeat the process for each month, changing only the `month` value:
- Run 1: `month: 10`
- Run 2: `month: 11`
- Run 3: `month: 12`

## Method 2: Python Backfill Script

Load multiple months automatically:

```bash
# Load Q4 2025 (October, November, December)
poetry run python scripts/dagster_monthly_backfill.py --year 2025 --months 10,11,12

# Load all of 2025
poetry run python scripts/dagster_monthly_backfill.py --year 2025 --months 1,2,3,4,5,6,7,8,9,10,11,12

# Load only weather for multiple months
poetry run python scripts/dagster_monthly_backfill.py --year 2025 --months 7,8,9 --sources weather

# Continue even if a month fails
poetry run python scripts/dagster_monthly_backfill.py --year 2025 --months 10,11,12 --continue-on-error
```

## What Happens During Each Run

1. **DLT Ingestion** (~5-7 minutes)
   - Downloads data for the specified month
   - Merges into DuckDB (idempotent - safe to rerun)
   - No data loss or duplicates

2. **dbt Transformation** (<1 second for incremental)
   - Processes only new data
   - Updates fact and dimension tables
   - Skips tests (tests run in GE step)

3. **Basic Validation** (~1 second)
   - Counts trips loaded
   - Shows breakdown by mode (taxi/FHV/CitiBike)
   - Validates data exists

4. **Great Expectations Validation** (~5-10 seconds) ⭐ NEW
   - Runs 5 comprehensive validation suites:
     - Staging models: yellow_taxi, fhv_taxi, citibike, weather
     - Fact tables: fct_trips
   - Checks data quality expectations:
     - Null checks on required fields
     - Unique key constraints
     - Value range validations (distances, amounts)
     - Trip metrics validity
   - Logs detailed failures if any
   - Pipeline continues even with warnings (investigate later)

## Monitoring

### View Run Progress

In Dagster UI:
- **Runs** tab shows all executions
- Click a run to see logs and validation results
- Green = success, Red = failed

### Verify Data Loaded

```bash
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb', read_only=True)
result = conn.execute('''
    SELECT
        DATE_TRUNC('month', pickup_datetime) as month,
        trip_type,
        COUNT(*) as trips
    FROM core_core.fct_trips
    GROUP BY 1, 2
    ORDER BY 1, 2
''').fetchdf()
print(result)
print(f\"\nTotal trips: {result['trips'].sum():,}\")
conn.close()
"
```

## Common Use Cases

### Load Last 3 Months of 2025

```bash
poetry run python scripts/dagster_monthly_backfill.py --year 2025 --months 10,11,12
```

### Reload a Month (Fix Data Issues)

Safe to rerun - DLT merge is idempotent:

```yaml
# In Dagster UI launchpad
ops:
  monthly_dlt_ingestion:
    config:
      year: 2025
      month: 10
      sources: "taxi,citibike,weather"
```

### Load Historical Data (2024)

```bash
poetry run python scripts/dagster_monthly_backfill.py --year 2024 --months 7,8,9,10,11,12
```

## Troubleshooting

### Issue: Database Lock Error

**Symptoms**: Error message contains "Could not set lock on file" or "Conflicting lock is held"

**Cause**: The Streamlit dashboard (or another process) has the database open

**Solution**: Stop all processes accessing the database:

```bash
# Stop Streamlit dashboard
pkill -f "streamlit run dashboard.py"

# Check for other processes
lsof | grep nyc_mobility.duckdb

# Then retry the Dagster job
```

### Issue: Job Fails at DLT Ingestion

**Solution**: Check Dagster logs for the specific error, then retry:

```bash
# Retry via UI or re-run the backfill script for that month
poetry run python scripts/dagster_monthly_backfill.py --year 2025 --months 10
```

### Issue: dbt Tests Fail

**Solution**: Run dbt manually to see specific test failures:

```bash
cd dbt
poetry run dbt test --select fct_trips
```

### Issue: No Data in Validation

**Check**: Verify raw tables have data:

```bash
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb', read_only=True)
print('Yellow taxi:', conn.execute('SELECT COUNT(*) FROM raw_data.yellow_taxi').fetchone())
print('CitiBike:', conn.execute('SELECT COUNT(*) FROM raw_data.trips').fetchone())
conn.close()
"
```

## Performance Expectations

| Operation | Time per Month |
|-----------|----------------|
| **DLT Ingestion** | ~5-7 minutes |
| **dbt Transform** | <1 second (incremental) |
| **Validation** | ~1 second |
| **Total** | ~6-8 minutes |

For 6 months: ~36-48 minutes total

## Next Steps

1. **Start with one month**: Test the workflow with a single month first
2. **Verify results**: Check validation output and query the data
3. **Scale up**: Once confident, load multiple months
4. **Monitor**: Always review validation results after each month

## Full Documentation

- **Detailed Guide**: `orchestration/MONTHLY_INGESTION_GUIDE.md`
- **Backfill Script**: `scripts/dagster_monthly_backfill.py --help`
- **Pipeline Architecture**: `docs/PIPELINE_ARCHITECTURE.md`

---

**Ready to load your data?** Start Dagster and begin with your first month!

```bash
poetry run dagster dev -w orchestration/workspace.yaml
```
