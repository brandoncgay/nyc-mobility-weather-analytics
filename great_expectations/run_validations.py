"""
Script to run Great Expectations validations and generate data docs.

This script:
1. Creates checkpoints for all expectation suites
2. Runs validations against the dbt models in DuckDB
3. Generates data docs with validation results
"""

import sys
from pathlib import Path

import great_expectations as gx
from great_expectations.checkpoint import Checkpoint
from great_expectations.core.batch import BatchRequest
from great_expectations.data_context import FileDataContext

# Add the project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def create_and_run_checkpoint(
    context: FileDataContext, checkpoint_name: str, suite_name: str, asset_name: str, connector_name: str
):
    """Create and run a checkpoint for a given expectation suite."""
    print(f"  Running validation: {suite_name}")

    # Create batch request
    batch_request = {
        "datasource_name": "nyc_mobility_duckdb",
        "data_connector_name": connector_name,
        "data_asset_name": asset_name,
    }

    # Create checkpoint configuration
    checkpoint_config = {
        "name": checkpoint_name,
        "config_version": 1.0,
        "class_name": "Checkpoint",
        "run_name_template": f"%Y%m%d-%H%M%S-{checkpoint_name}",
        "validations": [
            {
                "batch_request": batch_request,
                "expectation_suite_name": suite_name,
            }
        ],
        "action_list": [
            {
                "name": "store_validation_result",
                "action": {"class_name": "StoreValidationResultAction"},
            },
            {
                "name": "update_data_docs",
                "action": {"class_name": "UpdateDataDocsAction"},
            },
        ],
    }

    # Delete existing checkpoint if it exists
    try:
        context.delete_checkpoint(name=checkpoint_name)
    except Exception:
        pass

    # Add and run checkpoint
    checkpoint = context.add_checkpoint(**checkpoint_config)
    result = checkpoint.run()

    # Check if validation passed
    if result.success:
        print(f"    ✅ Validation passed")
    else:
        print(f"    ❌ Validation failed")
        # Print failure details
        for run_result in result.run_results.values():
            if not run_result.get("success"):
                validation_result = run_result.get("validation_result")
                if validation_result:
                    failed_expectations = [
                        exp
                        for exp in validation_result.results
                        if not exp.success
                    ]
                    print(f"    Failed expectations: {len(failed_expectations)}")

    return result


def main():
    """Main function to run all validations."""
    print("🎯 Running Great Expectations validations...")

    try:
        # Load the data context
        context = FileDataContext(context_root_dir=Path(__file__).parent)

        # Validation configuration: (checkpoint_name, suite_name, asset_name, connector_name)
        validations = [
            # Staging models
            ("chk_stg_yellow_taxi", "stg_yellow_taxi", "stg_tlc__yellow_taxi", "staging_connector"),
            ("chk_stg_fhv_taxi", "stg_fhv_taxi", "stg_tlc__fhv_taxi", "staging_connector"),
            ("chk_stg_citibike", "stg_citibike__trips", "stg_citibike__trips", "staging_connector"),
            ("chk_stg_weather", "stg_weather__hourly", "stg_weather__hourly", "staging_connector"),
            # Dimension tables
            ("chk_dim_date", "dim_date", "dim_date", "dimensions_connector"),
            ("chk_dim_time", "dim_time", "dim_time", "dimensions_connector"),
            ("chk_dim_weather", "dim_weather", "dim_weather", "dimensions_connector"),
            ("chk_dim_location", "dim_location", "dim_location", "dimensions_connector"),
            # Fact tables
            ("chk_fct_trips", "fct_trips", "fct_trips", "facts_connector"),
            ("chk_fct_hourly_mobility", "fct_hourly_mobility", "fct_hourly_mobility", "facts_connector"),
        ]

        print(f"\nRunning {len(validations)} validations...\n")

        total_passed = 0
        total_failed = 0

        # Run validations
        for checkpoint_name, suite_name, asset_name, connector_name in validations:
            result = create_and_run_checkpoint(
                context, checkpoint_name, suite_name, asset_name, connector_name
            )
            if result.success:
                total_passed += 1
            else:
                total_failed += 1

        print(f"\n📊 Validation Summary:")
        print(f"  ✅ Passed: {total_passed}")
        print(f"  ❌ Failed: {total_failed}")
        print(f"  Total: {len(validations)}")

        # Build data docs
        print("\n📚 Building data docs...")
        context.build_data_docs()

        docs_path = Path(__file__).parent / "uncommitted" / "data_docs" / "local_site" / "index.html"
        if docs_path.exists():
            print(f"  ✅ Data docs built successfully!")
            print(f"  Open in browser: file://{docs_path.absolute()}")
        else:
            print(f"  ⚠️  Data docs path not found at {docs_path}")

        print("\n✅ Validation complete!")
        return 0 if total_failed == 0 else 1

    except Exception as e:
        print(f"\n❌ Error running validations: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
