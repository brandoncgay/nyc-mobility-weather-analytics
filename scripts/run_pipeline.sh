#!/bin/bash
# Pipeline Runner Script
# Usage: ./scripts/run_pipeline.sh [option]
# Options: full, quick, test, validate, backfill

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() { echo -e "${BLUE}ℹ ${1}${NC}"; }
log_success() { echo -e "${GREEN}✅ ${1}${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  ${1}${NC}"; }
log_error() { echo -e "${RED}❌ ${1}${NC}"; }

# Function to check if database exists
check_database() {
    if [ ! -f "data/nyc_mobility.duckdb" ]; then
        log_error "Database not found at data/nyc_mobility.duckdb"
        log_info "Please run the ingestion pipeline first:"
        log_info "  poetry run python src/ingestion/run_pipeline.py"
        log_info "  OR run: ./scripts/run_pipeline.sh full"
        exit 1
    fi
    log_success "Database found"
}

# Function to run ingestion only
run_ingestion() {
    log_info "Running DLT data ingestion..."

    log_info "Ingesting data from sources:"
    log_info "  - NYC TLC Yellow Taxi (~8.6M trips)"
    log_info "  - CitiBike System Data (~1.4M trips)"
    log_info "  - Open-Meteo Weather API (~1.5K hours)"

    poetry run python src/ingestion/run_pipeline.py

    log_success "Data ingestion completed!"
    log_info "Database: data/nyc_mobility.duckdb"
}

