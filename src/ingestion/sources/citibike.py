"""DLT source for CitiBike trip data."""

import dlt
import pandas as pd
import requests
from io import BytesIO
from typing import Iterator
from zipfile import ZipFile, BadZipFile

from src.ingestion.errors import TransientError, PermanentError
from src.utils.logger import get_logger
from src.utils.retry import retry_on_transient_error

logger = get_logger(__name__)


@retry_on_transient_error(max_attempts=3, min_wait=2, max_wait=60)
def _download_month_data(url: str, year: int, month: int) -> bytes:
    """Download single month of CitiBike data with retry logic.

    Args:
        url: Download URL
        year: Year
        month: Month number

    Returns:
        ZIP file content as bytes

    Raises:
        TransientError: Retryable failures (network, rate limit, server errors)
        PermanentError: Non-retryable failures (auth, not found, data issues)
    """
    try:
        logger.debug(f"Fetching CitiBike data: {url}")
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

        # Validate it's a valid ZIP file
        try:
            with ZipFile(BytesIO(response.content)) as zip_file:
                # Check ZIP has files
                if not zip_file.namelist():
                    raise PermanentError(f"ZIP file is empty: {url}")
        except BadZipFile as e:
            raise PermanentError(f"Invalid ZIP file: {e}")

        logger.info(f"✓ Downloaded CitiBike ZIP for {year}-{month:02d}")
        return response.content

    except requests.exceptions.Timeout as e:
        logger.warning(f"Timeout downloading CitiBike for {year}-{month:02d}")
        raise TransientError(f"Timeout: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error for CitiBike {year}-{month:02d}")
        raise TransientError(f"Connection error: {e}")
    except (TransientError, PermanentError):
        # Re-raise our custom errors
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing CitiBike for {year}-{month:02d}")
        raise PermanentError(f"Processing error: {e}")


@dlt.source(name="citibike")
def citibike_source(year: int, months: list[int]):
    """DLT source for CitiBike trip data.

    Args:
        year: Year to download data for
        months: List of month numbers (1-12)

    Yields:
        CitiBike trip data
    """

    @dlt.resource(
        name="trips",
        write_disposition="merge",
        primary_key="ride_id"
    )
    def trips() -> Iterator:
        """Download and yield CitiBike trip data.

        CitiBike data comes as monthly CSV files in ZIP format.
        Schema may vary slightly across months, DLT handles this automatically.
        """
        base_url = "https://s3.amazonaws.com/tripdata"
        logger.info(f"Starting CitiBike ingestion for {year}, months: {months}")

        failed_months = {}
        for month in months:
            url = f"{base_url}/{year}{month:02d}-citibike-tripdata.zip"

            try:
                # Download ZIP file with retry logic
                zip_content = _download_month_data(url, year, month)

                # Extract and process CSV from ZIP
                with ZipFile(BytesIO(zip_content)) as zip_file:
                    # Get the first (and usually only) file in the ZIP
                    csv_filename = zip_file.namelist()[0]
                    logger.info(f"Extracting {csv_filename} from ZIP")

                    with zip_file.open(csv_filename) as csv_file:
                        # Read CSV in chunks for memory efficiency
                        chunk_size = 50000
                        chunk_num = 0

                        for chunk in pd.read_csv(csv_file, chunksize=chunk_size):
                            chunk_num += 1

                            # Convert DataFrame to list of dictionaries
                            records = chunk.to_dict(orient="records")

                            logger.info(
                                f"Loaded chunk {chunk_num} with {len(records):,} CitiBike records "
                                f"for {year}-{month:02d}"
                            )

                            # Yield chunk
                            yield records

                logger.info(f"Completed loading CitiBike data for {year}-{month:02d}")

            except PermanentError as e:
                logger.error(f"Permanently failed {year}-{month:02d}: {e}")
                failed_months[f"{year}-{month:02d}"] = str(e)
                continue  # Skip to next month
            except TransientError as e:
                # Should not reach here - retry decorator exhausted
                logger.error(f"Retry exhausted for {year}-{month:02d}: {e}")
                failed_months[f"{year}-{month:02d}"] = str(e)
                continue
            except Exception as e:
                # Catch any unexpected errors during CSV processing
                logger.exception(f"Failed to process CSV for {year}-{month:02d}: {e}")
                failed_months[f"{year}-{month:02d}"] = str(e)
                continue

        if failed_months:
            logger.warning(f"CitiBike failed months: {failed_months}")

    return trips
