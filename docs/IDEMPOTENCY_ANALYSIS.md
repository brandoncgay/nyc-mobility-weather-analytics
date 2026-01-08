# Pipeline Idempotency & Incremental Loading Analysis

**Date**: January 7, 2026
**Status**: 🔴 **NOT PRODUCTION READY**

## Executive Summary

The current pipeline is **NOT idempotent** and **NOT incremental**. Running the pipeline multiple times will:
- ❌ Replace all existing data (data loss risk)
- ❌ Reprocess everything from scratch (inefficient)
- ❌ Create duplicates if run with overlapping date ranges
- ❌ Not handle late-arriving data

**Critical for Production**: This MUST be fixed before MVP 3 cloud deployment.

---

## Current State Analysis

### Layer 1: DLT Ingestion (Bronze)

**Location**: `src/ingestion/sources/*.py`

**Current Configuration**:
```python
@dlt.resource(name="yellow_taxi", write_disposition="replace")
@dlt.resource(name="fhv_taxi", write_disposition="replace")
@dlt.resource(name="citibike_trips", write_disposition="replace")
@dlt.resource(name="hourly_weather", write_disposition="replace")
```

**Issues**:
- ❌ `write_disposition="replace"` **REPLACES ALL DATA** on each run
- ❌ No primary keys defined for deduplication
- ❌ No incremental state tracking
- ❌ Running `--months 10,11` twice will:
  1. First run: Load Oct-Nov data
  2. Second run: **DELETE Oct-Nov**, reload Oct-Nov
  3. Result: Same data, but all historical runs are lost

**Impact**:
- **Data Loss**: Historical data is replaced
- **No Backfilling**: Can't add new months without reloading everything
- **No Reruns**: Can't safely rerun failed jobs

---

### Layer 2: dbt Staging (Bronze → Silver)

**Location**: `dbt/models/staging/**/*.sql`

**Current Configuration**:
```yaml
staging:
  +materialized: view
```

**Issues**:
- ⚠️ Views are recomputed on every query (not an issue for correctness)
- ✅ HAS deduplication logic using `row_number()` window functions
- ⚠️ Views don't persist, so deduplication happens repeatedly

**Impact**:
- **Performance**: Deduplication computed on every downstream query
- **Partial OK**: Views are deterministic (always same output for same input)

---

### Layer 3: dbt Marts (Silver)

**Location**: `dbt/models/marts/core/*.sql`

**Current Configuration**:
```yaml
marts:
  +materialized: table
```

**Issues**:
- ❌ `table` materialization does **FULL REFRESH** on every `dbt run`
- ❌ All 12.5M trips reprocessed every time
- ❌ Fact tables (`fct_trips`, `fct_hourly_mobility`) completely rebuilt
- ❌ No incremental processing based on new data

**Impact**:
- **Inefficiency**: 30-second build time for 12.5M records
- **Scalability**: Won't scale to billions of records
- **Downtime**: Tables briefly unavailable during rebuild

---

## What "Idempotent" and "Incremental" Mean

### Idempotency

**Definition**: Running the pipeline multiple times with the same inputs produces the same output.

**Good Example** (Idempotent):
```bash
# Run 1: Load Oct data
$ poetry run python src/ingestion/run_pipeline.py --months 10
# Result: 5M trips for October

# Run 2: Load Oct data again (accidental rerun)
$ poetry run python src/ingestion/run_pipeline.py --months 10
# Result: STILL 5M trips for October (no duplicates)
```

**Bad Example** (Current State - NOT Idempotent):
```bash
# Run 1: Load Oct data
$ poetry run python src/ingestion/run_pipeline.py --months 10
# Result: 5M trips for October

# Run 2: Load Oct data again
$ poetry run python src/ingestion/run_pipeline.py --months 10
# Result: Oct data REPLACED (previous runs lost if you had Nov too)
```

### Incremental Loading

**Definition**: Only process new/changed data, not everything from scratch.

**Good Example** (Incremental):
```bash
# Run 1: Load Oct-Nov data
$ poetry run python src/ingestion/run_pipeline.py --months 10,11
# Processes: 10M trips

# Run 2: Add December data
$ poetry run python src/ingestion/run_pipeline.py --months 12
# Processes: Only 5M new December trips
# Total: 15M trips (Oct + Nov + Dec)
```

**Bad Example** (Current State - NOT Incremental):
```bash
# Run 1: Load Oct-Nov
$ poetry run python src/ingestion/run_pipeline.py --months 10,11
# Processes: 10M trips

# Run 2: Add December
$ poetry run python src/ingestion/run_pipeline.py --months 12
# Processes: 5M December trips
# Total: ONLY 5M trips (Oct-Nov DELETED!)
```

---

## Recommended Solutions

### Solution 1: Fix DLT Layer (Highest Priority)

**Change `write_disposition` from "replace" to "merge"**

