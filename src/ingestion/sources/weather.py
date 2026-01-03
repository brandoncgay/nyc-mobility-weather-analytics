"""DLT source for Open-Meteo historical weather data (free, no API key required)."""

import dlt
import requests
from datetime import datetime, timedelta
from typing import Iterator

from src.utils.logger import get_logger

logger = get_logger(__name__)


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
        write_disposition="replace",
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

        total_records = 0

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
                # Make API call
                response = requests.get(api_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Extract hourly data
                hourly_data = data.get("hourly", {})
                times = hourly_data.get("time", [])

                if not times:
                    logger.warning(f"No hourly data returned for {year}-{month:02d}")
                    continue

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

                logger.info(
                    f"Fetched {len(batch)} hourly records for {year}-{month:02d}"
                )

                # Yield the batch for this month
                yield batch

            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error for {year}-{month:02d}: {e}")
                continue

            except Exception as e:
                logger.error(f"Failed to fetch weather for {year}-{month:02d}: {e}")
                continue

        logger.info(
            f"Weather data collection complete: {total_records:,} hourly records"
        )

    return hourly_weather
