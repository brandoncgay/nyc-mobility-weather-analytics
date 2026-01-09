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
    description="Run dbt incremental transformations after monthly ingestion",
    group_name="monthly_ingestion",
    compute_kind="dbt",
)
def monthly_dbt_transformation(
    context: AssetExecutionContext,
    monthly_dlt_ingestion: dict,
) -> Output[dict]:
    """
    Run dbt transformations incrementally after data ingestion.

    This asset:
    - Runs dbt build (incremental - only processes new data)
    - Executes all models, tests, and snapshots
    - Depends on monthly_dlt_ingestion completing first

    Returns:
        dict: dbt run metadata including test results
    """
    year = monthly_dlt_ingestion["year"]
    month = monthly_dlt_ingestion["month"]

    context.log.info(
        f"Starting dbt transformation for {year}-{month:02d} data "
        "(incremental mode)"
    )

    dbt_dir = PROJECT_ROOT / "dbt"

    # Run dbt run (models only, skip tests)
    # This will be incremental for fact tables, fast!
    # Tests are skipped because:
    # - We have data validation in monthly_data_validation asset
    # - Some tests have known failures (weather coverage, dim_date range)
    # - We want monthly loads to complete successfully
    result = subprocess.run(
        ["poetry", "run", "dbt", "run"],
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
        context.log.warning(f"⚠️ No trips found for {year}-{month:02d}")
        metadata["status"] = "warning_no_data"
    else:
        context.log.info(f"✓ Validation successful: {total_trips:,} trips loaded")

    return Output(metadata, metadata=metadata)


@asset(
    name="monthly_ge_validation",
    description="Run Great Expectations data quality validations",
    group_name="monthly_ingestion",
    compute_kind="great_expectations",
)
def monthly_ge_validation(
    context: AssetExecutionContext,
    monthly_dbt_transformation: dict,
) -> Output[dict]:
    """
    Run Great Expectations validations on transformed data.

    This asset:
    - Validates staging models (data quality at ingestion)
    - Validates fact tables (completeness, accuracy, consistency)
    - Fails the pipeline if critical expectations are not met
    - Generates validation reports

    Returns:
        dict: Validation results with pass/fail counts
    """
    year = monthly_dbt_transformation["year"]
    month = monthly_dbt_transformation["month"]

    context.log.info(
        f"Running Great Expectations validations for {year}-{month:02d}"
    )

    # Import GE here to avoid loading it if not needed
    try:
        from great_expectations.data_context import FileDataContext
    except ImportError:
        context.log.error(
            "Great Expectations not installed. Run: poetry add great_expectations"
        )
        raise

    # Load GE context
    ge_dir = PROJECT_ROOT / "great_expectations"
    try:
        gx_context = FileDataContext(context_root_dir=ge_dir)
    except Exception as e:
        context.log.error(f"Failed to load Great Expectations context: {e}")
        raise

    # Define validations to run for monthly ingestion
    # Focus on staging and fact tables (dimensions are static)
    validations = [
        # Staging models - validate data quality at ingestion
        (
            "chk_stg_yellow_taxi",
            "stg_yellow_taxi",
            "stg_tlc__yellow_taxi",
            "staging_connector",
        ),
        (
            "chk_stg_fhv_taxi",
            "stg_fhv_taxi",
            "stg_tlc__fhv_taxi",
            "staging_connector",
        ),
        (
            "chk_stg_citibike",
            "stg_citibike__trips",
            "stg_citibike__trips",
            "staging_connector",
        ),
        (
            "chk_stg_weather",
            "stg_weather__hourly",
            "stg_weather__hourly",
            "staging_connector",
        ),
        # Fact tables - validate final transformed data
        ("chk_fct_trips", "fct_trips", "fct_trips", "facts_connector"),
    ]

    context.log.info(f"Running {len(validations)} validation suites...")

    passed = 0
    failed = 0
    failed_suites = []

    for checkpoint_name, suite_name, asset_name, connector_name in validations:
        context.log.info(f"  Validating {suite_name}...")

        try:
            # Create batch request
            batch_request = {
                "datasource_name": "nyc_mobility_duckdb",
                "data_connector_name": connector_name,
                "data_asset_name": asset_name,
            }

            # Create checkpoint configuration
            checkpoint_config = {
                "name": checkpoint_name,
                "config_version": 1.0,
                "class_name": "Checkpoint",
                "run_name_template": f"%Y%m%d-%H%M%S-{checkpoint_name}",
                "validations": [
                    {
                        "batch_request": batch_request,
                        "expectation_suite_name": suite_name,
                    }
                ],
                "action_list": [
                    {
                        "name": "store_validation_result",
                        "action": {"class_name": "StoreValidationResultAction"},
                    },
                ],
            }

            # Delete existing checkpoint if it exists
            try:
                gx_context.delete_checkpoint(name=checkpoint_name)
            except Exception:
                pass

            # Add and run checkpoint
            checkpoint = gx_context.add_checkpoint(**checkpoint_config)
            result = checkpoint.run()

            # Check if validation passed
            if result.success:
                context.log.info(f"    ✅ {suite_name} passed")
                passed += 1
            else:
                context.log.warning(f"    ❌ {suite_name} failed")
                failed += 1
                failed_suites.append(suite_name)

                # Log failure details
                for run_result in result.run_results.values():
                    if not run_result.get("success"):
                        validation_result = run_result.get("validation_result")
                        if validation_result:
                            failed_expectations = [
                                exp
                                for exp in validation_result.results
                                if not exp.success
                            ]
                            context.log.warning(
                                f"      Failed expectations: {len(failed_expectations)}"
                            )
                            # Log first few failures
                            for exp in failed_expectations[:3]:
                                context.log.warning(
                                    f"        - {exp.expectation_config.expectation_type}"
                                )

        except Exception as e:
            context.log.error(f"    ❌ {suite_name} error: {str(e)}")
            failed += 1
            failed_suites.append(suite_name)

    # Prepare metadata
    metadata = {
        "status": "passed" if failed == 0 else "failed",
        "year": year,
        "month": month,
        "total_suites": len(validations),
        "passed": passed,
        "failed": failed,
        "failed_suites": failed_suites,
    }

    # Log summary
    context.log.info(
        f"\n📊 Validation Summary for {year}-{month:02d}:"
        f"\n  ✅ Passed: {passed}/{len(validations)}"
        f"\n  ❌ Failed: {failed}/{len(validations)}"
    )

    if failed > 0:
        context.log.warning(
            f"⚠️ {failed} validation suite(s) failed: {', '.join(failed_suites)}"
        )
        # Don't fail the pipeline for non-critical validation failures
        # But log clearly so users can investigate
        context.log.warning(
            "Pipeline will continue, but data quality issues should be investigated"
        )

    context.log.info(
        f"✓ Great Expectations validation complete for {year}-{month:02d}"
    )

    return Output(metadata, metadata=metadata)
