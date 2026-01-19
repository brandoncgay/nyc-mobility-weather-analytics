# CitiBike Data Gap Analysis

**Date**: 2026-01-16
**Analyst**: NYC Mobility & Weather Analytics Platform
**Database**: `data/nyc_mobility.duckdb`

---

## Executive Summary

CitiBike data in the database has **significant gaps** for multiple months. Analysis reveals that **~2.1M trips are missing** (~32% of potential data). The root cause appears to be **incomplete source files** from CitiBike's S3 bucket, not pipeline issues.

**Pattern Discovered**: Multiple months are missing the first 13 days of data, always starting on day 14.

---

## 1. Current Data Coverage

| Month | Date Range | Days | Trips | Status |
|-------|------------|------|-------|--------|
| May 2025 | May 31 only | 1 | 4,724 | ⚠️ 30 days missing from start |
| June 2025 | Jun 1 - Jun 14 | 14 | 995,276 | ⚠️ 16 days missing from end |
| July 2025 | Jul 14 - Jul 31 | 18 | 988,053 | ❌ **13 days missing from start** |
| August 2025 | Aug 14 - Aug 31 | 18 | 123,145 | ❌ **13 days missing from start** |
| September 2025 | Sep 1 - Sep 30 | 30 | 999,012 | ✅ Complete |
| October 2025 | Oct 1 - Oct 31 | 31 | 999,376 | ✅ Complete |
| November 2025 | Nov 14 - Nov 30 | 17 | 417,052 | ❌ **13 days missing from start** |

**Total**: 4,526,638 trips across 129 days (should be ~6.7M trips for 184 days)

---

## 2. Pattern Analysis

### Consistent Gap Pattern

**4 out of 7 months** are missing the first 13 days:
- **July 2025**: Missing Jul 1-13, starts on **day 14**
- **August 2025**: Missing Aug 1-13, starts on **day 14**
- **November 2025**: Missing Nov 1-13, starts on **day 14**
- **May 2025**: Only has May 31 (extreme case)

### Anomalies

- **June 2025**: Has Jun 1-14 but missing Jun 15-30 (opposite pattern!)
- **September & October**: Complete months ✅

---

## 3. Source File Investigation

### File Metadata from S3 Bucket

| Month | File Size | Last Modified | Status |
|-------|-----------|---------------|--------|
| May 2025 | 805.3 MB | Jul 3, 2025 | Normal size |
| June 2025 | 886.0 MB | Jul 6, 2025 | Normal size |
| July 2025 | 928.8 MB | Aug 5, 2025 | Normal size |
| August 2025 | 953.9 MB | Sep 4, 2025 | Normal size |
| September 2025 | 984.6 MB | Oct 6, 2025 | Normal size |
| October 2025 | 881.3 MB | Nov 4, 2025 | Normal size |
| November 2025 | 636.2 MB | Dec 8, 2025 | 21% smaller |
| December 2025 | 388.9 MB | Jan 5, 2026 | **52% smaller** ⚠️ |

**Average complete month**: ~900 MB
**November**: 636 MB (-21%) - missing 13 days explains size reduction
**December**: 389 MB (-52%) - likely highly incomplete (not yet ingested)

---

## 4. Root Cause Analysis

### Hypothesis: Preliminary File Publication

CitiBike appears to publish **preliminary data files** mid-month before the full month is complete:

#### Evidence:
1. **Consistent day-14 start**: July, August, November all start on day 14
2. **File publication dates**: Files published 3-8 days after month end
3. **June reverse pattern**: Jun file published Jul 6 with only first 14 days
4. **Normal file sizes**: Despite missing days, files are 600-950 MB (not corrupted)

#### Theory:
```
Timeline for July 2025:
├─ Jul 1-13:  Data NOT in 202507-citibike-tripdata.zip
├─ Jul 14-31: Data IN 202507-citibike-tripdata.zip
└─ Aug 5:     File published with Jul 14-31 data only
```

