"""
Resource configurations for different environments.

Resources include:
- dbt CLI resource for running dbt commands
- DuckDB connection (managed by dbt)
- Logging configuration
"""

import os
from pathlib import Path

from dagster_dbt import DbtCliResource

# Get the absolute path to the dbt project directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DBT_PROJECT_DIR = PROJECT_ROOT / "dbt"
DBT_PROFILES_DIR = PROJECT_ROOT / "dbt"

# Development resources
dev_resources = {
    "dbt": DbtCliResource(
        project_dir=os.fspath(DBT_PROJECT_DIR),
        profiles_dir=os.fspath(DBT_PROFILES_DIR),
        target="dev",
    ),
}

# Production resources (same as dev for now, but can be customized)
prod_resources = {
    "dbt": DbtCliResource(
        project_dir=os.fspath(DBT_PROJECT_DIR),
        profiles_dir=os.fspath(DBT_PROFILES_DIR),
        target="dev",  # Update to "prod" when production target is configured
    ),
}

# Resource mapping by environment
resources_by_env = {
    "dev": dev_resources,
    "prod": prod_resources,
}

__all__ = ["resources_by_env", "dev_resources", "prod_resources"]