# Function to run full pipeline
run_full() {
    log_info "Running FULL end-to-end pipeline..."

    log_info "Step 1/6: Running DLT data ingestion (taxi, citibike, weather)..."
    poetry run python src/ingestion/run_pipeline.py

    log_info "Step 2/6: Installing dbt dependencies..."
    cd dbt
    poetry run dbt deps

    log_info "Step 3/6: Running dbt build (all models + tests)..."
    poetry run dbt build

    log_info "Step 4/6: Generating dbt documentation..."
    poetry run dbt docs generate

    cd ..
    log_info "Step 5/6: Running Great Expectations validations..."
    poetry run python great_expectations/run_validations.py

    log_info "Step 6/6: Generating validation summary..."
    echo ""
    echo "========================================="
    echo "Pipeline Execution Complete!"
    echo "========================================="
    poetry run python -c "
import duckdb
import json

conn = duckdb.connect('data/nyc_mobility.duckdb')

print('\n📊 Row Counts:')
print(f\"  Staging Models: {conn.execute('SELECT COUNT(*) FROM core.stg_tlc__yellow_taxi').fetchone()[0] + conn.execute('SELECT COUNT(*) FROM core.stg_tlc__fhv_taxi').fetchone()[0] + conn.execute('SELECT COUNT(*) FROM core.stg_citibike__trips').fetchone()[0]:,}\")
print(f\"  Fact - Trips: {conn.execute('SELECT COUNT(*) FROM core_core.fct_trips').fetchone()[0]:,}\")
print(f\"  Fact - Hourly Mobility: {conn.execute('SELECT COUNT(*) FROM core_core.fct_hourly_mobility').fetchone()[0]:,}\")

# Check weather coverage
coverage = conn.execute('''
    SELECT ROUND(100.0 * SUM(CASE WHEN weather_key IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 4)
    FROM core_core.fct_trips
''').fetchone()[0]
print(f\"\n✅ Weather Join Coverage: {coverage}%\")

# Check test results
with open('dbt/target/run_results.json') as f:
    results = json.load(f)
    total = len(results['results'])
    passed = sum(1 for r in results['results'] if r['status'] == 'success')
    print(f\"\n✅ dbt Tests: {passed}/{total} passing\")

conn.close()
"

    log_success "Pipeline completed successfully!"
    log_info "View docs: cd dbt && poetry run dbt docs serve"
    log_info "View data quality: open great_expectations/uncommitted/data_docs/local_site/index.html"
}

# Function to run quick test
run_quick() {
    log_info "Running QUICK pipeline test..."

    check_database

    cd dbt
    log_info "Running staging models only..."
    poetry run dbt run --select staging

    log_info "Running one dimension..."
    poetry run dbt run --select dim_date

    log_info "Running one fact..."
    poetry run dbt run --select fct_trips

    log_info "Running tests on fct_trips..."
    poetry run dbt test --select fct_trips

    log_success "Quick test completed!"
}

# Function to run tests only
run_test() {
    log_info "Running TEST suite..."

    check_database

    cd dbt
    log_info "Running all dbt tests..."
    poetry run dbt test

    cd ..
    log_info "Running Great Expectations validations..."
    poetry run python great_expectations/run_validations.py

    log_success "All tests completed!"
}

# Function to validate results
run_validate() {
    log_info "Validating pipeline results..."

    check_database

    poetry run python -c "
import duckdb
import sys

conn = duckdb.connect('data/nyc_mobility.duckdb')

print('\\n🔍 Data Quality Validation:')
print('=' * 50)

# Check row counts
checks = [
    ('Staging - Yellow Taxi', 'SELECT COUNT(*) FROM core.stg_tlc__yellow_taxi', 8_000_000, 9_000_000),
    ('Staging - FHV', 'SELECT COUNT(*) FROM core.stg_tlc__fhv_taxi', 2_000_000, 3_000_000),
    ('Staging - CitiBike', 'SELECT COUNT(*) FROM core.stg_citibike__trips', 1_000_000, 2_000_000),
    ('Dimension - Date', 'SELECT COUNT(*) FROM core_core.dim_date', 120, 125),
    ('Dimension - Time', 'SELECT COUNT(*) FROM core_core.dim_time', 24, 24),
    ('Dimension - Weather', 'SELECT COUNT(*) FROM core_core.dim_weather', 1_400, 1_500),
    ('Dimension - Location', 'SELECT COUNT(*) FROM core_core.dim_location', 260, 270),
    ('Fact - Trips', 'SELECT COUNT(*) FROM core_core.fct_trips', 12_000_000, 13_000_000),
    ('Fact - Hourly Mobility', 'SELECT COUNT(*) FROM core_core.fct_hourly_mobility', 4_000, 5_000),
]

all_passed = True
for name, query, min_expected, max_expected in checks:
    try:
        actual = conn.execute(query).fetchone()[0]
        passed = min_expected <= actual <= max_expected
        status = '✅' if passed else '❌'
        print(f'{status} {name:30} {actual:>12,} (expected {min_expected:,}-{max_expected:,})')
        if not passed:
            all_passed = False
    except Exception as e:
        print(f'❌ {name:30} ERROR: {e}')
        all_passed = False

# Check weather coverage
print('\\n🌤️  Weather Join Coverage:')
coverage_result = conn.execute('''
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN weather_key IS NOT NULL THEN 1 ELSE 0 END) as with_weather,
        ROUND(100.0 * SUM(CASE WHEN weather_key IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 4) as pct
    FROM core_core.fct_trips
''').fetchone()
coverage_pct = coverage_result[2]
coverage_passed = coverage_pct >= 99.99
status = '✅' if coverage_passed else '❌'
print(f'{status} Coverage: {coverage_pct}% ({coverage_result[1]:,}/{coverage_result[0]:,})')
if not coverage_passed:
    all_passed = False

# Check for nulls in key columns
print('\\n🔑 Key Column Completeness:')
null_checks = [
    ('fct_trips.trip_key', 'SELECT COUNT(*) FROM core_core.fct_trips WHERE trip_key IS NULL'),
    ('fct_trips.date_key', 'SELECT COUNT(*) FROM core_core.fct_trips WHERE date_key IS NULL'),
    ('dim_date.date_key', 'SELECT COUNT(*) FROM core_core.dim_date WHERE date_key IS NULL'),
]

for name, query in null_checks:
    nulls = conn.execute(query).fetchone()[0]
    status = '✅' if nulls == 0 else '❌'
    print(f'{status} {name:30} {nulls} nulls')
    if nulls > 0:
        all_passed = False

conn.close()

print('\\n' + '=' * 50)
if all_passed:
    print('✅ All validations PASSED!')
    sys.exit(0)
else:
    print('❌ Some validations FAILED!')
    sys.exit(1)
"

    if [ $? -eq 0 ]; then
        log_success "Validation passed!"
    else
        log_error "Validation failed!"
        exit 1
    fi
}

# Function to run backfill
run_backfill() {
    log_info "Running BACKFILL (full refresh)..."

    check_database

    cd dbt
    log_warning "This will drop and rebuild all models"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Backfill cancelled"
        exit 0
    fi

    log_info "Running full refresh..."
    poetry run dbt build --full-refresh

    log_success "Backfill completed!"
}

# Main script
case "${1:-full}" in
    full)
        run_full
        ;;
    ingestion)
        run_ingestion
        ;;
    quick)
        run_quick
        ;;
    test)
        run_test
        ;;
    validate)
        run_validate
        ;;
    backfill)
        run_backfill
        ;;
    *)
        echo "Usage: $0 {full|ingestion|quick|test|validate|backfill}"
        echo ""
        echo "Commands:"
        echo "  full      - Run complete end-to-end pipeline (DLT + dbt + tests + validation)"
        echo "  ingestion - Run DLT data ingestion only (yellow taxi + citibike + weather)"
        echo "  quick     - Run quick test (staging + 1 dim + 1 fact)"
        echo "  test      - Run all tests only"
        echo "  validate  - Validate data quality and row counts"
        echo "  backfill  - Full refresh all models (drops and rebuilds)"
        exit 1
        ;;
esac