**Before** (`src/ingestion/sources/taxi.py`):
```python
@dlt.resource(name="yellow_taxi", write_disposition="replace")
def yellow_taxi() -> Iterator:
    ...
```

**After**:
```python
@dlt.resource(
    name="yellow_taxi",
    write_disposition="merge",
    primary_key=["tpep_pickup_datetime", "tpep_dropoff_datetime", "vendor_id", "pu_location_id"]
)
def yellow_taxi() -> Iterator:
    ...
```

**What this does**:
- `merge`: Upsert behavior (INSERT new, UPDATE existing based on primary key)
- `primary_key`: Deduplication key (same as dbt staging models)
- **Result**: Running twice with same month = idempotent (no duplicates)

**Apply to**:
- ✅ `yellow_taxi`: Primary key on pickup/dropoff times + vendor + location
- ✅ `fhv_taxi`: Primary key on pickup/dropoff times + base number
- ✅ `citibike_trips`: Primary key on `ride_id`
- ✅ `hourly_weather`: Primary key on `timestamp`

---

### Solution 2: Convert dbt Staging to Incremental (Optional)

**Current**: Views (recomputed every time)
**Proposed**: Incremental tables (only process new data)

**Before** (`dbt/models/staging/tlc/stg_tlc__yellow_taxi.sql`):
```sql
{{
    config(
        materialized='view',
        tags=['bronze', 'staging', 'tlc']
    )
}}
```

**After**:
```sql
{{
    config(
        materialized='incremental',
        unique_key='trip_id',
        on_schema_change='sync_all_columns',
        tags=['bronze', 'staging', 'tlc']
    )
}}

with source as (
    select * from {{ source('tlc', 'yellow_taxi') }}

    {% if is_incremental() %}
    -- Only process new data
    where tpep_pickup_datetime > (select max(pickup_datetime) from {{ this }})
    {% endif %}
),
...
```

**Trade-offs**:
- ✅ **Pro**: Faster staging layer (only process new rows)
- ✅ **Pro**: Staging tables persist (downstream models run faster)
- ⚠️ **Con**: More complex (need to handle late-arriving data)
- ⚠️ **Con**: Staging models now have state

**Recommendation**: **Keep staging as views** for simplicity. The real performance gain is in incremental fact tables.

---

### Solution 3: Convert Fact Tables to Incremental (High Priority)

**Change `fct_trips` and `fct_hourly_mobility` to incremental**

**Before** (`dbt/models/marts/core/fct_trips.sql`):
```sql
{{
    config(
        materialized='table',
        tags=['silver', 'marts', 'fact']
    )
}}
```

**After**:
```sql
{{
    config(
        materialized='incremental',
        unique_key='trip_key',
        on_schema_change='sync_all_columns',
        tags=['silver', 'marts', 'fact']
    )
}}

with trips_unioned as (
    select * from {{ ref('int_trips__unioned') }}

    {% if is_incremental() %}
    -- Only process trips newer than what we already have
    where pickup_datetime > (select max(pickup_datetime) from {{ this }})
    {% endif %}
),
...
```

**What this does**:
- First run: Full refresh (loads all data)
- Subsequent runs: Only process new trips (based on `pickup_datetime`)
- **Result**: 12.5M trip initial load, then only process delta (e.g., 100K new trips)

**Performance Impact**:
- **Current**: 30 seconds to rebuild 12.5M trips every time
- **With Incremental**: 30 seconds first time, then <1 second for daily updates

---

### Solution 4: Add dbt Merge Strategy

For incremental models, use **merge strategy with delete+insert**:

```sql
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',  -- or 'merge' for proper upserts
        unique_key='trip_key',
        on_schema_change='sync_all_columns'
    )
}}
```

**Strategies**:
- `delete+insert`: Delete matching keys, insert new rows (faster, simpler)
- `merge`: True upsert (slower, handles updates)

**Recommendation**: Use `delete+insert` for trip data (immutable once loaded)

---

## Implementation Plan

### Phase 1: Fix DLT Layer (Critical)

**Priority**: 🔴 **CRITICAL** - Must do before production

**Tasks**:
1. Add `write_disposition="merge"` to all DLT resources
2. Add `primary_key` to all DLT resources
3. Test idempotency: Run same month twice, verify no duplicates
4. Test incremental: Load Oct, then Nov, verify both exist

**Files to Modify**:
- `src/ingestion/sources/taxi.py`
- `src/ingestion/sources/citibike.py`
- `src/ingestion/sources/weather.py`

**Estimated Time**: 1 hour

---

### Phase 2: Convert Fact Tables to Incremental (High Priority)

**Priority**: 🟡 **HIGH** - Needed for scale

**Tasks**:
1. Convert `fct_trips` to incremental with `unique_key='trip_key'`
2. Convert `fct_hourly_mobility` to incremental with `unique_key='hour_key'`
3. Add `{% if is_incremental() %}` logic to filter new data
4. Test: Full refresh, then add new month incrementally

