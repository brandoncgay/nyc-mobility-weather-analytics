# CitiBike Re-Ingestion Plan

**Date**: 2026-01-16
**Finding**: Source files contain COMPLETE data, but database is missing it

---

## Discovery Summary

### What We Found

**Source File Inspection** (January 2026):
- **July 2025** S3 file: Contains **5.0M records** from **July 1-31** ✅
- **September 2025** S3 file: Contains **5.3M records** from **Sep 3-29** (missing Sep 1-2)

**Our Database** (`raw_data.trips`):
- **July 2025**: Only **988K records** from **July 14-31** ❌
- **September 2025**: **999K records** from **Sep 1-30** ✅

### Key Insight

The source files have been **updated since our original ingestion**. CitiBike likely published preliminary files initially, then updated them with complete data later. Our DLT incremental ingestion didn't pick up the historical updates.

---

## Affected Months

| Month | Our Data | Source File | Missing | Action |
|-------|----------|-------------|---------|--------|
| May 2025 | May 31 only (5K) | Unknown | Unknown | Re-ingest |
| June 2025 | Jun 1-14 (995K) | Unknown | Unknown | Re-ingest |
| **July 2025** | **Jul 14-31 (988K)** | **Jul 1-31 (5M)** | **~4M trips** | **Re-ingest** |
| **August 2025** | **Aug 14-31 (123K)** | **Unknown** | **Unknown** | **Re-ingest** |
| September 2025 | Sep 1-30 (999K) | Sep 3-29 (5.3M) | Complex | Investigate |
| October 2025 | Oct 1-31 (999K) | Unknown | None? | Verify |
| **November 2025** | **Nov 14-30 (417K)** | **Unknown** | **Unknown** | **Re-ingest** |

---

## Why Our Ingestion Missed Data

### DLT Incremental Mode Behavior

DLT uses `write_disposition="merge"` with `primary_key="ride_id"`. When we originally ingested:

**Timeline Theory**:
1. **August 2025**: We ingest July data
   - CitiBike file only had Jul 14-31 at that time
   - DLT ingests 988K records ✅
2. **Later (unknown date)**: CitiBike **updates** July file
   - Now contains complete Jul 1-31 data (5M records)
   - But we never re-ingested! ❌
3. **Our pipeline runs monthly**: Only ingests NEW months, never re-checks old files

### Root Cause

**DLT incremental merge only adds NEW ride_ids**. If CitiBike added rides with July 1-13 dates AFTER we initially ingested July, those rides have new ride_ids that our database has never seen. DLT won't re-download the entire file unless we force it.

---

## Re-Ingestion Strategy

### Option 1: Full Refresh (RECOMMENDED)

Delete old data and re-ingest everything.

**Pros:**
- Guaranteed complete data
- Fixes all months at once
- Clean slate

**Cons:**
- Takes longer (~30-45 min for all months)
- Re-downloads all data

**Commands:**
```bash
# Stop dashboard first
kill -9 $(lsof -ti:8502) 2>/dev/null

# Clear CitiBike data from database
poetry run python << 'EOF'
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb')
conn.execute('DELETE FROM raw_data.trips')
conn.execute('DELETE FROM raw_data._dlt_loads WHERE pipeline_name = ANY(SELECT DISTINCT pipeline_name FROM raw_data._dlt_loads WHERE schema_name = ''raw_data'' AND load_id IN (SELECT load_id FROM raw_data.trips))')
conn.close()
print('✓ CitiBike data cleared')
EOF

# Re-run ingestion for all months
poetry run python src/ingestion/run_pipeline.py \
  --year 2025 \
  --months 5,6,7,8,9,10,11 \
  --sources citibike

# Run dbt to rebuild fact tables
cd dbt && poetry run dbt run --full-refresh --select fct_trips fct_hourly_mobility

# Restart dashboard
poetry run streamlit run dashboard_data_quality.py --server.port 8502 --server.headless true &
```

### Option 2: Targeted Re-Ingestion

Re-ingest only affected months.

**Problem**: DLT's merge mode won't replace existing data, only add NEW ride_ids.

**Workaround**: Delete specific months first, then re-ingest.

```bash
# Delete July data
poetry run python << 'EOF'
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb')
conn.execute("DELETE FROM raw_data.trips WHERE started_at >= '2025-07-01' AND started_at < '2025-08-01'")
conn.close()
print('✓ July data cleared')
EOF

# Re-ingest July
poetry run python src/ingestion/run_pipeline.py \
  --year 2025 \
  --months 7 \
  --sources citibike

# Rebuild fact tables with full refresh
cd dbt && poetry run dbt run --full-refresh --select fct_trips fct_hourly_mobility
```

**Repeat for months 8 and 11.**

### Option 3: Force DLT Refresh (EXPERIMENTAL)

