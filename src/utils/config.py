"""Configuration management using environment variables."""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class Config:
    """Configuration loader with environment variable validation."""

    def __init__(self, env_file: str = ".env") -> None:
        """Initialize configuration.

        Args:
            env_file: Path to environment file (default: .env)
        """
        self.env_file = env_file
        self._load_env()

    def _load_env(self) -> None:
        """Load environment variables from .env file."""
        env_path = Path(self.env_file)
        if env_path.exists():
            load_dotenv(env_path)
        else:
            print(f"Warning: {self.env_file} not found. Using system environment variables.")

    def get(self, key: str, default: Any = None, required: bool = False) -> Any:
        """Get configuration value from environment.

        Args:
            key: Environment variable name
            default: Default value if not found
            required: Raise error if not found and no default

        Returns:
            Configuration value

        Raises:
            ValueError: If required config is missing
        """
        value = os.getenv(key, default)

        if required and value is None:
            raise ValueError(f"Required configuration '{key}' not found in environment")

        return value

    @property
    def environment(self) -> str:
        """Get current environment (development/staging/production)."""
        return self.get("ENVIRONMENT", "development")

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self.get("LOG_LEVEL", "INFO")

    @property
    def motherduck_token(self) -> str | None:
        """Get MotherDuck token."""
        return self.get("MOTHERDUCK_TOKEN")

    @property
    def duckdb_path(self) -> str:
        """Get DuckDB database path.

        Returns:
            MotherDuck connection string if token is present, else local file path.
        """
        if self.motherduck_token:
            return "md:nyc_mobility"
        return self.get("DUCKDB_PATH", "./data/nyc_mobility.duckdb")

    @property
    def nyc_tlc_base_url(self) -> str:
        """Get NYC TLC data base URL."""
        return self.get(
            "NYC_TLC_BASE_URL", "https://d37ci6vzurychx.cloudfront.net/trip-data"
        )

    @property
    def citibike_base_url(self) -> str:
        """Get CitiBike data base URL."""
        return self.get("CITIBIKE_BASE_URL", "https://s3.amazonaws.com/tripdata")

    @property
    def gcs_bucket_name(self) -> str | None:
        """Get GCS bucket name for staging."""
        return self.get("GCS_BUCKET_NAME")



# Global config instance
config = Config()
