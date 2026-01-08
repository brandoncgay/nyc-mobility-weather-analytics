# Monthly Ingestion Workflow Guide

**Using Dagster to load and test one month at a time**

## Overview

The monthly ingestion workflow provides a structured way to load historical data one month at a time with automatic testing and validation.

**Workflow**: DLT Ingestion → dbt Transformation (Incremental) → Data Validation

**Benefits**:
- ✅ Load one month at a time (controlled, testable)
- ✅ Automatic dbt incremental transformations
- ✅ Data validation after each month
- ✅ View progress and logs in Dagster UI
- ✅ Retry failed months easily

---

## Quick Start

### 1. Start Dagster UI

```bash
poetry run dagster dev -w orchestration/workspace.yaml
```

Then open http://localhost:3000

### 2. Navigate to Monthly Ingestion Job

1. Go to **Jobs** tab
2. Find **monthly_ingestion**
3. Click **Launchpad**

### 3. Configure the Month

In the launchpad, you'll see a config editor. Modify the month/year:

```yaml
ops:
  monthly_dlt_ingestion:
    config:
      year: 2025
      month: 9  # September
      sources: "taxi,citibike,weather"
```

### 4. Launch the Job

Click **Launch Run**

Dagster will:
1. ✅ Ingest September 2025 data (DLT merge - idempotent)
2. ✅ Run dbt transformations (incremental - fast!)
3. ✅ Validate data loaded correctly
4. ✅ Show you results and logs

---

## Loading Multiple Months

### Method 1: Load Through UI (Recommended for Learning)

Repeat the process for each month:

```yaml
# Run 1: September
ops:
  monthly_dlt_ingestion:
    config:
      year: 2025
      month: 9
      sources: "taxi,citibike,weather"

# Run 2: October (after September completes)
ops:
  monthly_dlt_ingestion:
    config:
      year: 2025
      month: 10
      sources: "taxi,citibike,weather"

# Run 3: November (after October completes)
ops:
  monthly_dlt_ingestion:
    config:
      year: 2025
      month: 11
      sources: "taxi,citibike,weather"
```

### Method 2: CLI Backfill Script

Create a backfill script:

```bash
#!/bin/bash
# scripts/dagster_backfill.sh

# Load months 7-12 for 2025
for month in {7..12}; do
    echo "Loading month $month..."

    poetry run dagster job execute \
        -m orchestration \
        -j monthly_ingestion \
        -c <(cat <<EOF
ops:
  monthly_dlt_ingestion:
    config:
      year: 2025
      month: $month
      sources: "taxi,citibike,weather"
EOF
)

    echo "Month $month complete!"
    sleep 5  # Brief pause between months
done
```

Make it executable:
```bash
chmod +x scripts/dagster_backfill.sh
./scripts/dagster_backfill.sh
```

### Method 3: Python Script

Create `scripts/dagster_monthly_backfill.py`:

```python
"""Run monthly backfill via Dagster programmatically."""

from dagster import DagsterInstance, execute_job
from orchestration import defs

def backfill_months(year: int, months: list[int], sources: str = "taxi,citibike,weather"):
    """Load multiple months sequentially."""

    instance = DagsterInstance.get()

    for month in months:
        print(f"Loading {year}-{month:02d}...")

        result = execute_job(
            defs.get_job_def("monthly_ingestion"),
            instance=instance,
            run_config={
                "ops": {
                    "monthly_dlt_ingestion": {
                        "config": {
                            "year": year,
                            "month": month,
                            "sources": sources,
                        }
                    }
                }
            },
        )

        if result.success:
            print(f"✓ {year}-{month:02d} completed successfully")
        else:
            print(f"✗ {year}-{month:02d} failed")
            break

    print("Backfill complete!")

# Example usage
if __name__ == "__main__":
    # Load July-December 2025
    backfill_months(2025, [7, 8, 9, 10, 11, 12])
```

Run it:
```bash
poetry run python scripts/dagster_monthly_backfill.py
```

---

## Common Use Cases

### Use Case 1: Load Last 3 Months

```yaml
# Month 1: October
ops:
  monthly_dlt_ingestion:
    config:
      year: 2025
      month: 10
      sources: "taxi,citibike,weather"

# Then repeat for months 11 and 12
```

### Use Case 2: Load Only Weather for Multiple Months

```yaml
ops:
  monthly_dlt_ingestion:
    config:
      year: 2025
      month: 9
      sources: "weather"  # Only weather
```

### Use Case 3: Load Specific Month from 2024

```yaml
ops:
  monthly_dlt_ingestion:
    config:
      year: 2024
      month: 12
      sources: "taxi,citibike,weather"
```

### Use Case 4: Reload a Month (Fix Data Issue)

```yaml
# Safe to rerun - DLT merge is idempotent
ops:
  monthly_dlt_ingestion:
    config:
      year: 2025
      month: 10
      sources: "taxi,citibike,weather"
```

---

## Monitoring & Validation

