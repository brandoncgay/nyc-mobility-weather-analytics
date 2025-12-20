"""DLT source for CitiBike trip data."""

import dlt
import pandas as pd
import requests
from io import BytesIO
from typing import Iterator
from zipfile import ZipFile

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dlt.source(name="citibike")
def citibike_source(year: int, months: list[int]):
    """DLT source for CitiBike trip data.

    Args:
        year: Year to download data for
        months: List of month numbers (1-12)

    Yields:
        CitiBike trip data
    """

    @dlt.resource(name="trips", write_disposition="replace")
    def trips() -> Iterator:
        """Download and yield CitiBike trip data.

        CitiBike data comes as monthly CSV files in ZIP format.
        Schema may vary slightly across months, DLT handles this automatically.
        """
        base_url = "https://s3.amazonaws.com/tripdata"

        for month in months:
            url = f"{base_url}/{year}{month:02d}-citibike-tripdata.zip"
            logger.info(f"Downloading CitiBike data: {year}-{month:02d}")

            try:
                # Download ZIP file
                response = requests.get(url, timeout=120)
                response.raise_for_status()

                # Extract CSV from ZIP
                with ZipFile(BytesIO(response.content)) as zip_file:
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

            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to download CitiBike data for {year}-{month:02d}: {e}")
                # Continue with other months
                continue
            except Exception as e:
                logger.error(
                    f"Failed to process CitiBike data for {year}-{month:02d}: {e}"
                )
                # Continue with other months
                continue

    return trips
