# dbt Project: NYC Mobility Analytics

This dbt project implements the Bronze → Silver → Gold architecture for NYC mobility and weather analytics.

## Architecture

### Bronze Layer (Staging)
**Purpose**: Mechanical cleaning only - normalize columns, cast types, deduplicate
**Location**: `models/staging/`
**Materialization**: Views

- `staging/tlc/` - NYC TLC taxi data
- `staging/citibike/` - CitiBike trip data
- `staging/weather/` - Open-Meteo weather data

### Intermediate Layer
**Purpose**: Shared transformations (internal plumbing)
**Location**: `models/intermediate/`
**Materialization**: Ephemeral (CTEs, not persisted)

Contains only shared transformations needed by multiple marts.

### Silver Layer (Marts)
**Purpose**: Kimball dimensional model + ALL business logic (authoritative)
**Location**: `models/marts/core/`
**Materialization**: Tables

- Dimension tables (`dim_*`)
- Fact tables (`fct_*`)
- **This is where business logic lives**

### Gold Layer (Semantic)
**Purpose**: Consumption layer - governed metrics for self-service
**Location**: `semantic_models/` and `metrics/`

- Semantic models define dimensions and measures
- Metrics define business calculations

## Running dbt

```bash
# Install dbt packages
poetry run dbt deps

# Run all models
poetry run dbt run

# Run specific layer
poetry run dbt run --select staging
poetry run dbt run --select intermediate
poetry run dbt run --select marts

# Run tests
poetry run dbt test

# Generate documentation
poetry run dbt docs generate
poetry run dbt docs serve
```

## Project Structure

```
dbt/
├── dbt_project.yml      # Project configuration
├── profiles.yml         # Connection profiles
├── packages.yml         # Dependencies (dbt_utils, etc.)
├── models/
│   ├── staging/         # Bronze: Source cleaning
│   ├── intermediate/    # Shared transformations
│   └── marts/          # Silver: Dimensional model
├── semantic_models/     # Gold: Semantic layer
├── metrics/            # Gold: Metric definitions
├── tests/              # Custom tests
├── macros/             # Reusable SQL macros
└── seeds/              # Reference data (TLC zones)
```
