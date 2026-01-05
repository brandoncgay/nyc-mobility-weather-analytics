"""
Script to validate Dagster definitions can be loaded correctly.
"""

import sys
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from orchestration import defs

    print("✅ Dagster definitions loaded successfully!")
    print(f"\nAssets: {len(defs.assets)}")
    print(f"Resources: {len(defs.resources)}")
    print(f"Schedules: {len(defs.schedules)}")

    # Show asset details
    if defs.assets:
        print("\n📦 Assets:")
        for asset in defs.assets:
            print(f"  - {asset}")

    # Show schedule details
    if defs.schedules:
        print("\n⏰ Schedules:")
        for schedule in defs.schedules:
            print(f"  - {schedule.name}: {schedule.cron_schedule}")

    sys.exit(0)

except Exception as e:
    print(f"❌ Error loading Dagster definitions: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
