"""
dbt assets for NYC Mobility & Weather Analytics.

This module loads all dbt models from the project as Dagster assets,
creating a data lineage graph and enabling orchestration.
"""

import os
from pathlib import Path

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets

# Get the absolute path to the dbt project directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DBT_PROJECT_DIR = PROJECT_ROOT / "dbt"
DBT_PROFILES_DIR = PROJECT_ROOT / "dbt"

# Verify the dbt project exists
if not (DBT_PROJECT_DIR / "dbt_project.yml").exists():
    raise FileNotFoundError(
        f"dbt project not found at {DBT_PROJECT_DIR}. "
        "Please ensure the dbt project is in the correct location."
    )


@dbt_assets(
    manifest=DBT_PROJECT_DIR / "target" / "manifest.json",
)
def dbt_analytics_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    Dagster asset representing all dbt models in the analytics project.

    This asset will:
    1. Run all dbt models in dependency order
    2. Materialize dimension tables (dim_*)
    3. Materialize fact tables (fct_*)
    4. Make metrics available via the semantic layer

    The dbt project structure:
    - Staging (Bronze): Cleaned source data
    - Intermediate: Lightweight transformations (ephemeral)
    - Marts/Core (Silver): Dimension and fact tables
    - Semantic Layer (Gold): Metrics and semantic models
    """
    # Run all dbt models
    yield from dbt.cli(["build"], context=context).stream()