### View Progress in Dagster UI

1. **Runs** tab shows all executions
2. Click a run to see:
   - Asset execution logs
   - Data validation results
   - Test pass/fail counts
   - Trip counts by mode

### Check Validation Results

After each run completes, check the **monthly_data_validation** asset:

- Total trips loaded
- Breakdown by mode (taxi/FHV/CitiBike)
- Average distance and duration
- Data quality flags

### Query the Data

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
conn.close()
"
```

---

## Troubleshooting

### Issue: Job Fails at DLT Ingestion

**Check**: Dagster logs for the error message

**Common causes**:
- Network issue downloading data
- Invalid month/year combination
- Data source unavailable

**Solution**: Retry the job for that month

### Issue: dbt Transformation Fails

**Check**: dbt test results in logs

**Common causes**:
- Data quality test failures
- Schema changes

**Solution**:
```bash
# Run dbt debug
cd dbt && poetry run dbt debug

# Run tests manually
poetry run dbt test

# Full refresh if needed
poetry run dbt build --full-refresh
```

### Issue: No Data in Validation

**Check**: `monthly_data_validation` asset shows 0 trips

**Common causes**:
- DLT didn't actually load data
- Month/year has no available data

**Solution**: Check raw tables:
```bash
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb', read_only=True)
print(conn.execute('SELECT COUNT(*) FROM raw_data.yellow_taxi').fetchone())
conn.close()
"
```

---

## Best Practices

### 1. **Load Recent Months First**

```bash
# Start with most recent data
# Month: 12, then 11, then 10...
```

### 2. **Monitor Each Month**

Don't queue up 12 months and walk away. Check each month completes successfully.

### 3. **Use Dagster UI for First Time**

Get familiar with the UI before automating via scripts.

### 4. **Check Validation**

Always review the validation results after each month.

### 5. **Full Refresh After Backfill**

After loading all historical data, do one full refresh:

```bash
cd dbt && poetry run dbt build --full-refresh
```

This ensures all dimension joins are complete.

---

## Performance Expectations

| Operation | First Month | Subsequent Months |
|-----------|-------------|-------------------|
| **DLT Ingestion** | ~5-7 minutes | ~5-7 minutes |
| **dbt Transform** | ~30 seconds (full) | <1 second (incremental) |
| **Validation** | ~1 second | ~1 second |
| **Total per Month** | ~6-8 minutes | ~6 minutes |

**For 6 months**: ~36-48 minutes total

---

## Advanced: Automated Scheduled Backfill

Create a schedule to automatically load one month per day:

```python
# orchestration/schedules/monthly_backfill.py

from dagster import schedule, RunRequest

@schedule(
    job=monthly_ingestion_job,
    cron_schedule="0 2 * * *",  # 2 AM daily
)
def monthly_backfill_schedule(context):
    """Load one month per day automatically."""

    # Define months to backfill
    months_to_load = [
        (2025, 7),
        (2025, 8),
        (2025, 9),
        (2025, 10),
        (2025, 11),
        (2025, 12),
    ]

    # Get current cursor (which month we're on)
    cursor = context.cursor or 0
    cursor_int = int(cursor)

    if cursor_int >= len(months_to_load):
        # All months loaded
        return

    year, month = months_to_load[cursor_int]

    return RunRequest(
        run_key=f"{year}-{month:02d}",
        run_config={
            "ops": {
                "monthly_dlt_ingestion": {
                    "config": {
                        "year": year,
                        "month": month,
                        "sources": "taxi,citibike,weather",
                    }
                }
            }
        },
        cursor=str(cursor_int + 1),
    )
```

---

## Example: Load Q3 & Q4 2025

```bash
# Start Dagster UI
poetry run dagster dev -w orchestration/workspace.yaml

# In UI, launch monthly_ingestion job 6 times:

# Run 1: July
month: 7

# Run 2: August
month: 8

# Run 3: September
month: 9

# Run 4: October
month: 10

# Run 5: November
month: 11

# Run 6: December
month: 12

# Verify in database:
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb', read_only=True)
result = conn.execute('''
    SELECT
        DATE_TRUNC('month', pickup_datetime) as month,
        COUNT(*) as trips
    FROM core_core.fct_trips
    GROUP BY 1
    ORDER BY 1
''').fetchdf()
print('Loaded months:')
print(result)
print(f\"\\nTotal trips: {result['trips'].sum():,}\")
conn.close()
"
```

---

## Summary

**Dagster Monthly Ingestion Workflow**:
1. Start Dagster UI
2. Navigate to `monthly_ingestion` job
3. Configure year/month in launchpad
4. Launch and monitor
5. Review validation results
6. Repeat for next month

**Benefits**:
- ✅ Controlled, one month at a time
- ✅ Automatic testing and validation
- ✅ Full visibility in Dagster UI
- ✅ Incremental and idempotent
- ✅ Easy to retry failed months

---

**Ready to load your historical data?** Start the Dagster UI and begin with your first month!
