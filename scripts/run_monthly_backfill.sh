#!/bin/bash
# Run monthly ingestion for May-Nov 2025
# This script uses the Dagster CLI to launch jobs for each month

set -e  # Exit on error

MONTHS=(5 6 7 8 9 10 11)
YEAR=2025

echo "=========================================="
echo "Monthly Ingestion: May-Nov 2025"
echo "=========================================="
echo ""

for MONTH in "${MONTHS[@]}"; do
    echo "Loading ${YEAR}-$(printf '%02d' $MONTH)..."
    
    uv run dagster job launch \
        -m orchestration \
        -j monthly_ingestion \
        -c <(cat <<EOF
ops:
  monthly_dlt_ingestion:
    config:
      year: ${YEAR}
      month: ${MONTH}
      sources: "taxi,citibike,weather"
  monthly_dbt_transformation:
    config:
      full_refresh: false
EOF
)
    
    echo "✓ Launched job for ${YEAR}-$(printf '%02d' $MONTH)"
    echo ""
    
    # Wait a bit between launches to avoid overwhelming the system
    sleep 2
done

echo "=========================================="
echo "All jobs launched!"
echo "Monitor progress at: http://localhost:3000/runs"
echo "=========================================="
