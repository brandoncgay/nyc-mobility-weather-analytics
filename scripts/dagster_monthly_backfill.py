"""
Run monthly backfill via Dagster programmatically.

This script loads multiple months sequentially using Dagster's monthly_ingestion job.
Each month goes through: DLT Ingestion → dbt Transform → Validation
"""

import argparse
import sys
from pathlib import Path

from dagster import DagsterInstance
from dagster._core.execution.api import create_execution_plan, execute_plan
from dagster._core.storage.dagster_run import DagsterRun, DagsterRunStatus

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from orchestration import defs


def load_month(year: int, month: int, sources: str = "taxi,citibike,weather") -> bool:
    """
    Load data for a single month using Dagster.

    Args:
        year: Year to load (e.g., 2025)
        month: Month to load (1-12)
        sources: Comma-separated sources (e.g., "taxi,citibike,weather")

    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Loading {year}-{month:02d} ({sources})")
    print(f"{'='*60}\n")

    instance = DagsterInstance.get()
    job = defs.get_job_def("monthly_ingestion")

    run_config = {
        "ops": {
            "monthly_dlt_ingestion": {
                "config": {
                    "year": year,
                    "month": month,
                    "sources": sources,
                }
            }
        }
    }

    # Create a run
    run = instance.create_run_for_job(
        job,
        run_config=run_config,
        tags={
            "year": str(year),
            "month": str(month),
            "sources": sources,
        },
    )

    # Execute the run
    try:
        # Create execution plan
        execution_plan = create_execution_plan(job, run_config=run_config)

        # Execute
        events = execute_plan(
            execution_plan,
            job,
            instance,
            run,
        )

        # Check result
        final_run = instance.get_run_by_id(run.run_id)

        if final_run.status == DagsterRunStatus.SUCCESS:
            print(f"\n✓ {year}-{month:02d} completed successfully")
            print(f"  Run ID: {run.run_id}")
            return True
        else:
            print(f"\n✗ {year}-{month:02d} failed with status: {final_run.status}")
            print(f"  Run ID: {run.run_id}")
            print(f"  Check Dagster UI for details: http://localhost:3000")
            return False

    except Exception as e:
        print(f"\n✗ {year}-{month:02d} failed with exception: {e}")
        return False


def backfill_months(
    year: int,
    months: list[int],
    sources: str = "taxi,citibike,weather",
    continue_on_error: bool = False,
) -> dict:
    """
    Load multiple months sequentially.

    Args:
        year: Year to load
        months: List of months (e.g., [7, 8, 9, 10, 11, 12])
        sources: Comma-separated sources
        continue_on_error: If True, continue even if a month fails

    Returns:
        dict: Summary of results
    """
    print(f"\n{'='*60}")
    print(f"DAGSTER MONTHLY BACKFILL")
    print(f"{'='*60}")
    print(f"Year: {year}")
    print(f"Months: {', '.join(str(m) for m in months)}")
    print(f"Sources: {sources}")
    print(f"{'='*60}\n")

    results = {
        "successful": [],
        "failed": [],
        "total": len(months),
    }

    for month in months:
        success = load_month(year, month, sources)

        if success:
            results["successful"].append(month)
        else:
            results["failed"].append(month)

            if not continue_on_error:
                print(f"\n⚠️ Stopping backfill due to failure at month {month}")
                print(f"   Use --continue-on-error to continue despite failures")
                break

    # Summary
    print(f"\n{'='*60}")
    print(f"BACKFILL SUMMARY")
    print(f"{'='*60}")
    print(f"Total months: {results['total']}")
    print(f"Successful: {len(results['successful'])} - {results['successful']}")
    print(f"Failed: {len(results['failed'])} - {results['failed']}")

    if results['failed']:
        print(f"\n⚠️ Some months failed. Check Dagster UI for details.")
        print(f"   http://localhost:3000")
    else:
        print(f"\n✓ All months loaded successfully!")

    print(f"{'='*60}\n")

    return results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run monthly backfill via Dagster",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load Q4 2025
  python scripts/dagster_monthly_backfill.py --year 2025 --months 10,11,12

  # Load all of 2025
  python scripts/dagster_monthly_backfill.py --year 2025 --months 1,2,3,4,5,6,7,8,9,10,11,12

  # Load only weather for multiple months
  python scripts/dagster_monthly_backfill.py --year 2025 --months 7,8,9 --sources weather

  # Continue even if a month fails
  python scripts/dagster_monthly_backfill.py --year 2025 --months 10,11,12 --continue-on-error
        """,
    )

    parser.add_argument(
        "--year",
        type=int,
        default=2025,
        help="Year to load (default: 2025)",
    )

    parser.add_argument(
        "--months",
        type=str,
        default="10,11,12",
        help="Comma-separated months to load (default: 10,11,12)",
    )

    parser.add_argument(
        "--sources",
        type=str,
        default="taxi,citibike,weather",
        help="Comma-separated sources (default: taxi,citibike,weather)",
    )

    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue loading remaining months even if one fails",
    )

    args = parser.parse_args()

    # Parse months
    try:
        months = [int(m.strip()) for m in args.months.split(",")]

        # Validate months
        for month in months:
            if month < 1 or month > 12:
                print(f"Error: Invalid month {month}. Must be 1-12.")
                sys.exit(1)

    except ValueError:
        print(f"Error: Invalid months format '{args.months}'. Use comma-separated numbers.")
        sys.exit(1)

    # Run backfill
    results = backfill_months(
        year=args.year,
        months=months,
        sources=args.sources,
        continue_on_error=args.continue_on_error,
    )

    # Exit code based on results
    if results["failed"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
