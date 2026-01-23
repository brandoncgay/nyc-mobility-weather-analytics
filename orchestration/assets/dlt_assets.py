"""
DLT ingestion assets for NYC Mobility & Weather Analytics.

This module defines Dagster assets for DLT data ingestion from:
- NYC TLC (Yellow Taxi, FHV)
- CitiBike System Data
- Open-Meteo Weather API
"""

import subprocess
from pathlib import Path

from dagster import AssetExecutionContext, Output, asset

# Get the absolute path to the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
INGESTION_SCRIPT = PROJECT_ROOT / "src" / "ingestion" / "run_pipeline.py"


@asset(
    name="dlt_yellow_taxi_raw",
    description="Ingest yellow taxi data from NYC TLC via DLT",
    group_name="ingestion",
    compute_kind="dlt",
)
def dlt_yellow_taxi_raw(context: AssetExecutionContext) -> Output[dict]:
    """
    Ingest yellow taxi trip data from NYC TLC using DLT.

    This asset:
    - Downloads Parquet files from NYC TLC
    - Loads data into DuckDB raw_data schema
    - Handles deduplication and data quality

    Returns row count and status.
    """
    context.log.info("Starting yellow taxi data ingestion...")

    # Run DLT pipeline for taxi data only
    result = subprocess.run(
        [
            "uv", "run", "python",
            str(INGESTION_SCRIPT),
            "--sources", "taxi",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        context.log.error(f"DLT ingestion failed: {result.stderr}")
        raise RuntimeError(f"Yellow taxi ingestion failed: {result.stderr}")

    context.log.info(f"Yellow taxi ingestion output: {result.stdout}")

    # Parse row count from output (if available)
    # For now, return success status
    metadata = {
        "status": "success",
        "source": "NYC TLC Yellow Taxi",
        "output": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
    }

    return Output(metadata, metadata=metadata)


@asset(
    name="dlt_citibike_raw",
    description="Ingest CitiBike trip data via DLT",
    group_name="ingestion",
    compute_kind="dlt",
)
def dlt_citibike_raw(context: AssetExecutionContext) -> Output[dict]:
    """
    Ingest CitiBike trip data using DLT.

    This asset:
    - Downloads CSV files from CitiBike System Data
    - Loads data into DuckDB raw_data schema
    - Standardizes schema across months

    Returns row count and status.
    """
    context.log.info("Starting CitiBike data ingestion...")

    result = subprocess.run(
        [
            "uv", "run", "python",
            str(INGESTION_SCRIPT),
            "--sources", "citibike",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        context.log.error(f"DLT ingestion failed: {result.stderr}")
        raise RuntimeError(f"CitiBike ingestion failed: {result.stderr}")

    context.log.info(f"CitiBike ingestion output: {result.stdout}")

    metadata = {
        "status": "success",
        "source": "CitiBike System Data",
        "output": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
    }

    return Output(metadata, metadata=metadata)


@asset(
    name="dlt_weather_raw",
    description="Ingest weather data from Open-Meteo API via DLT",
    group_name="ingestion",
    compute_kind="dlt",
)
def dlt_weather_raw(context: AssetExecutionContext) -> Output[dict]:
    """
    Ingest hourly weather data from Open-Meteo API using DLT.

    This asset:
    - Fetches hourly weather data for NYC (Lower Manhattan)
    - Loads data into DuckDB raw_data schema
    - Provides temperature, precipitation, wind, humidity metrics

    Returns row count and status.
    """
    context.log.info("Starting weather data ingestion...")

    result = subprocess.run(
        [
            "uv", "run", "python",
            str(INGESTION_SCRIPT),
            "--sources", "weather",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        context.log.error(f"DLT ingestion failed: {result.stderr}")
        raise RuntimeError(f"Weather ingestion failed: {result.stderr}")

    context.log.info(f"Weather ingestion output: {result.stdout}")

    metadata = {
        "status": "success",
        "source": "Open-Meteo Weather API",
        "output": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
    }

    return Output(metadata, metadata=metadata)


@asset(
    name="dlt_ingestion_complete",
    description="Marker asset indicating all DLT ingestion is complete",
    group_name="ingestion",
)
def dlt_ingestion_complete(
    context: AssetExecutionContext,
    dlt_yellow_taxi_raw: dict,
    dlt_citibike_raw: dict,
    dlt_weather_raw: dict,
) -> Output[dict]:
    """
    Marker asset that depends on all DLT ingestion assets.

    This ensures all raw data is loaded before dbt transformations begin.
    """
    context.log.info("All DLT ingestion complete!")
    context.log.info(f"Yellow Taxi: {dlt_yellow_taxi_raw['status']}")
    context.log.info(f"CitiBike: {dlt_citibike_raw['status']}")
    context.log.info(f"Weather: {dlt_weather_raw['status']}")

    summary = {
        "yellow_taxi": dlt_yellow_taxi_raw,
        "citibike": dlt_citibike_raw,
        "weather": dlt_weather_raw,
        "status": "all_complete",
    }

    return Output(summary, metadata={"status": "complete"})
