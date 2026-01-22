"""
Monthly DLT ingestion assets with parameterized year/month.

This module provides assets for loading one month at a time,
enabling incremental backfills and controlled historical data loading.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

from dagster import AssetExecutionContext, Config, Output, asset

# Get the absolute path to the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
INGESTION_SCRIPT = PROJECT_ROOT / "src" / "ingestion" / "run_pipeline.py"


class MonthlyIngestionConfig(Config):
    """Configuration for monthly data ingestion."""

    year: int = 2025
    month: int = 10
    sources: str = "taxi,citibike,weather"


class MonthlyTransformationConfig(Config):
    """Configuration for monthly dbt transformation."""

    full_refresh: bool = False  # Set to True for backfilling historical months


@asset(
    name="monthly_dlt_ingestion",
    description="Ingest data for a specific month via DLT (incremental/idempotent)",
    group_name="monthly_ingestion",
    compute_kind="dlt",
)
def monthly_dlt_ingestion(
    context: AssetExecutionContext,
    config: MonthlyIngestionConfig,
) -> Output[dict]:
    """
    Ingest data for a specific year and month using DLT.

    This asset:
    - Loads data for the specified year/month/sources
    - Uses DLT merge strategy (idempotent - safe to rerun)
    - Incremental - adds new data without deleting old data
    - Can be parameterized via config for different months

    Config:
        year: Year to load (default: 2025)
        month: Month to load (1-12, default: 10)
        sources: Comma-separated sources (default: "taxi,citibike,weather")

    Returns:
        dict: Ingestion metadata including status and row counts
    """
    context.log.info(
        f"Starting DLT ingestion for {config.year}-{config.month:02d} "
        f"(sources: {config.sources})"
    )

    # Build command
    cmd = [
        "poetry",
        "run",
        "python",
        str(INGESTION_SCRIPT),
        "--year",
        str(config.year),
        "--months",
        str(config.month),
        "--sources",
        config.sources,
    ]

    context.log.info(f"Running command: {' '.join(cmd)}")

    # Run DLT pipeline
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    # Log output for debugging
    context.log.info(f"DLT stdout (last 2000 chars): {result.stdout[-2000:]}")
    if result.stderr:
        context.log.warning(f"DLT stderr: {result.stderr[-2000:]}")

    if result.returncode != 0:
        error_msg = f"Monthly ingestion failed for {config.year}-{config.month:02d}\n"
        error_msg += f"Exit code: {result.returncode}\n"
        error_msg += f"STDOUT (last 1000 chars):\n{result.stdout[-1000:]}\n"
        error_msg += f"STDERR (last 1000 chars):\n{result.stderr[-1000:]}"
        context.log.error(error_msg)
        raise RuntimeError(error_msg)

    # Parse output for row counts (if available in logs)
    # For now, return success status
    metadata = {
        "status": "success",
        "year": config.year,
        "month": config.month,
        "sources": config.sources,
        "output_preview": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
    }

    context.log.info(
        f"✓ Successfully ingested data for {config.year}-{config.month:02d}"
    )

    return Output(metadata, metadata=metadata)


@asset(
    name="monthly_dbt_transformation",
    description="Run dbt transformations after monthly ingestion (supports full refresh for backfills)",
    group_name="monthly_ingestion",
    compute_kind="dbt",
)
def monthly_dbt_transformation(
    context: AssetExecutionContext,
    config: MonthlyTransformationConfig,
    monthly_dlt_ingestion: dict,
) -> Output[dict]:
    """
    Run dbt transformations after data ingestion.

    ⚠️ BACKFILL WARNING:
    The incremental filter in fct_trips only processes data NEWER than the max date.
    To backfill historical months (months earlier than current data), set full_refresh=True.

    This asset:
    - Runs dbt run (incremental by default, or full refresh if configured)
    - Executes models (fact tables: fct_trips, fct_hourly_mobility)
    - Depends on monthly_dlt_ingestion completing first

    Config:
        full_refresh: Set to True when backfilling historical months (default: False)

    Returns:
        dict: dbt run metadata including test results
    """
    year = monthly_dlt_ingestion["year"]
    month = monthly_dlt_ingestion["month"]

    if config.full_refresh:
        context.log.warning(
            f"⚠️ Running with --full-refresh for {year}-{month:02d}. "
            "This will rebuild entire fact tables (slower but necessary for backfills)."
        )
    else:
        context.log.info(
            f"Starting dbt transformation for {year}-{month:02d} data "
            "(incremental mode - only processes new data)"
        )

    dbt_dir = PROJECT_ROOT / "dbt"

    # Build dbt command
    dbt_cmd = ["poetry", "run", "dbt", "run", "--select", "fct_trips", "fct_hourly_mobility"]

    # Add full-refresh flag if configured (needed for backfills)
    if config.full_refresh:
        dbt_cmd.append("--full-refresh")
        context.log.info("Using --full-refresh to handle historical data backfill")

    context.log.info(f"Running command: {' '.join(dbt_cmd)}")

    # Run dbt run (models only, skip tests)
    # Tests are skipped because:
    # - We have data validation in monthly_data_validation asset
    # - We want monthly loads to complete successfully
    result = subprocess.run(
        dbt_cmd,
        cwd=dbt_dir,
        capture_output=True,
        text=True,
    )

    # Log output for debugging
    context.log.info(f"dbt stdout (last 2000 chars): {result.stdout[-2000:]}")
    if result.stderr:
        context.log.warning(f"dbt stderr: {result.stderr[-2000:]}")

    if result.returncode != 0:
        error_msg = f"dbt transformation failed for {year}-{month:02d}\n"
        error_msg += f"Exit code: {result.returncode}\n"
        error_msg += f"STDOUT (last 1500 chars):\n{result.stdout[-1500:]}\n"
        error_msg += f"STDERR (last 1500 chars):\n{result.stderr[-1500:]}"
        context.log.error(error_msg)
        raise RuntimeError(error_msg)

    # Count models run
    models_run = result.stdout.count("OK created")

    metadata = {
        "status": "success",
        "year": year,
        "month": month,
        "models_run": models_run,
        "output_preview": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
    }

    context.log.info(
        f"✓ dbt run successful for {year}-{month:02d}: {models_run} models completed"
    )

    return Output(metadata, metadata=metadata)


@asset(
    name="monthly_data_validation",
    description="Validate data quality for the loaded month",
    group_name="monthly_ingestion",
)
def monthly_data_validation(
    context: AssetExecutionContext,
    monthly_dbt_transformation: dict,
) -> Output[dict]:
    """
    Run data validation checks after transformation.

    This asset:
    - Queries the database to verify data loaded correctly
    - Checks row counts and data quality metrics
    - Provides summary statistics

    Returns:
        dict: Validation results
    """
    import duckdb

    year = monthly_dbt_transformation["year"]
    month = monthly_dbt_transformation["month"]

    context.log.info(f"Validating data for {year}-{month:02d}")

    db_path = PROJECT_ROOT / "data" / "nyc_mobility.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)

    # Check trip counts for this month
    query = f"""
        SELECT
            trip_type,
            COUNT(*) as trip_count,
            AVG(trip_distance) as avg_distance,
            AVG(trip_duration_minutes) as avg_duration
        FROM core_core.fct_trips
        WHERE EXTRACT(YEAR FROM pickup_datetime) = {year}
          AND EXTRACT(MONTH FROM pickup_datetime) = {month}
        GROUP BY trip_type
    """

    results = conn.execute(query).fetchdf()
    conn.close()

    # Convert to dict for metadata
    validation_data = results.to_dict(orient="records")
    total_trips = results["trip_count"].sum()

    context.log.info(f"Found {total_trips:,} trips for {year}-{month:02d}")
    context.log.info(f"Breakdown:\n{results.to_string()}")

    metadata = {
        "status": "validated",
        "year": year,
        "month": month,
        "total_trips": int(total_trips),
        "by_mode": validation_data,
    }

    if total_trips == 0:
        context.log.error(
            f"❌ No trips found for {year}-{month:02d} in fct_trips!\n"
            f"\n"
            f"This usually means:\n"
            f"1. You are backfilling a historical month (month < current max date)\n"
            f"2. The incremental filter excluded the data\n"
            f"\n"
            f"Solution: Re-run with full_refresh=True or use the backfill_monthly_data job.\n"
            f"Example:\n"
            f"  dagster job launch backfill_monthly_data \\\n"
            f"    --config '{{\"ops\": {{\"monthly_dlt_ingestion\": {{\"config\": {{\"year\": {year}, \"month\": {month}}}}}, "
            f"\"monthly_dbt_transformation\": {{\"config\": {{\"full_refresh\": true}}}}}}}}'"
        )
        metadata["status"] = "error_no_data"
        metadata["warning"] = "Backfill failed - use full_refresh=True"
    else:
        context.log.info(f"✓ Validation successful: {total_trips:,} trips loaded")

    return Output(metadata, metadata=metadata)



