"""Unit tests for Weather DLT source."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.ingestion.sources.weather import weather_source, _fetch_weather_data
from src.ingestion.errors import TransientError, PermanentError


class TestWeatherSource:
    """Tests for weather_source DLT source."""

    def test_weather_source_returns_resource(self):
        """Test that weather_source returns a DLT source."""
        source = weather_source(2023, [10])

        assert source is not None
        assert hasattr(source, 'resources')
        assert "hourly_weather" in source.resources

    @patch('src.ingestion.sources.weather._fetch_weather_data')
    def test_weather_api_url_format(self, mock_fetch):
        """Test that weather API constructs correct URLs and parameters."""
        mock_fetch.return_value = {
            "hourly": {
                "time": ["2023-10-01T00:00"],
                "temperature_2m": [15.5],
                "apparent_temperature": [14.0],
                "relative_humidity_2m": [70],
                "dew_point_2m": [10.0],
                "precipitation": [0.0],
                "rain": [0.0],
                "snowfall": [0.0],
                "cloud_cover": [20],
                "pressure_msl": [1013],
                "wind_speed_10m": [3.5],
                "wind_direction_10m": [180]
            }
        }

        source = weather_source(2023, [10])
        weather_resource = source.resources["hourly_weather"]

        # Consume resource
        results = list(weather_resource())

        # Verify fetch was called
        assert mock_fetch.call_count == 1

        # Check that the call had correct structure
        call_args = mock_fetch.call_args
        url = call_args[0][0]
        params = call_args[0][1]

        # Using Open-Meteo API (free, no API key required)
        assert url == "https://archive-api.open-meteo.com/v1/archive"
        assert params['latitude'] == 40.7128
        assert params['longitude'] == -74.0060
        assert params['timezone'] == "America/New_York"
        # Open-Meteo doesn't require API key
        assert 'appid' not in params

    @patch('src.ingestion.sources.weather._fetch_weather_data')
    def test_weather_data_processing(self, mock_fetch):
        """Test that weather data is properly processed."""
        mock_fetch.return_value = {
            "hourly": {
                "time": ["2023-10-01T00:00", "2023-10-01T01:00"],
                "temperature_2m": [15.5, 16.0],
                "apparent_temperature": [14.0, 14.5],
                "relative_humidity_2m": [70, 68],
                "dew_point_2m": [10.0, 10.2],
                "precipitation": [0.0, 0.0],
                "rain": [0.0, 0.0],
                "snowfall": [0.0, 0.0],
                "cloud_cover": [20, 25],
                "pressure_msl": [1013, 1014],
                "wind_speed_10m": [3.5, 3.8],
                "wind_direction_10m": [180, 185]
            }
        }

        source = weather_source(2023, [10])
        weather_resource = source.resources["hourly_weather"]

        # Get first batch
        results = list(weather_resource())

        # Verify data structure - resource yields a list of records
        assert len(results) >= 1
        # Get the batch (which is a list of records)
        batch = results[0] if isinstance(results[0], list) else results

        # Find first record
        first_record = batch[0] if isinstance(batch, list) and len(batch) > 0 else results[0]

        assert 'timestamp' in first_record
        assert 'temp' in first_record
        assert 'feels_like' in first_record
        assert 'humidity' in first_record
        assert first_record['temp'] == 15.5

    @patch('src.ingestion.sources.weather._fetch_weather_data')
    def test_weather_handles_multiple_months(self, mock_fetch):
        """Test that weather processes multiple months."""
        mock_fetch.return_value = {
            "hourly": {
                "time": ["2023-10-01T00:00"],
                "temperature_2m": [15.5],
                "apparent_temperature": [14.0],
                "relative_humidity_2m": [70],
                "dew_point_2m": [10.0],
                "precipitation": [0.0],
                "rain": [0.0],
                "snowfall": [0.0],
                "cloud_cover": [20],
                "pressure_msl": [1013],
                "wind_speed_10m": [3.5],
                "wind_direction_10m": [180]
            }
        }

        source = weather_source(2023, [10, 11, 12])
        weather_resource = source.resources["hourly_weather"]

        # Consume all batches
        results = list(weather_resource())

        # Should call fetch once per month
        assert mock_fetch.call_count == 3
        assert len(results) == 3  # One batch per month

    @patch('src.ingestion.sources.weather._fetch_weather_data')
    def test_weather_http_error_handling(self, mock_fetch):
        """Test that weather source handles HTTP errors."""
        # Simulate permanent error (e.g., bad request)
        mock_fetch.side_effect = PermanentError("Bad request - check parameters")

        source = weather_source(2023, [10])
        weather_resource = source.resources["hourly_weather"]

        # Should not raise, but should track failed months
        results = list(weather_resource())

        # No data yielded due to error
        assert len(results) == 0

    @patch('src.ingestion.sources.weather._fetch_weather_data')
    def test_weather_rate_limit_handling(self, mock_fetch):
        """Test that weather source handles rate limit errors."""
        # First call fails with rate limit, second succeeds
        mock_fetch.side_effect = [
            TransientError("Rate limit exceeded"),
            {
                "hourly": {
                    "time": ["2023-10-01T00:00"],
                    "temperature_2m": [15.5],
                    "apparent_temperature": [14.0],
                    "relative_humidity_2m": [70],
                    "dew_point_2m": [10.0],
                    "precipitation": [0.0],
                    "rain": [0.0],
                    "snowfall": [0.0],
                    "cloud_cover": [20],
                    "pressure_msl": [1013],
                    "wind_speed_10m": [3.5],
                    "wind_direction_10m": [180]
                }
            }
        ]

        source = weather_source(2023, [10, 11])
        weather_resource = source.resources["hourly_weather"]

        # Should get data from second month after first fails
        results = list(weather_resource())

        # First month failed, second succeeded
        assert len(results) == 1

    @patch('src.ingestion.sources.weather._fetch_weather_data')
    def test_weather_missing_hourly_data(self, mock_fetch):
        """Test handling of missing hourly data in API response."""
        mock_fetch.side_effect = PermanentError("Missing 'hourly' key in response")

        source = weather_source(2023, [10])
        weather_resource = source.resources["hourly_weather"]

        # Should handle missing data gracefully
        results = list(weather_resource())

        # No data should be yielded
        assert len(results) == 0

    @patch('src.ingestion.sources.weather._fetch_weather_data')
    def test_weather_empty_time_array(self, mock_fetch):
        """Test handling of empty time array in hourly data."""
        mock_fetch.side_effect = PermanentError("No hourly data returned in response")

        source = weather_source(2023, [10])
        weather_resource = source.resources["hourly_weather"]

        # Should handle empty data gracefully
        results = list(weather_resource())

        # No data should be yielded
        assert len(results) == 0

    @patch('src.ingestion.sources.weather._fetch_weather_data')
    def test_weather_data_structure(self, mock_fetch):
        """Test that weather data has correct structure."""
        mock_fetch.return_value = {
            "hourly": {
                "time": ["2023-10-01T00:00"],
                "temperature_2m": [15.5],
                "apparent_temperature": [14.0],
                "relative_humidity_2m": [70],
                "dew_point_2m": [10.0],
                "precipitation": [0.5],
                "rain": [0.3],
                "snowfall": [0.2],
                "cloud_cover": [75],
                "pressure_msl": [1013],
                "wind_speed_10m": [8.5],
                "wind_direction_10m": [270]
            }
        }

        source = weather_source(2023, [10])
        weather_resource = source.resources["hourly_weather"]

        # Get first batch
        results = list(weather_resource())

        # Get the batch - could be nested list or flat list
        batch = results[0] if isinstance(results[0], list) else results
        record = batch[0] if isinstance(batch, list) and len(batch) > 0 else results[0]

        # Verify all expected fields are present
        assert record['timestamp'] == "2023-10-01T00:00"
        assert record['temp'] == 15.5
        assert record['feels_like'] == 14.0
        assert record['humidity'] == 70
        assert record['dew_point'] == 10.0
        assert record['precipitation'] == 0.5
        assert record['rain'] == 0.3
        assert record['snowfall'] == 0.2
        assert record['cloud_cover'] == 75
        assert record['pressure'] == 1013
        assert record['wind_speed'] == 8.5
        assert record['wind_direction'] == 270

    def test_weather_nyc_coordinates(self):
        """Test that NYC coordinates are used."""
        # NYC coordinates: 40.7128°N, 74.0060°W (Lower Manhattan)
        source = weather_source(2023, [10])
        assert source is not None
        assert "hourly_weather" in source.resources
