"""
Schedule definitions for pipeline orchestration.

Schedules include:
- Daily dbt build (runs all models and tests)
- Weekly full refresh (optional)
"""

from dagster import AssetSelection, ScheduleDefinition, define_asset_job

# Define a job that runs all dbt assets
dbt_build_job = define_asset_job(
    name="dbt_build_job",
    description="Build all dbt models, run tests, and update the semantic layer",
    selection=AssetSelection.all(),
)

# Daily schedule at 2 AM UTC
daily_dbt_schedule = ScheduleDefinition(
    name="daily_dbt_build",
    job=dbt_build_job,
    cron_schedule="0 2 * * *",  # Run at 2 AM UTC every day
    description="Daily dbt build: runs all staging, intermediate, and mart models with tests",
)

__all__ = ["daily_dbt_schedule", "dbt_build_job"]
