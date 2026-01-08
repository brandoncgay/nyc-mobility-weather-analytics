#!/bin/bash

###############################################################################
# Quick Incremental Loading Test
#
# Fast test to verify incremental loading works
# Use this for quick validation during development
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Count records
count_records() {
    poetry run python3 -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb', read_only=True)
result = conn.execute('SELECT COUNT(*) FROM $1').fetchone()
print(result[0])
conn.close()
"
}

log_info "Quick Incremental Loading Test"
log_info "==============================="

# Check current state
log_info "Current record counts:"
echo "  fct_trips: $(count_records core_core.fct_trips)"
echo "  raw yellow_taxi: $(count_records raw_data.yellow_taxi)"

log_info ""
log_info "To test incremental loading:"
log_info "1. Run: poetry run python src/ingestion/run_pipeline.py --months 10 --year 2025"
log_info "2. Run: cd dbt && poetry run dbt run"
log_info "3. Run: poetry run python src/ingestion/run_pipeline.py --months 11 --year 2025"
log_info "4. Run: cd dbt && poetry run dbt run"
log_info "5. Check counts again - should have increased"

log_success "Use scripts/test_idempotency.sh for full test suite"
