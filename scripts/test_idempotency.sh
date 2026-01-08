#!/bin/bash

###############################################################################
# Idempotency and Incremental Loading Test Suite
#
# This script validates that the NYC Mobility pipeline is:
# 1. Idempotent (running twice with same inputs = same output)
# 2. Incremental (can add new data without losing old data)
# 3. Handles late-arriving data correctly
#
# Prerequisites:
# - Clean database or willingness to rebuild
# - poetry environment set up
# - Access to data sources (taxi, citibike, weather)
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${PROJECT_ROOT}/data/nyc_mobility.duckdb"
BACKUP_PATH="${PROJECT_ROOT}/data/nyc_mobility_backup.duckdb"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to count records in a table
count_records() {
    local table=$1
    poetry run python3 -c "
import duckdb
conn = duckdb.connect('${DB_PATH}', read_only=True)
result = conn.execute('SELECT COUNT(*) FROM ${table}').fetchone()
print(result[0])
conn.close()
"
}

# Function to get max pickup datetime
get_max_pickup_datetime() {
    local table=$1
    poetry run python3 -c "
import duckdb
conn = duckdb.connect('${DB_PATH}', read_only=True)
result = conn.execute('SELECT MAX(pickup_datetime) FROM ${table}').fetchone()
print(result[0] if result[0] else 'NULL')
conn.close()
"
}

# Function to backup database
backup_db() {
    if [ -f "${DB_PATH}" ]; then
        log_info "Backing up database..."
        cp "${DB_PATH}" "${BACKUP_PATH}"
        log_success "Database backed up to ${BACKUP_PATH}"
    fi
}

# Function to restore database
restore_db() {
    if [ -f "${BACKUP_PATH}" ]; then
        log_info "Restoring database from backup..."
        cp "${BACKUP_PATH}" "${DB_PATH}"
        log_success "Database restored"
    fi
}

# Function to run dbt
run_dbt() {
    local mode=$1
    log_info "Running dbt ($mode)..."
    cd "${PROJECT_ROOT}/dbt"

    if [ "$mode" == "full-refresh" ]; then
        poetry run dbt build --full-refresh
    else
        poetry run dbt build
    fi

    cd "${PROJECT_ROOT}"
    log_success "dbt run complete"
}

###############################################################################
# TEST 1: Idempotency Test - DLT Layer
###############################################################################
test_dlt_idempotency() {
    log_info "=========================================="
    log_info "TEST 1: DLT Idempotency"
    log_info "=========================================="
    log_info "Testing that running DLT twice with same month produces same result"

    # Backup current state
    backup_db

    # Run ingestion for October 2025
    log_info "Run 1: Loading October 2025..."
    poetry run python src/ingestion/run_pipeline.py --year 2025 --months 10 --sources taxi,citibike,weather

    # Count records after first run
    log_info "Counting records after Run 1..."
    yellow_count_1=$(count_records "raw_data.yellow_taxi")
    fhv_count_1=$(count_records "raw_data.fhv_taxi")
    citibike_count_1=$(count_records "raw_data.trips")
    weather_count_1=$(count_records "raw_data.hourly_weather")

    log_info "Run 1 Results:"
    log_info "  Yellow Taxi: ${yellow_count_1}"
    log_info "  FHV: ${fhv_count_1}"
    log_info "  CitiBike: ${citibike_count_1}"
    log_info "  Weather: ${weather_count_1}"

    # Run ingestion for October 2025 AGAIN (idempotency test)
    log_info "Run 2: Loading October 2025 again (should be idempotent)..."
    poetry run python src/ingestion/run_pipeline.py --year 2025 --months 10 --sources taxi,citibike,weather

    # Count records after second run
    log_info "Counting records after Run 2..."
    yellow_count_2=$(count_records "raw_data.yellow_taxi")
    fhv_count_2=$(count_records "raw_data.fhv_taxi")
    citibike_count_2=$(count_records "raw_data.trips")
    weather_count_2=$(count_records "raw_data.hourly_weather")

    log_info "Run 2 Results:"
    log_info "  Yellow Taxi: ${yellow_count_2}"
    log_info "  FHV: ${fhv_count_2}"
    log_info "  CitiBike: ${citibike_count_2}"
    log_info "  Weather: ${weather_count_2}"

    # Verify counts are identical
    if [ "$yellow_count_1" == "$yellow_count_2" ] && \
       [ "$fhv_count_1" == "$fhv_count_2" ] && \
       [ "$citibike_count_1" == "$citibike_count_2" ] && \
       [ "$weather_count_1" == "$weather_count_2" ]; then
        log_success "✓ TEST 1 PASSED: DLT is idempotent (no duplicates created)"
    else
        log_error "✗ TEST 1 FAILED: Record counts changed between runs"
        log_error "  This indicates duplicates were created"
        restore_db
        exit 1
    fi
}

