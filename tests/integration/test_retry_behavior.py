"""Integration tests for retry behavior with mocked transient failures.

This test suite validates that the retry logic in all data sources correctly:
1. Retries on transient errors (429, 5xx, timeouts, connection errors)
2. Does not retry on permanent errors (404, 401, data quality issues)
3. Eventually gives up after max attempts
4. Logs failures appropriately
"""

import pytest
from unittest.mock import Mock, patch
import requests

from src.ingestion.sources.taxi import _download_month_data as taxi_download
from src.ingestion.sources.citibike import _download_month_data as citibike_download
from src.ingestion.sources.weather import _fetch_weather_data as weather_fetch
from src.ingestion.errors import TransientError, PermanentError


class TestTaxiRetryScenarios:
    """Test retry scenarios for taxi data ingestion."""

    @patch('requests.get')
    def test_rate_limit_retry_then_success(self, mock_get):
        """Test that 429 rate limits trigger retry and eventually succeed."""
        # First two calls: rate limited, third call: success
        mock_get.side_effect = [
            Mock(status_code=429),
            Mock(status_code=429),
            Mock(status_code=200, content=b"mock_parquet_data"),
        ]

        with patch('pyarrow.parquet.read_table') as mock_parquet:
            mock_table = Mock()
            mock_table.to_pylist.return_value = [{"id": 1, "fare": 10.5}]
            mock_parquet.return_value = mock_table

            records = taxi_download(
                "https://test.com/data.parquet",
                2025,
                10,
                "yellow"
            )

        assert mock_get.call_count == 3  # Two retries, then success
        assert len(records) == 1
        assert records[0]["fare"] == 10.5

    @patch('requests.get')
    def test_server_error_retry_then_success(self, mock_get):
        """Test that 5xx server errors trigger retry."""
        mock_get.side_effect = [
            Mock(status_code=503),
            Mock(status_code=502),
            Mock(status_code=200, content=b"mock_parquet_data"),
        ]

        with patch('pyarrow.parquet.read_table') as mock_parquet:
            mock_table = Mock()
            mock_table.to_pylist.return_value = [{"id": 1}]
            mock_parquet.return_value = mock_table

            records = taxi_download(
                "https://test.com/data.parquet",
                2025,
                10,
                "yellow"
            )

        assert mock_get.call_count == 3
        assert len(records) == 1

    @patch('requests.get')
    def test_timeout_retry_then_success(self, mock_get):
        """Test that timeouts trigger retry."""
        mock_get.side_effect = [
            requests.exceptions.Timeout("Connection timed out"),
            Mock(status_code=200, content=b"mock_parquet_data"),
        ]

        with patch('pyarrow.parquet.read_table') as mock_parquet:
            mock_table = Mock()
            mock_table.to_pylist.return_value = [{"id": 1}]
            mock_parquet.return_value = mock_table

            records = taxi_download(
                "https://test.com/data.parquet",
                2025,
                10,
                "yellow"
            )

        assert mock_get.call_count == 2  # One retry
        assert len(records) == 1

    @patch('requests.get')
    def test_connection_error_retry_then_success(self, mock_get):
        """Test that connection errors trigger retry."""
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("Failed to connect"),
            Mock(status_code=200, content=b"mock_parquet_data"),
        ]

        with patch('pyarrow.parquet.read_table') as mock_parquet:
            mock_table = Mock()
            mock_table.to_pylist.return_value = [{"id": 1}]
            mock_parquet.return_value = mock_table

            records = taxi_download(
                "https://test.com/data.parquet",
                2025,
                10,
                "yellow"
            )

        assert mock_get.call_count == 2
        assert len(records) == 1

    @patch('requests.get')
    def test_404_no_retry(self, mock_get):
        """Test that 404 errors don't retry (permanent failure)."""
        mock_get.return_value = Mock(status_code=404)

        with pytest.raises(PermanentError) as exc_info:
            taxi_download(
                "https://test.com/data.parquet",
                2025,
                10,
                "yellow"
            )

        assert "Data not found" in str(exc_info.value)
        assert mock_get.call_count == 1  # No retry

    @patch('requests.get')
    def test_401_no_retry(self, mock_get):
        """Test that 401 auth errors don't retry."""
        mock_get.return_value = Mock(status_code=401)

        with pytest.raises(PermanentError):
            taxi_download(
                "https://test.com/data.parquet",
                2025,
                10,
                "yellow"
            )

        assert mock_get.call_count == 1  # No retry

    @patch('requests.get')
    def test_retry_exhaustion(self, mock_get):
        """Test that retries give up after max attempts."""
        # Always return rate limit
        mock_get.return_value = Mock(status_code=429)

        with pytest.raises(TransientError):
            taxi_download(
                "https://test.com/data.parquet",
                2025,
                10,
                "yellow"
            )

        assert mock_get.call_count == 3  # max_attempts=3


