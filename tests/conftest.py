"""Pytest configuration and shared fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import duckdb
import pytest


@pytest.fixture
def tmp_duckdb() -> Generator[str, None, None]:
    """Create a temporary DuckDB database for testing.

    Yields:
        Path to temporary DuckDB file
    """
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as tmp:
        db_path = tmp.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def mock_env(monkeypatch) -> None:
    """Set up mock environment variables for testing.

    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    test_env = {
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "DEBUG",
        "DUCKDB_PATH": ":memory:",
        "NYC_TLC_BASE_URL": "https://test.example.com/tlc",
        "CITIBIKE_BASE_URL": "https://test.example.com/citibike",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def sample_data_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for sample test data.

    Args:
        tmp_path: Pytest tmp_path fixture

    Returns:
        Path to temporary data directory
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "raw").mkdir()
    (data_dir / "bronze").mkdir()
    (data_dir / "silver").mkdir()
    (data_dir / "gold").mkdir()

    return data_dir


@pytest.fixture
def duckdb_connection(tmp_duckdb: str) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Create a DuckDB connection for testing.

    Args:
        tmp_duckdb: Temporary DuckDB file path

    Yields:
        DuckDB connection
    """
    conn = duckdb.connect(tmp_duckdb)
    yield conn
    conn.close()
