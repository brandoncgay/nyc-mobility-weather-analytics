"""
Dagster orchestration for NYC Mobility & Weather Analytics Platform.

This package contains:
- dbt asset definitions
- Resource configurations (DuckDB, dbt)
- Schedules and sensors for pipeline orchestration
- Logging and monitoring configuration
"""

from dagster import Definitions

from .assets.dbt_assets import dbt_analytics_assets
from .resources import resources_by_env
from .schedules import daily_dbt_schedule

# Define all Dagster definitions
defs = Definitions(
    assets=[dbt_analytics_assets],
    resources=resources_by_env["dev"],
    schedules=[daily_dbt_schedule],
)