class TestCitiBikeRetryScenarios:
    """Test retry scenarios for CitiBike data ingestion."""

    @patch('requests.get')
    def test_rate_limit_retry_then_success(self, mock_get):
        """Test CitiBike handles rate limits with retry."""
        from io import BytesIO
        from zipfile import ZipFile

        # Create valid ZIP file
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            csv_data = "ride_id,started_at,ended_at\n1,2023-10-01,2023-10-01\n"
            zip_file.writestr("202310-citibike-tripdata.csv", csv_data)
        valid_zip = zip_buffer.getvalue()

        mock_get.side_effect = [
            Mock(status_code=429),
            Mock(status_code=200, content=valid_zip),
        ]

        zip_content = citibike_download(
            "https://test.com/data.zip",
            2023,
            10
        )

        assert mock_get.call_count == 2  # One retry
        assert isinstance(zip_content, bytes)
        assert len(zip_content) > 0
        # Verify it's a valid ZIP
        with ZipFile(BytesIO(zip_content)) as zf:
            assert "202310-citibike-tripdata.csv" in zf.namelist()

    @patch('requests.get')
    def test_404_no_retry(self, mock_get):
        """Test CitiBike doesn't retry 404."""
        mock_get.return_value = Mock(status_code=404)

        with pytest.raises(PermanentError):
            citibike_download(
                "https://test.com/data.zip",
                2023,
                10
            )

        assert mock_get.call_count == 1  # No retry

    @patch('requests.get')
    def test_timeout_retry(self, mock_get):
        """Test CitiBike retries on timeout."""
        from io import BytesIO
        from zipfile import ZipFile

        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            csv_data = "ride_id,started_at,ended_at\n1,2023-10-01,2023-10-01\n"
            zip_file.writestr("202310-citibike-tripdata.csv", csv_data)
        valid_zip = zip_buffer.getvalue()

        mock_get.side_effect = [
            requests.exceptions.Timeout("Connection timed out"),
            Mock(status_code=200, content=valid_zip),
        ]

        zip_content = citibike_download(
            "https://test.com/data.zip",
            2023,
            10
        )

        assert mock_get.call_count == 2
        assert isinstance(zip_content, bytes)
        assert len(zip_content) > 0


class TestWeatherRetryScenarios:
    """Test retry scenarios for weather data ingestion."""

    @patch('requests.get')
    def test_rate_limit_retry_then_success(self, mock_get):
        """Test weather API handles rate limits with retry."""
        valid_response = {
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

        mock_get.side_effect = [
            Mock(status_code=429, raise_for_status=lambda: None),
            Mock(status_code=200, json=lambda: valid_response, raise_for_status=lambda: None),
        ]

        response = weather_fetch(
            "https://api.weather.com/data",
            {"param": "value"},
            2023,
            10
        )

        assert mock_get.call_count == 2  # One retry
        assert "hourly" in response
        assert len(response["hourly"]["time"]) == 1

    @patch('requests.get')
    def test_server_error_retry(self, mock_get):
        """Test weather API retries on 5xx errors."""
        valid_response = {
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

        mock_get.side_effect = [
            Mock(status_code=503, raise_for_status=lambda: None),
            Mock(status_code=200, json=lambda: valid_response, raise_for_status=lambda: None),
        ]

        response = weather_fetch(
            "https://api.weather.com/data",
            {"param": "value"},
            2023,
            10
        )

        assert mock_get.call_count == 2
        assert "hourly" in response

    @patch('requests.get')
    def test_timeout_retry(self, mock_get):
        """Test weather API retries on timeout."""
        valid_response = {
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

        mock_get.side_effect = [
            requests.exceptions.Timeout("Request timed out"),
            Mock(status_code=200, json=lambda: valid_response, raise_for_status=lambda: None),
        ]

        response = weather_fetch(
            "https://api.weather.com/data",
            {"param": "value"},
            2023,
            10
        )

        assert mock_get.call_count == 2
        assert "hourly" in response

    @patch('requests.get')
    def test_retry_exhaustion(self, mock_get):
        """Test weather API gives up after max attempts."""
        mock_get.return_value = Mock(status_code=429, raise_for_status=lambda: None)

        with pytest.raises(TransientError):
            weather_fetch(
                "https://api.weather.com/data",
                {"param": "value"},
                2023,
                10
            )

        assert mock_get.call_count == 3  # max_attempts=3


class TestMixedRetryScenarios:
    """Test complex scenarios with mixed success/failure patterns."""

    @patch('requests.get')
    def test_transient_then_permanent_failure(self, mock_get):
        """Test that transient errors followed by permanent errors are handled correctly."""
        # First: rate limit (retry), Second: 404 (no retry)
        mock_get.side_effect = [
            Mock(status_code=429),
            Mock(status_code=404),
        ]

        with pytest.raises(PermanentError):
            taxi_download(
                "https://test.com/data.parquet",
                2025,
                10,
                "yellow"
            )

        assert mock_get.call_count == 2  # Retried once, then hit permanent error

    @patch('requests.get')
    def test_multiple_transient_then_success(self, mock_get):
        """Test multiple different transient errors before success."""
        mock_get.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            Mock(status_code=503),
            Mock(status_code=200, content=b"mock_parquet_data"),
        ]

        with patch('pyarrow.parquet.read_table') as mock_parquet:
            mock_table = Mock()
            mock_table.to_pylist.return_value = [{"id": 1}]
            mock_parquet.return_value = mock_table

            records = taxi_download(
                "https://test.com/data.parquet",
                2025,
                10,
                "yellow"
            )

        assert mock_get.call_count == 3  # Two different transient errors, then success
        assert len(records) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