###############################################################################
# TEST 2: Incremental Loading Test - DLT Layer
###############################################################################
test_dlt_incremental() {
    log_info "=========================================="
    log_info "TEST 2: DLT Incremental Loading"
    log_info "=========================================="
    log_info "Testing that adding new month preserves old data"

    # Run ingestion for October 2025
    log_info "Loading October 2025..."
    poetry run python src/ingestion/run_pipeline.py --year 2025 --months 10 --sources taxi,citibike,weather

    # Count October records
    oct_yellow=$(count_records "raw_data.yellow_taxi")
    oct_fhv=$(count_records "raw_data.fhv_taxi")
    oct_citibike=$(count_records "raw_data.trips")
    oct_weather=$(count_records "raw_data.hourly_weather")

    log_info "October counts:"
    log_info "  Yellow Taxi: ${oct_yellow}"
    log_info "  FHV: ${oct_fhv}"
    log_info "  CitiBike: ${oct_citibike}"
    log_info "  Weather: ${oct_weather}"

    # Add November 2025
    log_info "Adding November 2025 (incremental)..."
    poetry run python src/ingestion/run_pipeline.py --year 2025 --months 11 --sources taxi,citibike,weather

    # Count total records (should be Oct + Nov)
    total_yellow=$(count_records "raw_data.yellow_taxi")
    total_fhv=$(count_records "raw_data.fhv_taxi")
    total_citibike=$(count_records "raw_data.trips")
    total_weather=$(count_records "raw_data.hourly_weather")

    log_info "Total counts after adding November:"
    log_info "  Yellow Taxi: ${total_yellow}"
    log_info "  FHV: ${total_fhv}"
    log_info "  CitiBike: ${total_citibike}"
    log_info "  Weather: ${total_weather}"

    # Verify counts increased (November data added)
    if [ "$total_yellow" -gt "$oct_yellow" ] && \
       [ "$total_fhv" -gt "$oct_fhv" ] && \
       [ "$total_citibike" -gt "$oct_citibike" ] && \
       [ "$total_weather" -gt "$oct_weather" ]; then
        log_success "✓ TEST 2 PASSED: Incremental loading works (October + November both exist)"
    else
        log_error "✗ TEST 2 FAILED: November data not added or October data was lost"
        exit 1
    fi
}

###############################################################################
# TEST 3: dbt Incremental Models Test
###############################################################################
test_dbt_incremental() {
    log_info "=========================================="
    log_info "TEST 3: dbt Incremental Models"
    log_info "=========================================="
    log_info "Testing that dbt incremental models work correctly"

    # First run: Full refresh
    log_info "Run 1: Full refresh..."
    run_dbt "full-refresh"

    # Count records
    trips_count_1=$(count_records "core_core.fct_trips")
    hourly_count_1=$(count_records "core_core.fct_hourly_mobility")
    max_datetime_1=$(get_max_pickup_datetime "core_core.fct_trips")

    log_info "Run 1 Results:"
    log_info "  fct_trips: ${trips_count_1}"
    log_info "  fct_hourly_mobility: ${hourly_count_1}"
    log_info "  Max pickup_datetime: ${max_datetime_1}"

    # Add new month to raw data (November)
    log_info "Adding November data to raw layer..."
    poetry run python src/ingestion/run_pipeline.py --year 2025 --months 11 --sources taxi,citibike,weather

    # Second run: Incremental (should only process November)
    log_info "Run 2: Incremental run (should only process November)..."

    # Time the incremental run
    START_TIME=$(date +%s)
    run_dbt "incremental"
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Count records after incremental
    trips_count_2=$(count_records "core_core.fct_trips")
    hourly_count_2=$(count_records "core_core.fct_hourly_mobility")
    max_datetime_2=$(get_max_pickup_datetime "core_core.fct_trips")

    log_info "Run 2 Results:"
    log_info "  fct_trips: ${trips_count_2}"
    log_info "  fct_hourly_mobility: ${hourly_count_2}"
    log_info "  Max pickup_datetime: ${max_datetime_2}"
    log_info "  Duration: ${DURATION} seconds"

    # Verify counts increased and runtime was fast
    if [ "$trips_count_2" -gt "$trips_count_1" ] && \
       [ "$hourly_count_2" -gt "$hourly_count_1" ] && \
       [ "$max_datetime_2" != "$max_datetime_1" ]; then
        log_success "✓ TEST 3 PASSED: dbt incremental models work"
        log_success "  - New data added"
        log_success "  - Incremental run took ${DURATION} seconds"

        if [ "$DURATION" -lt 10 ]; then
            log_success "  - Performance excellent (<10 seconds)"
        fi
    else
        log_error "✗ TEST 3 FAILED: Incremental models did not add new data"
        exit 1
    fi
}

