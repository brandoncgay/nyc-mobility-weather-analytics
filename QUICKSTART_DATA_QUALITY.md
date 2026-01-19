# Data Quality Dashboard - Quick Start Guide

**Launch in 30 seconds** ⚡

---

## Launch the Dashboard

```bash
poetry run streamlit run dashboard_data_quality.py
```

Opens at: **http://localhost:8502**

---

## What You'll See

### 1. Overview Metrics (Top)
```
┌─────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Total Trips │  Date Range  │ Day Coverage │   Weather    │   Months     │
│  32.5M      │  154 days    │  154 days    │  99.9999%    │   6 months   │
│             │  Jun - Nov   │  (100%)      │  ✅          │              │
└─────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

**What to look for:**
- ✅ Weather Coverage >99.99% (green) = Good
- ⚠️ Weather Coverage <99% (orange/red) = Backfill needed
- ✅ Day Coverage = 100% = No gaps
- ⚠️ Day Coverage <95% = Missing dates

---

### 2. Monthly Breakdown (Stacked Bar Chart)

Shows trip volume by month with color-coded trip types:
- 🟨 Yellow = Yellow Taxi
- 🟦 Blue = FHV
- 🟩 Green = CitiBike

**What to look for:**
- Each month should have >100k trips
- Consistent proportions across months
- No missing months in sequence

**Example Good Data:**
```
Jun ████ 16k      (partial month - OK)
Jul ████████████ 7M
Aug ████████████ 5.9M
Sep ████████████ 7.3M
Oct ████████████ 7.8M
Nov ████████████ 4.5M
```

**Example Bad Data (Backfill Needed):**
```
Jun ████ 16k
Jul ████████████ 7M
Aug ██ 50k       ⚠️ LOW VOLUME - Missing data!
Sep ████████████ 7.3M
```

---

### 3. Detailed Monthly Table (Click "View Detailed")

| Month | Total Trips | Days | Avg Trips/Day | Weather % | Status |
|-------|------------|------|---------------|-----------|--------|
| 2025-06 | 16,065 | 1 | 16,065 | 99.96% | ℹ️ Partial Month |
| 2025-07 | 6,998,077 | 31 | 225,744 | 100.00% | ✅ Complete |
| 2025-08 | 5,872,290 | 31 | 189,429 | 100.00% | ✅ Complete |

**Status meanings:**
- ✅ Complete = Good data, no action needed
- ⚠️ Low Volume = <100k trips, run backfill
- ⚠️ Weather Issues = <99% coverage, run full refresh
- ℹ️ Partial Month = Expected (first/last month)

---

### 4. Daily Coverage Heatmap (Calendar View)

Visual calendar showing trip volume by day:
- **Darker blue** = More trips
- **Light blue** = Fewer trips
- **White** = No data (gap!)

**Switch metrics** with radio buttons:
- Total trips
- Yellow taxi only
- FHV only
- CitiBike only
- Trips with weather

---

### 5. Data Gap Detection

**Good:**
```
✅ No date gaps detected! All days in the date range have data.
```

**Bad:**
```
⚠️ Found 3 day(s) with no data:
- 2025-05-15 to 2025-05-17: 3 consecutive days missing

🚨 Large gap detected (>3 days). This likely indicates a backfill issue.

Run:
poetry run dagster job launch backfill_monthly_data \
  --config '{"ops": {"monthly_dlt_ingestion": {"config": {"year": 2025, "month": 5}}}}'
```

---

### 6. Data Quality Metrics

**Weather Coverage by Month** (Bar chart)
- Green bars = >99.99% (excellent)
- Orange bars = 99-99.99% (good)
- Red bars = <99% (needs attention)

**Trip Type Distribution** (Pie chart)
- Shows mode share across all data
- Yellow Taxi typically 60-65%
- FHV typically 25-30%
- CitiBike typically 10-15%

**Quality Checks Summary**
```
✅ No low-volume days
✅ Weather coverage excellent (6 trips missing)
✅ No date gaps
```

---

### 7. Backfill Recommendations (Bottom)

**No Issues:**
```
✅ No backfill issues detected. Data looks complete!
```

**Issues Found:**
```
⚠️ Found 2 issue(s) requiring attention:

🚨 May 2025 has only 0 trips (expected >100k). Likely missing data.
   Action: Run backfill for 2025-05

⚠️ August 2025 has 45,231 trips (70% below average). Partial data?
   Action: Verify data completeness for 2025-08

[Show backfill command for May 2025]
```

Click "Show backfill command" for copy-paste command.

---

## Common Workflows

### Workflow 1: Check After Backfill
```bash
# 1. Run backfill
poetry run dagster job launch backfill_monthly_data --config '{...}'

