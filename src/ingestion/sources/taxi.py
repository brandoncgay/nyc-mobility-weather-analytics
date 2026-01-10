"""DLT source for NYC TLC taxi trip data (Yellow Taxi and For-Hire Vehicles)."""

import dlt
import pyarrow.parquet as pq
import requests
from io import BytesIO
from typing import Iterator

from src.ingestion.errors import TransientError, PermanentError
from src.utils.logger import get_logger
from src.utils.retry import retry_on_transient_error

logger = get_logger(__name__)


@retry_on_transient_error(max_attempts=3, min_wait=2, max_wait=60)
def _download_month_data(url: str, year: int, month: int, taxi_type: str) -> list:
    """Download and parse single month of taxi data with retry logic.

    Args:
        url: Download URL
        year: Year
        month: Month number
        taxi_type: 'yellow' or 'fhv'

    Returns:
        List of records

    Raises:
        TransientError: Retryable failures (network, rate limit, server errors)
        PermanentError: Non-retryable failures (auth, not found, data issues)
    """
    try:
        logger.debug(f"Fetching {taxi_type} taxi data: {url}")
        response = requests.get(url, timeout=120)

        # Check HTTP status codes
        if response.status_code == 404:
            logger.warning(f"Data not available for {year}-{month:02d} (404)")
            raise PermanentError(f"Data not found: {url}")
        elif response.status_code == 429:
            logger.warning(f"Rate limited for {year}-{month:02d}, will retry")
            raise TransientError(f"Rate limit exceeded: {url}")
        elif response.status_code >= 500:
            logger.warning(f"Server error {response.status_code}, will retry")
            raise TransientError(f"Server error {response.status_code}: {url}")
        elif response.status_code != 200:
            logger.error(f"Unexpected status {response.status_code}")
            raise PermanentError(f"HTTP {response.status_code}: {url}")

        # Parse parquet
        table = pq.read_table(BytesIO(response.content))
        records = table.to_pylist()

        if not records:
            logger.warning(f"No records in {taxi_type} data for {year}-{month:02d}")
            return []

        logger.info(f"✓ Loaded {len(records):,} {taxi_type} taxi records for {year}-{month:02d}")
        return records

    except requests.exceptions.Timeout as e:
        logger.warning(f"Timeout downloading {taxi_type} for {year}-{month:02d}")
        raise TransientError(f"Timeout: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error for {taxi_type} {year}-{month:02d}")
        raise TransientError(f"Connection error: {e}")
    except (TransientError, PermanentError):
        # Re-raise our custom errors
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing {taxi_type} for {year}-{month:02d}")
        raise PermanentError(f"Processing error: {e}")


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
        logger.info(f"Starting Yellow Taxi ingestion for {year}, months: {months}")

        failed_months = {}
        for month in months:
            url = f"{base_url}/yellow_tripdata_{year}-{month:02d}.parquet"

            try:
                records = _download_month_data(url, year, month, "yellow")
                if records:
                    yield records
            except PermanentError as e:
                logger.error(f"Permanently failed {year}-{month:02d}: {e}")
                failed_months[f"{year}-{month:02d}"] = str(e)
                continue  # Skip to next month
            except TransientError as e:
                # Should not reach here - retry decorator exhausted
                logger.error(f"Retry exhausted for {year}-{month:02d}: {e}")
                failed_months[f"{year}-{month:02d}"] = str(e)
                continue

        if failed_months:
            logger.warning(f"Yellow Taxi failed months: {failed_months}")

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
        logger.info(f"Starting FHV ingestion for {year}, months: {months}")

        failed_months = {}
        for month in months:
            url = f"{base_url}/fhv_tripdata_{year}-{month:02d}.parquet"

            try:
                records = _download_month_data(url, year, month, "fhv")
                if records:
                    yield records
            except PermanentError as e:
                logger.error(f"Permanently failed {year}-{month:02d}: {e}")
                failed_months[f"{year}-{month:02d}"] = str(e)
                continue  # Skip to next month
            except TransientError as e:
                # Should not reach here - retry decorator exhausted
                logger.error(f"Retry exhausted for {year}-{month:02d}: {e}")
                failed_months[f"{year}-{month:02d}"] = str(e)
                continue

        if failed_months:
            logger.warning(f"FHV failed months: {failed_months}")

    # Return the resources to ingest
    resources = []
    if "yellow" in taxi_types:
        resources.append(yellow_taxi)
    if "fhv" in taxi_types:
        resources.append(fhv_taxi)

    return resources
