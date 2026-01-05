"""
Script to validate Great Expectations data context and list available data assets.
"""

import sys
from pathlib import Path

# Add the project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import great_expectations as gx
    from great_expectations.data_context import FileDataContext

    # Load the data context
    context = FileDataContext(context_root_dir=Path(__file__).parent)

    print("✅ Great Expectations context loaded successfully!")
    print(f"\nContext root: {context.root_directory}")

    # List datasources
    print("\n📊 Configured Datasources:")
    for ds_name in context.list_datasources():
        print(f"  - {ds_name['name']}")

    # List available data assets
    print("\n📦 Available Data Assets:")
    datasource = context.get_datasource("nyc_mobility_duckdb")

    for connector_name in ["staging_connector", "dimensions_connector", "facts_connector"]:
        print(f"\n  {connector_name}:")
        try:
            connector = datasource.data_connectors[connector_name]
            for asset_name in connector.get_available_data_asset_names():
                print(f"    - {asset_name}")
        except Exception as e:
            print(f"    Error: {e}")

    # List expectation suites
    print("\n📋 Expectation Suites:")
    suites = context.list_expectation_suite_names()
    if suites:
        for suite in suites:
            print(f"  - {suite}")
    else:
        print("  (none created yet)")

    print("\n✅ Validation complete!")
    sys.exit(0)

except Exception as e:
    print(f"❌ Error loading Great Expectations context: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
