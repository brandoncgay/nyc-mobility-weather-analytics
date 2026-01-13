"""
Script to create Great Expectations expectation suites for all data assets.

This script creates comprehensive expectation suites for:
- Staging models (data quality and completeness)
- Dimension tables (referential integrity and validity)
- Fact tables (metrics and business rules)
"""

import sys
from pathlib import Path

import great_expectations as gx
from great_expectations.core.batch import BatchRequest
from great_expectations.core.expectation_configuration import ExpectationConfiguration
from great_expectations.data_context import FileDataContext

# Add the project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def create_staging_expectations(context: FileDataContext):
    """Create expectation suites for staging models."""
    print("\n📋 Creating expectation suites for staging models...")

    # Common expectations for all staging models
    common_staging_expectations = [
        {
            "expectation_type": "expect_table_row_count_to_be_between",
            "kwargs": {"min_value": 1000},
        }
    ]

    # Staging model-specific expectations
    staging_suites = {
        "stg_yellow_taxi": [
            *common_staging_expectations,
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "trip_id"},
            },
            {
                "expectation_type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "trip_id"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "pickup_datetime"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "dropoff_datetime"},
            },
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "trip_distance",
                    "min_value": 0,
                    "mostly": 0.99,  # Allow 1% outliers
                },
            },
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "total_amount",
                    "min_value": -10,  # Allow small negative adjustments
                    "max_value": 5000,  # Very high but catches extreme data errors
                    "mostly": 0.99,  # Allow 1% outliers
                },
            },
        ],
        "stg_fhv_taxi": [
            *common_staging_expectations,
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "trip_id"},
            },
            {
                "expectation_type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "trip_id"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "pickup_datetime"},
            },
        ],
        "stg_citibike__trips": [
            *common_staging_expectations,
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "trip_id"},
            },
            {
                "expectation_type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "trip_id"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "pickup_datetime"},
            },
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "member_casual",
                    "value_set": ["member", "casual"],
                },
            },
        ],
        "stg_weather__hourly": [
            {
                "expectation_type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 100},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "timestamp"},
            },
            {
                "expectation_type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "timestamp"},
            },
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {"column": "temp", "min_value": -30, "max_value": 50},
            },
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {"column": "humidity", "min_value": 0, "max_value": 100},
            },
        ],
    }

    for suite_name, expectations in staging_suites.items():
        print(f"  Creating suite: {suite_name}")

        # Delete existing suite if it exists
        try:
            context.delete_expectation_suite(expectation_suite_name=suite_name)
            print(f"    Deleted existing suite: {suite_name}")
        except Exception:
            pass  # Suite doesn't exist, which is fine

        suite = context.add_expectation_suite(expectation_suite_name=suite_name)

        for exp_config in expectations:
            expectation = ExpectationConfiguration(**exp_config)
            suite.expectations.append(expectation)

        context.save_expectation_suite(expectation_suite=suite)

    print("  ✅ Staging expectation suites created")


def create_dimension_expectations(context: FileDataContext):
    """Create expectation suites for dimension tables."""
    print("\n📋 Creating expectation suites for dimension tables...")

    dimension_suites = {
        "dim_date": [
            {
                "expectation_type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 90},  # At least 3 months
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "date_key"},
            },
            {
                "expectation_type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "date_key"},
            },
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {"column": "is_weekend", "value_set": [True, False]},
            },
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {"column": "day_of_month", "min_value": 1, "max_value": 31},
            },
        ],
        "dim_time": [
            {
                "expectation_type": "expect_table_row_count_to_equal",
                "kwargs": {"value": 24},  # Exactly 24 hours
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "time_key"},
            },
            {
                "expectation_type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "time_key"},
            },
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {"column": "hour", "min_value": 0, "max_value": 23},
            },
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "day_part",
                    "value_set": ["morning", "afternoon", "evening", "night"],
                },
            },
        ],
        "dim_weather": [
            {
                "expectation_type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 100},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "weather_key"},
            },
            {
                "expectation_type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "weather_key"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "timestamp"},
            },
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "temp_category",
                    "value_set": ["cold", "cool", "mild", "warm", "hot"],
                },
            },
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "is_adverse_weather",
                    "value_set": [True, False],
                },
            },
        ],
        "dim_location": [
            {
                "expectation_type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 200},  # NYC has ~260 taxi zones
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "location_id"},
            },
            {
                "expectation_type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "location_id"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "zone_name"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "borough"},
            },
        ],
    }

    for suite_name, expectations in dimension_suites.items():
        print(f"  Creating suite: {suite_name}")

        # Delete existing suite if it exists
        try:
            context.delete_expectation_suite(expectation_suite_name=suite_name)
            print(f"    Deleted existing suite: {suite_name}")
        except Exception:
            pass  # Suite doesn't exist, which is fine

        suite = context.add_expectation_suite(expectation_suite_name=suite_name)

        for exp_config in expectations:
            expectation = ExpectationConfiguration(**exp_config)
            suite.expectations.append(expectation)

        context.save_expectation_suite(expectation_suite=suite)

    print("  ✅ Dimension expectation suites created")


def create_fact_expectations(context: FileDataContext):
    """Create expectation suites for fact tables."""
    print("\n📋 Creating expectation suites for fact tables...")

    fact_suites = {
        "fct_trips": [
            {
                "expectation_type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 1000000},  # At least 1M trips
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "trip_key"},
            },
            {
                "expectation_type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "trip_key"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "pickup_datetime"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "date_key"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "time_key"},
            },
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "trip_type",
                    "value_set": ["yellow_taxi", "fhv", "citibike"],
                },
            },
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "trip_duration_minutes",
                    "min_value": 0,
                    "max_value": 1440,  # 24 hours max
                },
            },
        ],
        "fct_hourly_mobility": [
            {
                "expectation_type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 100},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "hour_timestamp"},
            },
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "trip_type"},
            },
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {
                    "column": "trip_type",
                    "value_set": ["yellow_taxi", "fhv", "citibike"],
                },
            },
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {"column": "trip_count", "min_value": 0},
            },
            {
                "expectation_type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "citibike_mode_share_pct",
                    "min_value": 0,
                    "max_value": 100,
                },
            },
        ],
    }

    for suite_name, expectations in fact_suites.items():
        print(f"  Creating suite: {suite_name}")

        # Delete existing suite if it exists
        try:
            context.delete_expectation_suite(expectation_suite_name=suite_name)
            print(f"    Deleted existing suite: {suite_name}")
        except Exception:
            pass  # Suite doesn't exist, which is fine

        suite = context.add_expectation_suite(expectation_suite_name=suite_name)

        for exp_config in expectations:
            expectation = ExpectationConfiguration(**exp_config)
            suite.expectations.append(expectation)

        context.save_expectation_suite(expectation_suite=suite)

    print("  ✅ Fact expectation suites created")


def main():
    """Main function to create all expectation suites."""
    print("🎯 Creating Great Expectations expectation suites...")

    try:
        # Load the data context
        context = FileDataContext(context_root_dir=Path(__file__).parent)

        # Create expectation suites for each layer
        create_staging_expectations(context)
        create_dimension_expectations(context)
        create_fact_expectations(context)

        print("\n✅ All expectation suites created successfully!")
        print(f"\nTotal suites: {len(context.list_expectation_suite_names())}")
        print("\nSuites created:")
        for suite_name in sorted(context.list_expectation_suite_names()):
            print(f"  - {suite_name}")

        return 0

    except Exception as e:
        print(f"\n❌ Error creating expectation suites: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
