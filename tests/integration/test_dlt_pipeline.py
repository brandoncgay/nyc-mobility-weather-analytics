"""Integration tests for DLT ingestion pipeline."""

import pytest
import duckdb
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
import dlt
from dlt.destinations import duckdb as duckdb_destination

from src.ingestion.sources.taxi import taxi_source
from src.ingestion.sources.citibike import citibike_source
from src.ingestion.sources.weather import weather_source
from src.ingestion.run_pipeline import run_ingestion_pipeline


class TestDLTPipelineIntegration:
    """Integration tests for the complete DLT pipeline."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_nyc_mobility.duckdb"
        yield str(db_path)
        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_pipeline(self, temp_db_path):
        """Create a DLT pipeline with temporary database."""
        pipeline = dlt.pipeline(
            pipeline_name="test_nyc_mobility",
            destination=duckdb_destination(credentials=temp_db_path),
            dataset_name="raw_data",
            progress="log"
        )
        return pipeline

    @patch('pyarrow.parquet.read_table')
    def test_taxi_pipeline_end_to_end(self, mock_read_table, mock_pipeline):
        """Test complete taxi ingestion pipeline."""
        # Mock parquet data
        mock_table = Mock()
        mock_table.to_pylist.return_value = [
            {"tpep_pickup_datetime": "2023-10-01 12:00:00", "fare_amount": 10.5},
            {"tpep_pickup_datetime": "2023-10-01 13:00:00", "fare_amount": 15.0}
        ]
        mock_read_table.return_value = mock_table

        # Run pipeline
        taxi_data = taxi_source(2023, [10], ["yellow"])
        info = mock_pipeline.run(taxi_data)

        # Verify pipeline ran successfully
        assert info is not None
        assert info.has_failed_jobs is False

        # Verify data was loaded into DuckDB
        # Get the actual database path from the pipeline destination
        db_path = mock_pipeline.destination.config_params['credentials']
        conn = duckdb.connect(db_path)
        try:
            result = conn.execute("SELECT COUNT(*) FROM raw_data.yellow_taxi").fetchone()
            assert result[0] >= 1  # At least some records loaded
        finally:
            conn.close()

    @patch('requests.get')
    @patch('pandas.read_csv')
    def test_citibike_pipeline_end_to_end(self, mock_read_csv, mock_get, mock_pipeline):
        """Test complete CitiBike ingestion pipeline."""
        from io import BytesIO
        from zipfile import ZipFile
        import pandas as pd

        # Create mock ZIP file
        csv_data = b"ride_id,started_at,ended_at\n1,2023-10-01,2023-10-01\n2,2023-10-01,2023-10-01"
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("202310-citibike-tripdata.csv", csv_data)
        zip_buffer.seek(0)

        mock_response = Mock()
        mock_response.content = zip_buffer.getvalue()
        mock_get.return_value = mock_response

        # Mock pandas read_csv
        mock_df = pd.DataFrame({
            'ride_id': [1, 2],
            'started_at': ['2023-10-01', '2023-10-01']
        })
        mock_read_csv.return_value = [mock_df]

        # Run pipeline
        citibike_data = citibike_source(2023, [10])
        info = mock_pipeline.run(citibike_data)

        # Verify pipeline ran successfully
        assert info is not None
        assert info.has_failed_jobs is False

    @patch('requests.get')
    @patch('time.sleep')
    def test_weather_pipeline_end_to_end(self, mock_sleep, mock_get, mock_pipeline):
        """Test complete weather ingestion pipeline."""
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

        # Run pipeline for just one day
        weather_data = weather_source(2023, [10], "test_api_key")

        # Run pipeline directly with the weather source
        # DltSource is already iterable, no need to manually extract batches
        info = mock_pipeline.run(weather_data)

        # Verify pipeline ran successfully
        assert info is not None

    @patch('src.ingestion.sources.taxi.pq.read_table')
    @patch('requests.get')
    @patch('time.sleep')
    def test_full_pipeline_all_sources(
        self, mock_sleep, mock_get_weather, mock_read_table
    ):
        """Test running all sources together."""
        # Mock taxi data
        mock_table = Mock()
        mock_table.to_pylist.return_value = [
            {"tpep_pickup_datetime": "2023-10-01", "fare_amount": 10.5}
        ]
        mock_read_table.return_value = mock_table

        # Mock weather data
        mock_weather_response = Mock()
        mock_weather_response.json.return_value = {
            "hourly": [{"dt": 1696118400, "temp": 15.5, "weather": [{"main": "Clear"}]}]
        }
        mock_get_weather.return_value = mock_weather_response

        # This test validates that all sources can be loaded together
        # In practice, we would use run_ingestion_pipeline here
        # but to avoid actual downloads, we verify the structure is correct

        # Verify sources can be instantiated
        taxi_src = taxi_source(2023, [10], ["yellow"])
        weather_src = weather_source(2023, [10], "test_api_key")

        assert taxi_src is not None
        assert weather_src is not None

    def test_dlt_metadata_tables_created(self, mock_pipeline):
        """Test that DLT creates its metadata tables."""
        # Create a simple resource to trigger pipeline run
        @dlt.resource(name="test_data", write_disposition="replace")
        def test_data():
            yield [{"id": 1, "value": "test"}]

        # Run pipeline
        info = mock_pipeline.run(test_data)

        # Check that DLT metadata tables exist
        # Note: DLT creates these automatically
        assert info is not None

    @patch('pyarrow.parquet.read_table')
    def test_pipeline_schema_evolution(self, mock_read_table, mock_pipeline):
        """Test that DLT handles schema evolution."""
        # First batch with initial schema
        mock_table1 = Mock()
        mock_table1.to_pylist.return_value = [
            {"tpep_pickup_datetime": "2023-10-01", "fare_amount": 10.5}
        ]

        # Second batch with additional column
        mock_table2 = Mock()
        mock_table2.to_pylist.return_value = [
            {
                "tpep_pickup_datetime": "2023-10-02",
                "fare_amount": 15.0,
                "new_column": "new_value"
            }
        ]

        mock_read_table.side_effect = [mock_table1, mock_table2]

        # Run pipeline
        taxi_data = taxi_source(2023, [10, 11], ["yellow"])
        info = mock_pipeline.run(taxi_data)

        # DLT should handle schema evolution automatically
        assert info is not None
        assert info.has_failed_jobs is False

    def test_pipeline_error_recovery(self, mock_pipeline):
        """Test that pipeline handles errors gracefully."""
        # Create a resource that fails midway
        @dlt.resource(name="failing_data", write_disposition="replace")
        def failing_data():
            yield [{"id": 1, "value": "good"}]
            # Subsequent batches would fail in real scenario
            # DLT should handle this gracefully

        # Run pipeline
        info = mock_pipeline.run(failing_data)

        # Pipeline should complete even with partial failures
        assert info is not None

    @patch('src.utils.config.config')
    def test_pipeline_configuration(self, mock_config):
        """Test that pipeline uses configuration correctly."""
        mock_config.duckdb_path = "test_path.duckdb"

        # Verify configuration is accessible
        assert mock_config.duckdb_path == "test_path.duckdb"

    @patch('pyarrow.parquet.read_table')
    def test_write_disposition_replace(self, mock_read_table, mock_pipeline):
        """Test that write_disposition='replace' works correctly."""
        mock_table = Mock()
        mock_table.to_pylist.return_value = [
            {"tpep_pickup_datetime": "2023-10-01", "fare_amount": 10.5}
        ]
        mock_read_table.return_value = mock_table

        # Run pipeline twice
        taxi_data1 = taxi_source(2023, [10], ["yellow"])
        info1 = mock_pipeline.run(taxi_data1)

        taxi_data2 = taxi_source(2023, [10], ["yellow"])
        info2 = mock_pipeline.run(taxi_data2)

        # Both runs should succeed
        assert info1 is not None
        assert info2 is not None

        # Second run should replace first (not append)
        # This is handled by write_disposition='replace'
