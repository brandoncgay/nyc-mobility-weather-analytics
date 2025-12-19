# Development Setup Guide

This guide will help you set up your local development environment for the NYC Mobility & Weather Analytics Platform.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11 or higher** - [Download Python](https://www.python.org/downloads/)
- **Poetry** - Python dependency management tool
  ```bash
  curl -sSL https://install.python-poetry.org | python3 -
  ```
- **Git** - Version control system

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/nyc-mobility-weather-analytics.git
cd nyc-mobility-weather-analytics
```

### 2. Run the Setup Script

The easiest way to set up your environment is to run the automated setup script:

```bash
chmod +x scripts/setup/init_env.sh
./scripts/setup/init_env.sh
```

This script will:
- Copy `.env.template` to `.env`
- Install Poetry dependencies
- Set up pre-commit hooks
- Create data directories
- Initialize the DuckDB database

### 3. Manual Setup (Alternative)

If you prefer to set up manually:

#### Install Dependencies

```bash
poetry install
```

#### Configure Environment Variables

```bash
cp .env.template .env
```

Edit `.env` and add your API keys:
- `OPENWEATHER_API_KEY` - Get from [OpenWeather](https://openweathermap.org/api)

#### Set up Pre-commit Hooks

```bash
poetry run pre-commit install
```

#### Create Data Directories

```bash
mkdir -p data/{raw,bronze,silver,gold}
```

## Environment Configuration

### Required Variables

- `OPENWEATHER_API_KEY` - Required for weather data ingestion (MVP 1)

### Optional Variables (for later MVPs)

- Snowflake credentials (MVP 3)
- AWS S3 credentials (MVP 3)
- OpenAI API key (MVP 4)

## Verify Installation

### Run Tests

```bash
poetry run pytest
```

You should see all tests passing.

### Check Code Quality

```bash
# Run linter
poetry run ruff check .

# Format code
poetry run ruff format .
```

### Verify Imports

```bash
poetry run python -c "from src.utils.config import config; print(config.environment)"
```

This should print `development`.

## Development Workflow

### Activate Poetry Shell

```bash
poetry shell
```

This activates a virtual environment with all dependencies.

### Running Jupyter Notebooks

```bash
poetry run jupyter notebook
```

Notebooks should be saved in the `notebooks/` directory for exploratory analysis.

### Running Tests with Coverage

```bash
poetry run pytest --cov=src --cov-report=html
```

View the coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Pre-commit Hooks

Pre-commit hooks will automatically run on every commit to ensure code quality:

- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON validation
- Ruff linting and formatting
- SQL linting (for dbt files)

To run pre-commit manually:
```bash
poetry run pre-commit run --all-files
```

## Project Structure

```
nyc-mobility-weather-analytics/
├── src/                    # Source code
│   ├── ingestion/         # Data ingestion scripts
│   ├── api/               # FastAPI service (MVP 4)
│   └── utils/             # Shared utilities
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── data/                  # Local data storage (gitignored)
│   ├── raw/              # Raw downloaded data
│   ├── bronze/           # Bronze layer
│   ├── silver/           # Silver layer
│   └── gold/             # Gold layer
├── notebooks/            # Jupyter notebooks
├── dbt/                  # dbt project (MVP 2)
├── dagster/              # Dagster pipelines (MVP 2)
└── docs/                 # Documentation
```

## Common Issues

### Poetry Installation Fails

If `poetry install` fails, try:
```bash
poetry lock --no-update
poetry install
```

### Pre-commit Hooks Fail

If pre-commit hooks fail after installation:
```bash
poetry run pre-commit clean
poetry run pre-commit install
```

### DuckDB Import Error

Ensure you're using Python 3.11+:
```bash
python --version
```

## Next Steps

After successful setup:

1. **MVP 1**: Start with data ingestion
   - See `src/ingestion/` for ingestion scripts
   - Download sample taxi and CitiBike data

2. **Explore the data**
   - Use Jupyter notebooks in `notebooks/`
   - Connect to DuckDB at `data/nyc_mobility.duckdb`

3. **Read the documentation**
   - Architecture diagram in README.md
   - MVP roadmap for implementation order

## Getting Help

- Check the [main README](../README.md) for project overview
- Review the [architecture diagram](../README.md#architecture-diagram)
- Open an issue on GitHub for bugs or questions

## Additional Resources

- [Poetry Documentation](https://python-poetry.org/docs/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [dbt Documentation](https://docs.getdbt.com/)
