"""Data ingestion modules for NYC taxi, CitiBike, and weather data using DLT."""

from src.ingestion.dlt_config import get_pipeline, get_pipeline_info
from src.ingestion.run_pipeline import run_ingestion_pipeline
from src.ingestion.sources import citibike_source, taxi_source, weather_source

__all__ = [
    "taxi_source",
    "citibike_source",
    "weather_source",
    "get_pipeline",
    "get_pipeline_info",
    "run_ingestion_pipeline",
]
