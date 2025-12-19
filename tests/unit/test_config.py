"""Tests for configuration module."""

import os

import pytest

from src.utils.config import Config


def test_config_loads_from_env(mock_env):
    """Test that configuration loads from environment variables."""
    config = Config()

    assert config.environment == "testing"
    assert config.log_level == "DEBUG"
    assert config.duckdb_path == ":memory:"


def test_config_get_with_default():
    """Test getting config value with default."""
    config = Config()

    # Non-existent key should return default
    value = config.get("NON_EXISTENT_KEY", default="default_value")
    assert value == "default_value"


def test_config_get_required_missing():
    """Test that missing required config raises error."""
    config = Config()

    with pytest.raises(ValueError, match="Required configuration"):
        config.get("NON_EXISTENT_REQUIRED_KEY", required=True)


def test_config_properties(mock_env):
    """Test configuration properties."""
    config = Config()

    assert config.nyc_tlc_base_url == "https://test.example.com/tlc"
    assert config.citibike_base_url == "https://test.example.com/citibike"
    assert config.openweather_api_key == "test_api_key"
    assert config.openweather_base_url == "https://test.example.com/weather"


def test_config_with_missing_env_file():
    """Test config works when .env file is missing."""
    # Set a test environment variable
    os.environ["TEST_VAR"] = "test_value"

    config = Config(env_file="non_existent.env")
    value = config.get("TEST_VAR")

    assert value == "test_value"

    # Cleanup
    del os.environ["TEST_VAR"]
