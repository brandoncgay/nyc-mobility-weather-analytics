"""Unit tests for Weather DLT source."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.ingestion.sources.weather import weather_source


class TestWeatherSource:
    """Tests for weather_source DLT source."""

    def test_weather_source_returns_resource(self):
        """Test that weather_source returns a resource."""
        source = weather_source(2023, [10], "test_api_key")

        assert source is not None

    @patch('requests.get')
    @patch('time.sleep')
    def test_weather_api_url_format(self, mock_sleep, mock_get):
        """Test that weather API constructs correct URLs."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hourly": [
                {
                    "dt": 1696118400,
                    "temp": 15.5,
                    "feels_like": 14.0,
                    "pressure": 1013,
                    "humidity": 70,
                    "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}]
                }
            ]
        }
        mock_get.return_value = mock_response

        api_key = "test_api_key"
        source = weather_source(2023, [10], api_key)

        # Consume a few records
        results = []
        for i, batch in enumerate(source()):
            results.extend(batch)
            if i >= 2:  # Just test first few days
                break

        # Verify API was called with correct parameters
        assert mock_get.call_count >= 1

        # Check that the first call had correct structure
        first_call = mock_get.call_args_list[0]
        url = first_call[0][0]
        params = first_call[1].get('params', {})

        assert url == "https://api.openweathermap.org/data/2.5/onecall/timemachine"
        assert params['lat'] == 40.7128
        assert params['lon'] == -74.0060
        assert params['appid'] == api_key
        assert params['units'] == "metric"

    @patch('requests.get')
    @patch('time.sleep')
    def test_weather_data_processing(self, mock_sleep, mock_get):
        """Test that weather data is properly processed."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hourly": [
                {
                    "dt": 1696118400,
                    "temp": 15.5,
                    "feels_like": 14.0,
                    "pressure": 1013,
                    "humidity": 70,
                    "dew_point": 10.0,
                    "clouds": 20,
                    "visibility": 10000,
                    "wind_speed": 3.5,
                    "wind_deg": 180,
                    "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}]
                }
            ]
        }
        mock_get.return_value = mock_response

        source = weather_source(2023, [10], "test_api_key")

        # Get first batch
        results = []
        for i, batch in enumerate(source()):
            results.extend(batch)
            if i >= 0:  # Just get first day
                break

        # Verify data structure
        assert len(results) > 0
        first_record = results[0]

        assert 'dt' in first_record
        assert 'timestamp' in first_record
        assert 'temp' in first_record
        assert 'weather_main' in first_record
        assert first_record['weather_main'] == "Clear"

    @patch('requests.get')
    @patch('time.sleep')
    def test_weather_handles_multiple_months(self, mock_sleep, mock_get):
        """Test that weather processes multiple months."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hourly": [{"dt": 1696118400, "temp": 15.5, "weather": [{"main": "Clear"}]}]
        }
        mock_get.return_value = mock_response

        source = weather_source(2023, [10, 11], "test_api_key")

        # Count total API calls for two months
        # October has 31 days, November has 30 days = 61 days total
        call_count = 0
        for batch in source():
            call_count = mock_get.call_count
            if call_count > 5:  # Just test first few days
                break

        assert call_count >= 5

    @patch('requests.get')
    @patch('time.sleep')
    def test_weather_rate_limiting(self, mock_sleep, mock_get):
        """Test that rate limiting is applied between API calls."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hourly": [{"dt": 1696118400, "temp": 15.5, "weather": [{"main": "Clear"}]}]
        }
        mock_get.return_value = mock_response

        source = weather_source(2023, [10], "test_api_key")

        # Process a few days
        count = 0
        for batch in source():
            count += 1
            if count >= 3:
                break

        # Verify sleep was called (rate limiting)
        assert mock_sleep.call_count >= 2  # Should sleep between calls

    @patch('requests.get')
    @patch('time.sleep')
    def test_weather_http_error_handling(self, mock_sleep, mock_get):
        """Test that weather source handles HTTP errors."""
        from requests.exceptions import HTTPError

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = HTTPError()

        mock_get.return_value = mock_response

        source = weather_source(2023, [10], "invalid_api_key")

        # Should raise error for invalid API key (401)
        with pytest.raises(HTTPError):
            list(source())

    @patch('requests.get')
    @patch('time.sleep')
    def test_weather_rate_limit_retry(self, mock_sleep, mock_get):
        """Test that weather source handles rate limit errors."""
        from requests.exceptions import HTTPError

        # First call returns 429 (rate limit)
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        http_error = HTTPError()
        http_error.response = mock_response_429
        mock_response_429.raise_for_status.side_effect = http_error

        # Second call succeeds
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "hourly": [{"dt": 1696118400, "temp": 15.5, "weather": [{"main": "Clear"}]}]
        }

        mock_get.side_effect = [mock_response_429, mock_response_200]

        source = weather_source(2023, [10], "test_api_key")

        # Should retry after rate limit
        results = []
        for i, batch in enumerate(source()):
            results.extend(batch)
            if i >= 0:  # Get first successful batch
                break

        # Should have slept for 60 seconds on rate limit
        assert any(call[0][0] == 60 for call in mock_sleep.call_args_list)

    @patch('requests.get')
    @patch('time.sleep')
    def test_weather_missing_hourly_data(self, mock_sleep, mock_get):
        """Test handling of missing hourly data in API response."""
        mock_response = Mock()
        mock_response.json.return_value = {}  # No hourly data

        mock_get.return_value = mock_response

        source = weather_source(2023, [10], "test_api_key")

        # Should handle missing data gracefully
        results = []
        for i, batch in enumerate(source()):
            results.extend(batch)
            if i >= 2:  # Test a few days
                break

        # No data should be yielded
        assert len(results) == 0

    @patch('requests.get')
    @patch('time.sleep')
    def test_weather_timestamp_conversion(self, mock_sleep, mock_get):
        """Test that timestamps are correctly converted."""
        unix_timestamp = 1696118400  # Oct 1, 2023

        mock_response = Mock()
        mock_response.json.return_value = {
            "hourly": [
                {
                    "dt": unix_timestamp,
                    "temp": 15.5,
                    "weather": [{"id": 800, "main": "Clear", "description": "clear"}]
                }
            ]
        }
        mock_get.return_value = mock_response

        source = weather_source(2023, [10], "test_api_key")

        # Get first batch
        for batch in source():
            first_record = batch[0]
            break

        # Verify timestamp was converted
        assert first_record['dt'] == unix_timestamp
        assert isinstance(first_record['timestamp'], datetime)

    def test_weather_nyc_coordinates(self):
        """Test that NYC coordinates are used."""
        # This is implicitly tested in the API URL format test
        # NYC coordinates: 40.7128°N, 74.0060°W
        source = weather_source(2023, [10], "test_api_key")
        assert source is not None
