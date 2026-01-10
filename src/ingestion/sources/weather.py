"""DLT source for Open-Meteo historical weather data (free, no API key required)."""

import dlt
import requests
from datetime import datetime, timedelta
from typing import Iterator, Dict, Any

from src.ingestion.errors import TransientError, PermanentError
from src.utils.logger import get_logger
from src.utils.retry import retry_on_transient_error

logger = get_logger(__name__)


@retry_on_transient_error(max_attempts=3, min_wait=2, max_wait=60)
def _fetch_weather_data(
    api_url: str,
    params: Dict[str, Any],
    year: int,
    month: int
) -> Dict[str, Any]:
    """Fetch weather data for a single month with retry logic.

    Args:
        api_url: Open-Meteo API URL
        params: Request parameters (lat, lon, date range, etc.)
        year: Year
        month: Month number

    Returns:
        API response JSON data

    Raises:
        TransientError: Retryable failures (network, rate limit, server errors)
        PermanentError: Non-retryable failures (bad request, data issues)
    """
    try:
        logger.debug(f"Fetching weather data from Open-Meteo API: {year}-{month:02d}")
        response = requests.get(api_url, params=params, timeout=30)

        # Check HTTP status codes
        if response.status_code == 400:
            logger.error(f"Bad request for {year}-{month:02d} (400)")
            raise PermanentError(f"Bad request - check parameters: {response.text}")
        elif response.status_code == 429:
            logger.warning(f"Rate limited for {year}-{month:02d}, will retry")
            raise TransientError(f"Rate limit exceeded (10,000 requests/day limit)")
        elif response.status_code >= 500:
            logger.warning(f"Server error {response.status_code}, will retry")
            raise TransientError(f"Server error {response.status_code}")
        elif response.status_code != 200:
            logger.error(f"Unexpected status {response.status_code}")
            raise PermanentError(f"HTTP {response.status_code}: {response.text}")

        # Parse JSON response
        data = response.json()

        # Validate response structure
        if "hourly" not in data:
            raise PermanentError(f"Missing 'hourly' key in response")

        hourly_data = data["hourly"]
        if "time" not in hourly_data or not hourly_data["time"]:
            raise PermanentError(f"No hourly data returned in response")

        logger.info(f"✓ Fetched {len(hourly_data['time'])} hourly records for {year}-{month:02d}")
        return data

    except requests.exceptions.Timeout as e:
        logger.warning(f"Timeout fetching weather for {year}-{month:02d}")
        raise TransientError(f"Timeout: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error for {year}-{month:02d}")
        raise TransientError(f"Connection error: {e}")
    except (TransientError, PermanentError):
        # Re-raise our custom errors
        raise
    except ValueError as e:
        # JSON parsing error
        logger.error(f"Invalid JSON response for {year}-{month:02d}")
        raise PermanentError(f"JSON parsing error: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error fetching weather for {year}-{month:02d}")
        raise PermanentError(f"Processing error: {e}")


@dlt.source(name="weather")
def weather_source(year: int, months: list[int], api_key: str = None):
    """DLT source for Open-Meteo historical weather data.

    Args:
        year: Year to download data for
        months: List of month numbers (1-12)
        api_key: Not used (Open-Meteo is free), kept for compatibility

    Yields:
        Hourly weather data for NYC
    """

    @dlt.resource(
        name="hourly_weather",
        write_disposition="merge",
        primary_key="timestamp",
    )
    def hourly_weather() -> Iterator:
        """Fetch hourly historical weather data from Open-Meteo API.

        NYC coordinates: 40.7128°N, 74.0060°W (Lower Manhattan)
        Open-Meteo API is completely free and requires no API key.

        Spatial Accuracy Note:
        - Uses single weather station for entire NYC area
        - Accurate within 1-3°F for core Manhattan/Brooklyn (3-8 miles)
        - Temp variance increases up to 5-10°F for outer boroughs (15-20 miles)
        - Suitable for city-wide trends; limited for neighborhood-level analysis
        - See docs/data_model.md for detailed spatial accuracy assessment
        """
        lat, lon = 40.7128, -74.0060  # NYC coordinates
        api_url = "https://archive-api.open-meteo.com/v1/archive"

        logger.info(f"Starting weather ingestion for {year}, months: {months}")

        total_records = 0
        failed_months = {}

        for month in months:
            # Calculate date range for this month
            start_date = datetime(year, month, 1)

            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)

            # Format dates as strings
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            logger.info(f"Fetching weather data for {year}-{month:02d} ({start_str} to {end_str})")

            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_str,
                "end_date": end_str,
                "hourly": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "dew_point_2m",
                    "apparent_temperature",
                    "precipitation",
                    "rain",
                    "snowfall",
                    "cloud_cover",
                    "pressure_msl",
                    "wind_speed_10m",
                    "wind_direction_10m",
                ],
                "timezone": "America/New_York",
                "temperature_unit": "celsius",
                "wind_speed_unit": "ms",
                "precipitation_unit": "mm",
            }

            try:
                # Fetch data with retry logic
                data = _fetch_weather_data(api_url, params, year, month)

                # Extract hourly data
                hourly_data = data["hourly"]
                times = hourly_data["time"]

                # Build records from hourly data
                batch = []
                for i in range(len(times)):
                    record = {
                        "timestamp": times[i],
                        "temp": hourly_data.get("temperature_2m", [])[i],
                        "feels_like": hourly_data.get("apparent_temperature", [])[i],
                        "humidity": hourly_data.get("relative_humidity_2m", [])[i],
                        "dew_point": hourly_data.get("dew_point_2m", [])[i],
                        "precipitation": hourly_data.get("precipitation", [])[i],
                        "rain": hourly_data.get("rain", [])[i],
                        "snowfall": hourly_data.get("snowfall", [])[i],
                        "cloud_cover": hourly_data.get("cloud_cover", [])[i],
                        "pressure": hourly_data.get("pressure_msl", [])[i],
                        "wind_speed": hourly_data.get("wind_speed_10m", [])[i],
                        "wind_direction": hourly_data.get("wind_direction_10m", [])[i],
                    }
                    batch.append(record)

                total_records += len(batch)

                # Yield the batch for this month
                yield batch

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
                # Catch any unexpected errors during record building
                logger.exception(f"Failed to process weather data for {year}-{month:02d}: {e}")
                failed_months[f"{year}-{month:02d}"] = str(e)
                continue

        if failed_months:
            logger.warning(f"Weather failed months: {failed_months}")

        logger.info(
            f"Weather data collection complete: {total_records:,} hourly records"
        )

    return hourly_weather
