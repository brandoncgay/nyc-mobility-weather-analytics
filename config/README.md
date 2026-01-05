# Configuration Directory

This directory contains configuration files for the NYC Mobility & Weather Analytics pipeline.

## Files

### ingestion.yaml

Configuration for DLT data ingestion pipeline.

**Key sections:**

1. **sources**: Configure which data sources to ingest
   - Enable/disable individual sources
   - Specify months/date ranges to ingest
   - Configure location parameters (for weather)

2. **database**: Database connection and schema settings

3. **settings**: Ingestion behavior
   - Full refresh vs incremental
   - Retry logic
   - Validation thresholds

4. **logging**: Logging configuration

5. **performance**: Performance tuning parameters

**Usage:**

The ingestion configuration is loaded automatically by the DLT pipeline:

```bash
# Run ingestion with default config
poetry run python src/ingestion/run_pipeline.py

# Run specific sources
poetry run python src/ingestion/run_pipeline.py --sources taxi citibike

# Or use the pipeline script
./scripts/run_pipeline.sh ingestion
```

**Customization:**

To ingest different time periods, edit the `months` arrays:

```yaml
sources:
  yellow_taxi:
    months:
      - "2024-12"  # Add new month
      - "2025-01"  # Add another month
```

To change weather location (e.g., Brooklyn):

```yaml
sources:
  weather:
    location:
      latitude: 40.6782
      longitude: -73.9442
      timezone: "America/New_York"
```

## Environment Variables

Some configuration can also be set via environment variables (see `.env` file):

- `DUCKDB_PATH`: Path to DuckDB database
- `NYC_TLC_BASE_URL`: Base URL for NYC TLC data
- `CITIBIKE_BASE_URL`: Base URL for CitiBike data
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)
- `ENVIRONMENT`: Environment name (development, staging, production)

Environment variables take precedence over configuration files.

## Adding New Configuration

To add new configuration files:

1. Create YAML file in this directory (e.g., `transformation.yaml`)
2. Document the structure in this README
3. Load in your code using `pyyaml`:

```python
import yaml
from pathlib import Path

config_path = Path(__file__).parent.parent / "config" / "transformation.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)
```

## Best Practices

1. **Never commit secrets** - Use environment variables or `.env` for sensitive data
2. **Version control configs** - Configuration files should be in git
3. **Document changes** - Update this README when adding new config options
4. **Provide defaults** - Always have sensible defaults in the code
5. **Validate inputs** - Check configuration values at runtime

## Example: Running Pipeline with Custom Config

```bash
# 1. Edit config/ingestion.yaml to set desired parameters
vim config/ingestion.yaml

# 2. Run ingestion
poetry run python src/ingestion/run_pipeline.py

# 3. Run transformations
cd dbt && poetry run dbt build

# Or use the combined script:
./scripts/run_pipeline.sh full
```
