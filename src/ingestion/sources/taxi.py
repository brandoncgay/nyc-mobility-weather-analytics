"""DLT source for NYC TLC taxi trip data (Yellow Taxi and For-Hire Vehicles)."""

import dlt
import pyarrow.parquet as pq
import requests
from io import BytesIO
from typing import Iterator

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dlt.source(name="nyc_tlc")
def taxi_source(year: int, months: list[int], taxi_types: list[str]):
    """DLT source for NYC TLC taxi data.

    Args:
        year: Year to download data for
        months: List of month numbers (1-12)
        taxi_types: List of taxi types to download ("yellow", "fhv")

    Yields:
        Taxi trip data resources
    """

    @dlt.resource(
        name="yellow_taxi",
        write_disposition="merge",
        primary_key=["tpep_pickup_datetime", "tpep_dropoff_datetime", "vendor_id", "pu_location_id"]
    )
    def yellow_taxi() -> Iterator:
        """Download and yield Yellow Taxi trip data.

        Yellow taxi primarily serves Manhattan and airports.
        Data includes pickup/dropoff times, locations, fares, and trip details.
        """
        if "yellow" not in taxi_types:
            return

        base_url = "https://d37ci6vzurychx.cloudfront.net/trip-data"

        for month in months:
            url = f"{base_url}/yellow_tripdata_{year}-{month:02d}.parquet"
            logger.info(f"Downloading Yellow Taxi data: {year}-{month:02d}")

            try:
                # Download Parquet file
                response = requests.get(url, timeout=120)
                response.raise_for_status()

                # Read Parquet file from bytes
                table = pq.read_table(BytesIO(response.content))

                # Convert to Python dicts for DLT
                records = table.to_pylist()

                logger.info(f"Loaded {len(records):,} Yellow Taxi records for {year}-{month:02d}")

                # Yield all records
                yield records

            except Exception as e:
                logger.error(f"Failed to download Yellow Taxi data for {year}-{month:02d}: {e}")
                # Continue with other months even if one fails
                continue

    @dlt.resource(
        name="fhv_taxi",
        write_disposition="merge",
        primary_key=["pickup_datetime", "drop_off_datetime", "dispatching_base_num"]
    )
    def fhv_taxi() -> Iterator:
        """Download and yield For-Hire Vehicle (FHV) trip data.

        FHV includes Uber, Lyft, and other app-based ride services.
        Data includes pickup/dropoff times and location IDs.
        """
        if "fhv" not in taxi_types:
            return

        base_url = "https://d37ci6vzurychx.cloudfront.net/trip-data"

        for month in months:
            url = f"{base_url}/fhv_tripdata_{year}-{month:02d}.parquet"
            logger.info(f"Downloading FHV data: {year}-{month:02d}")

            try:
                # Download Parquet file
                response = requests.get(url, timeout=120)
                response.raise_for_status()

                # Read Parquet file from bytes
                table = pq.read_table(BytesIO(response.content))

                # Convert to Python dicts for DLT
                records = table.to_pylist()

                logger.info(f"Loaded {len(records):,} FHV records for {year}-{month:02d}")

                # Yield all records
                yield records

            except Exception as e:
                logger.error(f"Failed to download FHV data for {year}-{month:02d}: {e}")
                # Continue with other months even if one fails
                continue

    # Return the resources to ingest
    resources = []
    if "yellow" in taxi_types:
        resources.append(yellow_taxi)
    if "fhv" in taxi_types:
        resources.append(fhv_taxi)

    return resources
