"""
Dagster orchestration for NYC Mobility & Weather Analytics Platform.

This package contains:
- dbt asset definitions
- Resource configurations (DuckDB, dbt)
- Schedules and sensors for pipeline orchestration
- Logging and monitoring configuration
- Monthly ingestion workflow for incremental backfills
"""

from dagster import Definitions

from .assets.dbt_assets import dbt_analytics_assets
from .assets.dlt_assets import (
    dlt_citibike_raw,
    dlt_ingestion_complete,
    dlt_weather_raw,
    dlt_yellow_taxi_raw,
)
from .assets.monthly_ingestion import (
    monthly_data_validation,
    monthly_dbt_transformation,
    monthly_dlt_ingestion,
    monthly_ge_validation,
)
from .jobs import (
    dbt_transformation_job,
    dlt_ingestion_job,
    full_pipeline_job,
    monthly_ingestion_job,
)
from .resources import resources_by_env
from .schedules import daily_dbt_schedule

# Define all Dagster definitions
# Pipeline flow: DLT Ingestion → dbt Transformation → Validation
defs = Definitions(
    assets=[
        # DLT ingestion assets (run first)
        dlt_yellow_taxi_raw,
        dlt_citibike_raw,
        dlt_weather_raw,
        dlt_ingestion_complete,
        # dbt transformation assets (depend on ingestion)
        dbt_analytics_assets,
        # Monthly ingestion workflow assets
        monthly_dlt_ingestion,
        monthly_dbt_transformation,
        monthly_data_validation,
        monthly_ge_validation,
    ],
    jobs=[
        full_pipeline_job,
        dlt_ingestion_job,
        dbt_transformation_job,
        monthly_ingestion_job,
    ],
    resources=resources_by_env["dev"],
    schedules=[daily_dbt_schedule],
)
