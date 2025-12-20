"""DLT pipeline configuration for NYC Mobility data ingestion."""

import dlt
from dlt.destinations import duckdb

from src.utils.config import config


def get_pipeline() -> dlt.Pipeline:
    """Get configured DLT pipeline with DuckDB destination.

    Returns:
        Configured DLT pipeline instance
    """
    pipeline = dlt.pipeline(
        pipeline_name="nyc_mobility",
        destination=duckdb(credentials=config.duckdb_path),
        dataset_name="raw_data",
        progress="log",  # Show progress in logs
    )

    return pipeline


def get_pipeline_info(pipeline: dlt.Pipeline) -> dict:
    """Get information about the last pipeline run.

    Args:
        pipeline: DLT pipeline instance

    Returns:
        Dictionary with load information
    """
    return {
        "pipeline_name": pipeline.pipeline_name,
        "destination": pipeline.destination,
        "dataset_name": pipeline.dataset_name,
        "last_trace": pipeline.last_trace,
    }