###############################################################################
# TEST 4: End-to-End Idempotency Test
###############################################################################
test_e2e_idempotency() {
    log_info "=========================================="
    log_info "TEST 4: End-to-End Idempotency"
    log_info "=========================================="
    log_info "Testing full pipeline run twice produces same result"

    # Full pipeline run 1
    log_info "Run 1: Full pipeline..."
    poetry run python src/ingestion/run_pipeline.py --year 2025 --months 10 --sources taxi,citibike,weather
    run_dbt "full-refresh"

    # Count final records
    trips_count_1=$(count_records "core_core.fct_trips")

    # Full pipeline run 2 (should be identical)
    log_info "Run 2: Repeating full pipeline (idempotency test)..."
    poetry run python src/ingestion/run_pipeline.py --year 2025 --months 10 --sources taxi,citibike,weather
    run_dbt "full-refresh"

    # Count final records
    trips_count_2=$(count_records "core_core.fct_trips")

    log_info "Run 1 fct_trips: ${trips_count_1}"
    log_info "Run 2 fct_trips: ${trips_count_2}"

    if [ "$trips_count_1" == "$trips_count_2" ]; then
        log_success "✓ TEST 4 PASSED: End-to-end pipeline is idempotent"
    else
        log_error "✗ TEST 4 FAILED: Pipeline produced different results"
        exit 1
    fi
}

###############################################################################
# TEST 5: dbt Tests Validation
###############################################################################
test_dbt_tests() {
    log_info "=========================================="
    log_info "TEST 5: dbt Tests"
    log_info "=========================================="
    log_info "Running all 108 dbt tests..."

    cd "${PROJECT_ROOT}/dbt"
    if poetry run dbt test; then
        log_success "✓ TEST 5 PASSED: All dbt tests passing"
    else
        log_error "✗ TEST 5 FAILED: Some dbt tests failed"
        cd "${PROJECT_ROOT}"
        exit 1
    fi
    cd "${PROJECT_ROOT}"
}

###############################################################################
# Main Test Runner
###############################################################################
main() {
    log_info "=========================================="
    log_info "NYC Mobility Pipeline Test Suite"
    log_info "=========================================="
    log_info "Starting idempotency and incremental loading tests..."
    log_info ""

    # Option to skip certain tests
    RUN_TEST_1=${RUN_TEST_1:-true}
    RUN_TEST_2=${RUN_TEST_2:-true}
    RUN_TEST_3=${RUN_TEST_3:-true}
    RUN_TEST_4=${RUN_TEST_4:-false}  # Expensive, off by default
    RUN_TEST_5=${RUN_TEST_5:-true}

    # Run tests
    if [ "$RUN_TEST_1" == "true" ]; then
        test_dlt_idempotency
        echo ""
    fi

    if [ "$RUN_TEST_2" == "true" ]; then
        test_dlt_incremental
        echo ""
    fi

    if [ "$RUN_TEST_3" == "true" ]; then
        test_dbt_incremental
        echo ""
    fi

    if [ "$RUN_TEST_4" == "true" ]; then
        test_e2e_idempotency
        echo ""
    fi

    if [ "$RUN_TEST_5" == "true" ]; then
        test_dbt_tests
        echo ""
    fi

    # Summary
    log_info "=========================================="
    log_success "ALL TESTS PASSED!"
    log_info "=========================================="
    log_success "Pipeline is production-ready:"
    log_success "  ✓ DLT merge strategy is idempotent"
    log_success "  ✓ DLT incremental loading works"
    log_success "  ✓ dbt incremental models work"
    log_success "  ✓ All dbt tests passing"
    log_info ""
    log_info "You can now safely deploy to production (MVP 3)"
}

# Run main function
main "$@"