# 2. Open dashboard
poetry run streamlit run dashboard_data_quality.py

# 3. Click "🔄 Refresh Data"

# 4. Verify:
#    - Month appears in bar chart
#    - Trip count >100k
#    - Status = ✅ Complete
#    - Weather coverage >99.99%
```

### Workflow 2: Find Missing Months
```bash
# 1. Open dashboard
poetry run streamlit run dashboard_data_quality.py

# 2. Look at Monthly Breakdown chart
#    - Is there a gap in the sequence?
#    - Example: Jun, Jul, Sep (missing Aug)

# 3. Scroll to "Backfill Recommendations"
#    - Copy backfill command

# 4. Run backfill
#    - Paste and execute command

# 5. Refresh dashboard to verify
```

### Workflow 3: Monitor Data Quality
```bash
# Run daily or after pipeline runs

# 1. Open dashboard
poetry run streamlit run dashboard_data_quality.py

# 2. Check Overview Metrics (top)
#    - All green? ✅ Good!
#    - Any orange/red? ⚠️ Investigate

# 3. Check Quality Checks Summary
#    - All ✅? Good!
#    - Any ⚠️? Follow recommendations

# 4. Review Backfill Recommendations
#    - Take action on any issues
```

---

## Interpreting Results

### Scenario 1: Fresh Deployment
```
Overview Metrics:
- Total Trips: 16,065
- Date Range: 1 day (Jun 30, 2025)
- Day Coverage: 1 day (100%)
- Weather: 99.96% ✅
- Months: 1

Monthly Breakdown: Only June showing

Action: ✅ Normal for fresh deployment. Start loading more months.
```

### Scenario 2: Successful Backfill
```
Before backfill:
- Months: Jun, Jul, Aug, Oct, Nov (Sep missing)
- Backfill Recommendations: Run backfill for 2025-09

After backfill:
- Months: Jun, Jul, Aug, Sep, Oct, Nov (complete sequence!)
- No recommendations
- Sep: 7.3M trips, ✅ Complete

Action: ✅ Success! Backfill worked.
```

### Scenario 3: Failed Backfill (Incremental Mode)
```
After backfill attempt:
- Monthly Breakdown: Sep still showing 0 trips
- Gap Detection: 30 days missing in September
- Recommendations: Run backfill for 2025-09

Why: Backfill ran in incremental mode, not full refresh

Action: Use backfill_monthly_data job (not monthly_ingestion_job)
```

### Scenario 4: Weather Coverage Issue
```
Overview Metrics:
- Weather: 66.15% ⚠️

Monthly Breakdown:
- Sep: 0% weather coverage ⚠️

Recommendations:
- Run dbt full-refresh

Action: cd dbt && poetry run dbt run --full-refresh --select fct_trips
```

---

## Quick Reference

### Dashboard Controls
- **🔄 Refresh Data**: Clears cache, reloads all data (5 min default)
- **Radio buttons**: Switch between metrics on heatmap
- **Expand buttons**: Show detailed tables and commands

### Color Codes
- **Green**: Good, no action needed
- **Orange**: Warning, investigate
- **Red**: Error, action required
- **Blue**: Information, context

### Key Thresholds
- Weather coverage: >99.99% (excellent), 99-99.99% (good), <99% (poor)
- Monthly trips: >100k (normal), <100k (investigate)
- Date gaps: 0 (perfect), 1-3 days (minor), >3 days (major issue)

---

## Troubleshooting

### Dashboard won't start
```bash
# Check if port 8502 is in use
lsof -ti:8502

# Kill existing process
kill -9 $(lsof -ti:8502)

# Restart
poetry run streamlit run dashboard_data_quality.py
```

### "No data found in fct_trips"
```bash
# Check if database exists
ls -lh data/nyc_mobility.duckdb

# Run dbt to build fct_trips
cd dbt && poetry run dbt run --select fct_trips

# Restart dashboard
```

### Data looks stale
```bash
# Click "🔄 Refresh Data" button in dashboard
# Or restart dashboard to clear all caches
```

---

## Next Steps

1. ✅ Launch dashboard: `poetry run streamlit run dashboard_data_quality.py`
2. ✅ Review current data state
3. ✅ Follow any backfill recommendations
4. ✅ Bookmark for regular monitoring

**Tip**: Run this dashboard after every backfill to verify success!

---

## Learn More

- **Full documentation**: [docs/DASHBOARDS.md](docs/DASHBOARDS.md)
- **Backfill guide**: [orchestration/README.md](orchestration/README.md#backfilling-historical-data)
- **Analytics dashboard**: `poetry run streamlit run dashboard.py`