**Files to Modify**:
- `dbt/models/marts/core/fct_trips.sql`
- `dbt/models/marts/core/fct_hourly_mobility.sql`

**Estimated Time**: 2 hours

---

### Phase 3: Add Dimension SCD Type 2 (Optional)

**Priority**: 🟢 **LOW** - Future enhancement

**Concept**: Track dimension changes over time (Slowly Changing Dimensions)

**Example**: If a taxi zone changes boroughs, keep historical record

**Skip for now**: Dimensions are static (zones don't change)

---

### Phase 4: Testing & Validation (Critical)

**Priority**: 🔴 **CRITICAL** - Verify everything works

**Test Scenarios**:

1. **Idempotency Test**:
   ```bash
   # Load October twice
   poetry run python src/ingestion/run_pipeline.py --months 10
   poetry run python src/ingestion/run_pipeline.py --months 10

   # Verify: No duplicates, count unchanged
   poetry run dbt test --select fct_trips
   ```

2. **Incremental Test**:
   ```bash
   # Load October
   poetry run python src/ingestion/run_pipeline.py --months 10
   cd dbt && poetry run dbt run

   # Load November
   poetry run python src/ingestion/run_pipeline.py --months 11
   cd dbt && poetry run dbt run  # Should be fast

   # Verify: Both months exist
   ```

3. **Backfill Test**:
   ```bash
   # Load Oct-Nov
   poetry run python src/ingestion/run_pipeline.py --months 10,11
   cd dbt && poetry run dbt run

   # Later, backfill September
   poetry run python src/ingestion/run_pipeline.py --months 9
   cd dbt && poetry run dbt run --full-refresh  # Full refresh once

   # Verify: All three months exist
   ```

4. **Late Data Test**:
   ```bash
   # Load October
   poetry run python src/ingestion/run_pipeline.py --months 10
   cd dbt && poetry run dbt run

   # Re-run October (simulate late-arriving data)
   poetry run python src/ingestion/run_pipeline.py --months 10
   cd dbt && poetry run dbt run

   # Verify: October data updated, no duplicates
   ```

**Estimated Time**: 3 hours

---

## Comparison: Before vs After

### Before (Current State)

| Scenario | Behavior | Issue |
|----------|----------|-------|
| Run months 10,11 twice | Oct-Nov **replaced** | ❌ Not idempotent |
| Run month 10, then 11 | Only Nov exists | ❌ Oct deleted |
| Run month 10, then 10 again | Oct data **replaced** | ❌ Not idempotent |
| dbt run with 12.5M trips | 30 seconds every time | ❌ Inefficient |
| Add new month | Must reprocess all | ❌ Not incremental |

### After (Fixed)

| Scenario | Behavior | Result |
|----------|----------|--------|
| Run months 10,11 twice | Oct-Nov **unchanged** | ✅ Idempotent |
| Run month 10, then 11 | Both Oct and Nov exist | ✅ Incremental |
| Run month 10, then 10 again | Oct data **unchanged** | ✅ Idempotent |
| dbt run with 12.5M trips | 30s first, <1s incremental | ✅ Efficient |
| Add new month | Only process new month | ✅ Incremental |

---

## Production Readiness Checklist

Before deploying to production (MVP 3), verify:

- [ ] **DLT resources use `write_disposition="merge"`**
- [ ] **DLT resources have `primary_key` defined**
- [ ] **Fact tables use `materialized='incremental'`**
- [ ] **Idempotency tested** (run twice, no duplicates)
- [ ] **Incremental loading tested** (add new month, old data preserved)
- [ ] **Backfill tested** (add historical month)
- [ ] **Late-arriving data tested** (rerun same month, updates applied)
- [ ] **dbt tests passing** (108 tests)
- [ ] **Great Expectations passing** (56 validations)
- [ ] **Dagster schedule tested** (daily runs don't duplicate data)

---

## Next Steps

1. **Review this analysis** with stakeholders
2. **Prioritize Phase 1** (Fix DLT layer) - CRITICAL
3. **Implement Phase 2** (Incremental fact tables) - HIGH
4. **Run Phase 4 tests** (Validate everything) - CRITICAL
5. **Update documentation** (README, runbooks)
6. **Deploy to production** (MVP 3) only after all checkboxes complete

---

## References

- [dbt Incremental Models](https://docs.getdbt.com/docs/build/incremental-models)
- [dbt Incremental Strategies](https://docs.getdbt.com/docs/build/incremental-strategy)
- [DLT Write Dispositions](https://dlthub.com/docs/general-usage/incremental-loading#write-dispositions)
- [DLT Primary Keys](https://dlthub.com/docs/general-usage/resource#primary-key)
- [Kimball Slowly Changing Dimensions](https://en.wikipedia.org/wiki/Slowly_changing_dimension)

---

**Status**: 📋 Analysis complete, implementation pending
**Next**: Implement Phase 1 (Fix DLT layer)
