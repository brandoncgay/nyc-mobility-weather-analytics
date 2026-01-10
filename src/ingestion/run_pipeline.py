"""Main script to run NYC Mobility data ingestion pipeline using DLT."""

import argparse
import sys
from typing import List

import dlt
from dlt.destinations import duckdb

from src.ingestion.sources.citibike import citibike_source
from src.ingestion.sources.taxi import taxi_source
from src.ingestion.sources.weather import weather_source
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_ingestion_pipeline(
    year: int, months: List[int], sources: List[str]
) -> None:
    """Run DLT ingestion pipeline for specified sources.

    Args:
        year: Year to ingest data for
        months: List of month numbers to ingest
        sources: List of source names to ingest

    Raises:
        ValueError: If invalid sources are specified
    """
    valid_sources = {"taxi", "citibike", "weather"}
    invalid = set(sources) - valid_sources

    if invalid:
        raise ValueError(
            f"Invalid sources: {invalid}. Valid sources are: {valid_sources}"
        )

    logger.info("=" * 80)
    logger.info("NYC Mobility Data Ingestion Pipeline")
    logger.info("=" * 80)
    logger.info(f"Year: {year}")
    logger.info(f"Months: {months}")
    logger.info(f"Sources: {sources}")
    logger.info(f"DuckDB Path: {config.duckdb_path}")
    logger.info("=" * 80)

    # Initialize DLT pipeline with DuckDB destination
    pipeline = dlt.pipeline(
        pipeline_name="nyc_mobility",
        destination=duckdb(credentials=config.duckdb_path),
        dataset_name="raw_data",
        progress="log",  # Show progress
    )

    logger.info(f"Pipeline initialized: {pipeline.pipeline_name}")

    # Run taxi ingestion if requested
    if "taxi" in sources:
        logger.info("\n" + "=" * 80)
        logger.info("INGESTING TAXI DATA (Yellow + FHV)")
        logger.info("=" * 80)

        try:
            taxi_data = taxi_source(year, months, ["yellow", "fhv"])
            info = pipeline.run(taxi_data)

            logger.info("Taxi ingestion completed successfully")
            logger.info(f"Load info: {info}")

        except Exception as e:
            logger.error(f"Taxi ingestion failed: {e}")
            logger.exception("Full traceback:")

    # Run CitiBike ingestion if requested
    if "citibike" in sources:
        logger.info("\n" + "=" * 80)
        logger.info("INGESTING CITIBIKE DATA")
        logger.info("=" * 80)

        try:
            citibike_data = citibike_source(year, months)
            info = pipeline.run(citibike_data)

            logger.info("CitiBike ingestion completed successfully")
            logger.info(f"Load info: {info}")

        except Exception as e:
            logger.error(f"CitiBike ingestion failed: {e}")
            logger.exception("Full traceback:")

    # Run weather ingestion if requested
    if "weather" in sources:
        logger.info("\n" + "=" * 80)
        logger.info("INGESTING WEATHER DATA")
        logger.info("=" * 80)

        try:
            # Using Open-Meteo API (free, no API key required)
            weather_data = weather_source(year, months)
            info = pipeline.run(weather_data)

            logger.info("Weather ingestion completed successfully")
            logger.info(f"Load info: {info}")

        except Exception as e:
                logger.error(f"Weather ingestion failed: {e}")
                logger.exception("Full traceback:")

    # Print pipeline summary
    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 80)

    try:
        trace = pipeline.last_trace
        logger.info(f"Last trace: {trace}")
    except Exception as e:
        logger.warning(f"Could not retrieve pipeline trace: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("INGESTION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Data stored in: {config.duckdb_path}")
    logger.info("You can now explore the data using:")
    logger.info("  - Jupyter notebooks in notebooks/")
    logger.info("  - DuckDB CLI: duckdb data/nyc_mobility.duckdb")
    logger.info("  - Python: import duckdb; conn = duckdb.connect('data/nyc_mobility.duckdb')")


def main() -> None:
    """CLI entry point for the ingestion pipeline."""
    parser = argparse.ArgumentParser(
        description="Run NYC Mobility data ingestion pipeline using DLT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest all sources for Q4 2023
  python src/ingestion/run_pipeline.py

  # Ingest only taxi data
  python src/ingestion/run_pipeline.py --sources taxi

  # Ingest specific months
  python src/ingestion/run_pipeline.py --months 1,2,3

  # Ingest taxi and citibike for a single month
  python src/ingestion/run_pipeline.py --months 10 --sources taxi,citibike
        """,
    )

    parser.add_argument(
        "--year",
        type=int,
        default=2023,
        help="Year to ingest data for (default: 2023)",
    )

    parser.add_argument(
        "--months",
        type=str,
        default="10,11,12",
        help="Comma-separated list of months to ingest (default: 10,11,12 for Q4)",
    )

    parser.add_argument(
        "--sources",
        type=str,
        default="taxi,citibike,weather",
        help="Comma-separated list of sources to ingest (default: taxi,citibike,weather)",
    )

    args = parser.parse_args()

    # Parse months
    try:
        months = [int(m.strip()) for m in args.months.split(",")]

        # Validate months
        for month in months:
            if month < 1 or month > 12:
                logger.error(f"Invalid month: {month}. Months must be between 1 and 12.")
                sys.exit(1)

    except ValueError as e:
        logger.error(f"Invalid months format: {args.months}. Use comma-separated numbers.")
        sys.exit(1)

    # Parse sources
    sources = [s.strip() for s in args.sources.split(",")]

    try:
        run_ingestion_pipeline(args.year, months, sources)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
