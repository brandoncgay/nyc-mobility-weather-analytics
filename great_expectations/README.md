# Great Expectations Data Quality

This directory contains the Great Expectations data quality framework for the NYC Mobility & Weather Analytics Platform.

## Overview

Great Expectations provides:
- **Data Validation**: Automated quality checks on all dbt models
- **Expectation Suites**: Comprehensive data quality rules for staging, dimensions, and facts
- **Data Docs**: Interactive HTML documentation of all validations
- **Checkpoints**: Automated validation workflows

## Project Structure

```
great_expectations/
├── great_expectations.yml          # Main configuration
├── expectations/                   # Expectation suite definitions
├── checkpoints/                    # Validation checkpoint configurations
├── uncommitted/
│   ├── data_docs/                 # Generated HTML documentation
│   ├── validations/               # Validation results
│   └── config_variables.yml       # Environment-specific variables
├── plugins/                        # Custom expectations (future)
├── create_expectation_suites.py   # Script to generate all suites
├── run_validations.py             # Script to run all validations
└── validate_context.py            # Context validation utility
```

## Expectation Suites

### Staging Models (4 suites)
- `stg_yellow_taxi` - Yellow taxi data quality
- `stg_fhv_taxi` - FHV taxi data quality
- `stg_citibike__trips` - CitiBike trips data quality
- `stg_weather__hourly` - Hourly weather data quality

**Key Expectations**:
- Minimum row counts (1,000+ trips, 100+ weather records)
- Unique trip IDs
- Non-null required fields
- Valid value ranges (distances 0-200 miles, amounts 0-1000)
- Categorical value sets (member types, etc.)

### Dimension Tables (4 suites)
- `dim_date` - Date dimension integrity
- `dim_time` - Time dimension integrity
- `dim_weather` - Weather dimension integrity
- `dim_location` - Location dimension integrity

**Key Expectations**:
- Unique dimension keys
- Non-null key fields
- Valid categorical values
- Referential integrity
- Expected row counts (24 hours in dim_time, 200+ locations)

### Fact Tables (2 suites)
- `fct_trips` - Trip-level fact data quality
- `fct_hourly_mobility` - Hourly aggregated metrics quality

**Key Expectations**:
- Minimum 1M+ trips in fct_trips
- Unique fact keys
- Non-null foreign keys
- Valid trip metrics (duration 0-1440 min, speed reasonable)
- Weather join coverage (99.99%+)
- Valid mode share percentages (0-100%)

## Usage

### 1. Validate Data Context

```bash
poetry run python great_expectations/validate_context.py
```

This verifies:
- Great Expectations configuration is valid
- DuckDB connection works
- All data assets are accessible

### 2. Create/Update Expectation Suites

```bash
poetry run python great_expectations/create_expectation_suites.py
```

This creates or updates all 10 expectation suites with comprehensive data quality rules.

### 3. Run Validations

```bash
poetry run python great_expectations/run_validations.py
```

This:
- Runs all 10 validation checkpoints
- Generates validation results
- Builds data docs
- Outputs summary statistics

### 4. View Data Docs

After running validations:

```bash
open great_expectations/uncommitted/data_docs/local_site/index.html
```

The data docs provide:
- Overview of all expectation suites
- Detailed validation results
- Data profiling statistics
- Historical validation trends

## Integration with dbt

Great Expectations validates the output of dbt models:

```
dbt run → DuckDB tables → Great Expectations → Validation Reports
```

Run after dbt builds to ensure data quality:

```bash
cd dbt && poetry run dbt build
poetry run python great_expectations/run_validations.py
```

## Integration with Dagster (Phase 9 Complete!)

Great Expectations can be integrated with Dagster to run validations as part of the pipeline. This will be added in the next phase.

## Data Sources

The `great_expectations.yml` configuration defines 3 data connectors:

1. **staging_connector**: Validates staging models in `core` schema
2. **dimensions_connector**: Validates dimension tables in `core_core` schema
3. **facts_connector**: Validates fact tables in `core_core` schema

## Checkpoints

Each model has a dedicated checkpoint (e.g., `chk_stg_yellow_taxi`) that:
- Defines which expectation suite to run
- Specifies the data asset to validate
- Configures actions (store results, update docs)

## Expectations Reference

Common expectation types used:

- **`expect_table_row_count_to_be_between`**: Validates row counts
- **`expect_column_values_to_not_be_null`**: Checks for required fields
- **`expect_column_values_to_be_unique`**: Ensures uniqueness
- **`expect_column_values_to_be_between`**: Validates numeric ranges
- **`expect_column_values_to_be_in_set`**: Checks categorical values

## Customization

### Adding New Expectations

Edit `create_expectation_suites.py` and add expectations to the appropriate suite:

```python
{
    "expectation_type": "expect_column_values_to_be_between",
    "kwargs": {
        "column": "your_column",
        "min_value": 0,
        "max_value": 100,
    },
}
```

Then regenerate suites:

```bash
poetry run python great_expectations/create_expectation_suites.py
```

### Adjusting Thresholds

If validations fail due to overly strict expectations:
1. Review failed expectations in data docs
2. Adjust thresholds in `create_expectation_suites.py`
3. Regenerate suites
4. Re-run validations

## Troubleshooting

### Connection Errors

If you see DuckDB connection errors:
- Verify the database path in `great_expectations.yml`
- Ensure dbt models have been built
- Check file permissions

### Schema Errors

If tables aren't found:
- Run `poetry run python great_expectations/validate_context.py`
- Verify schema names match dbt output
- Check `SHOW ALL TABLES` in DuckDB

### Failed Expectations

This is normal! Failed expectations indicate:
- Data quality issues to investigate
- Expectations that need tuning for your data
- Edge cases in the data

Review data docs to understand failures and adjust accordingly.

## Next Steps

- Fine-tune expectation thresholds based on actual data characteristics
- Add custom expectations for business-specific rules
- Integrate with Dagster for automated validation
- Set up alerts for validation failures
- Add data profiling for new datasets

## Documentation

- [Great Expectations Docs](https://docs.greatexpectations.io/)
- [Expectation Gallery](https://greatexpectations.io/expectations/)
- [DuckDB Integration](https://docs.greatexpectations.io/docs/guides/connecting_to_your_data/database/duckdb/)