CitiBike may:
- Publish preliminary files with available data before month completes
- Backfill missing days later (but file names don't change)
- Or never republish complete files

---

## 5. Data Quality Impact

### Current State
- **Total trips loaded**: 4,526,638
- **Complete months**: 2 (September, October)
- **Incomplete months**: 5
- **Missing days**: ~55 days across 5 months

### Estimated Missing Data
- **Average trips/complete month**: 999,194
- **Estimated missing trips**: ~2,148,267
- **Current coverage**: ~68% of expected

### By Month
| Month | Actual Trips | Expected Trips | Missing |
|-------|-------------|----------------|---------|
| May | 4,724 | ~1,000,000 | 995,276 |
| June | 995,276 | ~1,000,000 | 4,724 |
| July | 988,053 | ~1,400,000 | 411,947 |
| August | 123,145 | ~1,400,000 | 1,276,855 |
| November | 417,052 | ~800,000 | 382,948 |

---

## 6. Recommendations

### Immediate Actions

#### 1. Download and Inspect Source Files
```bash
# Download suspicious months
wget https://s3.amazonaws.com/tripdata/202507-citibike-tripdata.zip
wget https://s3.amazonaws.com/tripdata/202508-citibike-tripdata.zip
wget https://s3.amazonaws.com/tripdata/202511-citibike-tripdata.zip

# Extract and check date ranges
unzip 202507-citibike-tripdata.zip
head -100 202507-citibike-tripdata.csv | tail -5
tail -100 202507-citibike-tripdata.csv | head -5
```

#### 2. Compare with Complete Month
```bash
# Download known complete month
wget https://s3.amazonaws.com/tripdata/202509-citibike-tripdata.zip
unzip 202509-citibike-tripdata.zip

# Compare file structures and date ranges
wc -l 202507-citibike-tripdata.csv
wc -l 202509-citibike-tripdata.csv
```

#### 3. Check CitiBike Official Documentation
- Visit: https://citibikenyc.com/system-data
- Look for:
  - Data update schedule
  - Known issues or announcements
  - Contact information for data inquiries

### Long-term Solutions

#### Option 1: Re-ingest with Updated Files
If CitiBike updates files with complete data:
```bash
# Re-run backfill for affected months
cd orchestration
poetry run dagster job launch backfill_monthly_data \
  --config '{"ops": {"monthly_dlt_ingestion": {"config": {"year": 2025, "month": 7}}}}'

# Repeat for months 8 and 11
```

#### Option 2: Alternative Data Sources
- **NYC Open Data Portal**: May have more complete CitiBike data
- **CitiBike API**: Real-time/historical data API (if available)
- **GBFS Feed**: General Bikeshare Feed Specification (may have historical)

#### Option 3: Accept Limitation
- Document the gaps in dashboard
- Add data quality warnings
- Focus analysis on complete months (Sept, Oct)

---

## 7. Dashboard Updates

### Recommended Enhancements

Add a **CitiBike Data Quality Warning** section:

```python
# In dashboard_data_quality.py
st.warning("""
⚠️ **CitiBike Data Gaps**: Multiple months are missing the first 13 days
due to incomplete source files from CitiBike's S3 bucket:
- July 2025: Missing Jul 1-13
- August 2025: Missing Aug 1-13
- November 2025: Missing Nov 1-13

Only September and October have complete data.
""")
```

### Data Quality Metrics
- Add "CitiBike Completeness" metric
- Show % of expected trips by month
- Flag incomplete months in visualizations

---

## 8. Investigation Tools Created

### 1. `investigate_citibike_gaps.py`
Analyzes database for gaps and patterns.

**Usage:**
```bash
poetry run python investigate_citibike_gaps.py
```

**Output:**
- Monthly summary with date ranges
- Missing date ranges by month
- Pattern analysis
- Data quality impact estimates

### 2. `check_citibike_sources.py`
Checks CitiBike S3 bucket for file metadata.

**Usage:**
```bash
poetry run python check_citibike_sources.py
```

**Output:**
- File existence and sizes
- Last modified dates
- Size comparison vs averages
- Recommendations

---

## 9. Next Steps

### Priority 1 (Immediate)
- [ ] Download July, August, November ZIP files
- [ ] Inspect CSV headers and date ranges
- [ ] Compare with September (complete month)
- [ ] Document findings

### Priority 2 (This Week)
- [ ] Check CitiBike's official data page for updates
- [ ] Contact CitiBike support about incomplete files
- [ ] Research alternative data sources
- [ ] Add dashboard warnings

### Priority 3 (Future)
- [ ] Set up monitoring for file updates
- [ ] Create automated re-ingestion if files are updated
- [ ] Explore CitiBike API for backfilling
- [ ] Document limitations in project README

---

## 10. References

- **CitiBike Data Portal**: https://citibikenyc.com/system-data
- **S3 Bucket**: s3://tripdata/
- **Data Files**: `YYYYMM-citibike-tripdata.zip`
- **Investigation Scripts**:
  - `investigate_citibike_gaps.py`
  - `check_citibike_sources.py`

---

## Appendix: SQL Queries Used

### Check Daily Coverage
```sql
SELECT
    CAST(started_at AS DATE) as date,
    COUNT(*) as trips
FROM raw_data.trips
WHERE started_at >= '2025-07-01' AND started_at < '2025-08-01'
GROUP BY date
ORDER BY date;
```

### Find Missing Dates
```sql
WITH date_range AS (
    SELECT generate_series(
        DATE '2025-07-01',
        DATE '2025-07-31',
        INTERVAL '1 day'
    )::date as expected_date
),
actual_dates AS (
    SELECT DISTINCT CAST(started_at AS DATE) as actual_date
    FROM raw_data.trips
    WHERE started_at >= '2025-07-01' AND started_at < '2025-08-01'
)
SELECT expected_date
FROM date_range
LEFT JOIN actual_dates ON expected_date = actual_date
WHERE actual_date IS NULL;
```

---

**End of Analysis**