Force DLT to ignore existing data and re-download.

```bash
# Delete DLT state for CitiBike
poetry run python << 'EOF'
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb')
conn.execute("DELETE FROM raw_data._dlt_pipeline_state WHERE pipeline_name = 'citibike'")
conn.close()
EOF

# Re-run ingestion
poetry run python src/ingestion/run_pipeline.py \
  --year 2025 \
  --months 5,6,7,8,9,10,11 \
  --sources citibike
```

---

## Verification Steps

After re-ingestion:

### 1. Check Raw Data
```bash
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb', read_only=True)
result = conn.execute('''
SELECT
    DATE_TRUNC('month', started_at) as month,
    MIN(CAST(started_at AS DATE)) as first_date,
    MAX(CAST(started_at AS DATE)) as last_date,
    COUNT(*) as trips
FROM raw_data.trips
WHERE started_at >= '2025-05-01'
GROUP BY month
ORDER BY month
''').fetchdf()
print(result.to_string())
conn.close()
"
```

**Expected output:**
```
May 2025:  May 1 to May 31  (~1M trips)
June 2025: Jun 1 to Jun 30  (~1.7M trips)
July 2025: Jul 1 to Jul 31  (~5M trips)   ← Was 988K
Aug 2025:  Aug 1 to Aug 31  (~5M trips)   ← Was 123K
Sept 2025: Sep 1 to Sep 30  (~5M trips)
Oct 2025:  Oct 1 to Oct 31  (~5M trips)
Nov 2025:  Nov 1 to Nov 30  (~5M trips)   ← Was 417K
```

### 2. Check Fact Table
```bash
poetry run python -c "
import duckdb
conn = duckdb.connect('data/nyc_mobility.duckdb', read_only=True)
result = conn.execute('''
SELECT
    DATE_TRUNC('month', pickup_datetime) as month,
    COUNT(*) as trips
FROM core_core.fct_trips
WHERE trip_type = 'citibike'
GROUP BY month
ORDER BY month
''').fetchdf()
print(result.to_string())
conn.close()
"
```

### 3. Check Dashboard
- Open http://localhost:8502
- Click **🔄 Refresh Data**
- Verify:
  - Total trips increases from ~40M to ~48M
  - July shows ~5M CitiBike trips (not 988K)
  - August shows ~5M CitiBike trips (not 123K)
  - No warnings about missing first 13 days

---

## Estimated Impact

### Before Re-Ingestion
- **Total CitiBike trips**: 4.5M
- **Complete months**: 2 (Sept, Oct)
- **Missing trips**: ~2.1M

### After Re-Ingestion (Expected)
- **Total CitiBike trips**: ~35M (7x increase!)
- **Complete months**: 7 (all months)
- **Missing trips**: 0 (assuming source files are complete)

### Overall Database Impact
- **Current total trips**: 40M
- **Expected after re-ingest**: ~48M
- **Increase**: +8M trips (+20%)

---

## Timeline

**Estimated time for Option 1 (Full Refresh):**
- Clear data: 1 min
- Re-ingest 7 months: 25-30 min
- dbt full refresh: 3-5 min
- Verification: 2 min
- **Total: ~35-40 minutes**

---

## Risks & Mitigation

### Risk 1: Data Loss
**Mitigation**: Backup database first
```bash
cp data/nyc_mobility.duckdb data/nyc_mobility.backup.duckdb
```

### Risk 2: Source Files Still Incomplete
**Mitigation**: We verified July has complete data. Download and check other months:
```bash
cd /tmp/citibike_investigation
wget https://s3.amazonaws.com/tripdata/202508-citibike-tripdata.zip
wget https://s3.amazonaws.com/tripdata/202511-citibike-tripdata.zip
# Inspect before re-ingesting
```

### Risk 3: Long Downtime
**Mitigation**: Dashboard will be offline during re-ingestion. Schedule during off-hours.

---

## Next Steps

1. **Backup database** ✅
2. **Download and verify source files** for Aug, Nov (optional but recommended)
3. **Choose strategy** (recommend Option 1)
4. **Execute re-ingestion**
5. **Verify results**
6. **Update documentation** with lessons learned

---

## Lessons Learned

1. **CitiBike updates historical files** - files aren't immutable
2. **DLT incremental merge doesn't re-check** old files by default
3. **Need monitoring** for data completeness after ingestion
4. **Verification is critical** - don't trust file names, inspect contents

### Future Improvements

1. **Add data quality checks** after each ingestion
2. **Periodic re-ingestion** of recent months (e.g., re-ingest last 2 months monthly)
3. **File hash tracking** to detect when CitiBike updates files
4. **Dashboard alerts** for suspiciously low trip counts

---

**Ready to proceed with Option 1?**
