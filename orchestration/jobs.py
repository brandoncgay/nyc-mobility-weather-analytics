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
monthly_ingestion_job = define_asset_job(
    name="monthly_ingestion",
    description="Load data for one month: DLT ingestion → dbt transformation → validation",
    selection=AssetSelection.groups("monthly_ingestion"),
    config={
        "ops": {
            "monthly_dlt_ingestion": {
                "config": {
                    "year": 2025,
                    "month": 10,
                    "sources": "taxi,citibike,weather",
                }
            }
        }
    },
)
