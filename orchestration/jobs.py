"""
Dagster job definitions for NYC Mobility & Weather Analytics.

Jobs orchestrate the execution order of assets, ensuring:
1. DLT ingestion completes first
2. dbt transformations run after data is loaded
3. Validation runs after transformations
"""

from dagster import AssetSelection, define_asset_job

# Full pipeline job: DLT Ingestion → dbt Transformation
full_pipeline_job = define_asset_job(
    name="full_pipeline",
    description="Run complete pipeline: DLT ingestion → dbt transformation",
    selection=AssetSelection.all(),
)

# DLT ingestion only job
dlt_ingestion_job = define_asset_job(
    name="dlt_ingestion",
    description="Run DLT data ingestion only (yellow taxi, citibike, weather)",
    selection=AssetSelection.groups("ingestion"),
)

# dbt transformation only job (assumes data already loaded)
dbt_transformation_job = define_asset_job(
    name="dbt_transformation",
    description="Run dbt transformations only (assumes raw data exists)",
    selection=AssetSelection.all() - AssetSelection.groups("ingestion"),
)

# Monthly ingestion job: Load one month at a time with validation
# ⚠️ Use this for loading NEW months (months > current max date)
# For historical backfills, use backfill_monthly_data instead
monthly_ingestion_job = define_asset_job(
    name="monthly_ingestion",
    description="Load data for one month: DLT ingestion → dbt transformation (incremental) → validation. Use for forward-loading only.",
    selection=AssetSelection.groups("monthly_ingestion"),
    config={
        "ops": {
            "monthly_dlt_ingestion": {
                "config": {
                    "year": 2025,
                    "month": 10,
                    "sources": "taxi,citibike,weather",
                }
            },
            "monthly_dbt_transformation": {
                "config": {
                    "full_refresh": False,  # Incremental mode
                }
            }
        }
    },
)

# Backfill job: Load historical data with full refresh
# Use this when loading months EARLIER than your current data range
backfill_monthly_data = define_asset_job(
    name="backfill_monthly_data",
    description="""
    Backfill historical data for a specific month.

    ⚠️ IMPORTANT: Use this job when loading months EARLIER than your current max date.

    This job:
    1. Runs DLT ingestion for the specified month (idempotent - safe to rerun)
    2. Runs dbt with --full-refresh for fact tables (rebuilds entire table)
    3. Validates data loaded correctly

    Why full refresh is needed:
    - fct_trips incremental filter: WHERE pickup_datetime > max(pickup_datetime)
    - Only processes data NEWER than current max date
    - Historical months would be filtered out without full refresh

    Example usage:
    To backfill May 2025 when you already have June-November:

    dagster job launch backfill_monthly_data \\
      --config '{"ops": {"monthly_dlt_ingestion": {"config": {"year": 2025, "month": 5}}}}'

    Performance note:
    Full refresh processes all trips (~32M rows). Takes ~30 seconds in DuckDB.
    """,
    selection=AssetSelection.groups("monthly_ingestion"),
    config={
        "ops": {
            "monthly_dlt_ingestion": {
                "config": {
                    "year": 2025,
                    "month": 5,  # Example: backfill May
                    "sources": "taxi,citibike,weather",
                }
            },
            "monthly_dbt_transformation": {
                "config": {
                    "full_refresh": True,  # Required for backfills
                }
            }
        }
    },
)
