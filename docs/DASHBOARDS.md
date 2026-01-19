# NYC Mobility Dashboards

This project includes two Streamlit dashboards for different use cases.

---

## 1. Analytics Dashboard (`dashboard.py`)

**Purpose:** Business intelligence and exploratory data analysis

**Target Users:** Analysts, data scientists, business stakeholders

### Features
- **Key Metrics**: Total trips, average fare, distance, duration
- **Daily Trends**: Time series of trip volumes
- **Hourly Patterns**: Peak hours and usage patterns
- **Weather Impact**: Trip volume vs temperature, precipitation
- **Mode Comparison**: Yellow taxi vs FHV vs CitiBike
- **Time Patterns**: Weekend vs weekday, day parts

### Launch
```bash
poetry run streamlit run dashboard.py
```

Opens at: http://localhost:8501

### Screenshots
- Interactive date range filtering
- Trip type filtering (all, yellow taxi, FHV, CitiBike)
- Plotly charts with zoom and hover details
- Real-time query performance (<3 seconds)

---

## 2. Data Quality Dashboard (`dashboard_data_quality.py`)

**Purpose:** Data completeness monitoring and backfill validation

**Target Users:** Data engineers, analytics engineers, pipeline operators

### Features

#### 📈 Overview Metrics
- Total trips across all modes
- Date range coverage (earliest to latest)
- Day coverage percentage
- Weather coverage (target: 99.99%)
- Number of months loaded

#### 📅 Monthly Data Completeness
- **Stacked bar chart**: Trip volume by month and type
- **Detailed table**: Days in month, avg trips/day, weather coverage
- **Status indicators**:
  - ✅ Complete: >100k trips, good weather coverage
  - ⚠️ Low Volume: <100k trips (possible backfill issue)
  - ⚠️ Weather Issues: <99% weather coverage
  - ℹ️ Partial Month: <28 days of data

#### 📊 Daily Coverage Heatmap
- Calendar-style heatmap for each month
- Color intensity shows trip volume
- Switch between metrics:
  - Total trips
  - Yellow taxi trips
  - FHV trips
  - CitiBike trips
  - Trips with weather data

#### 🔍 Data Gap Detection
- Automatically detects missing dates
- Groups consecutive gaps
- Highlights gaps >3 days (likely backfill failures)
- Provides backfill command suggestions

#### ✅ Data Quality Metrics
- **Weather Coverage by Month**: Bar chart showing coverage %
- **Trip Type Distribution**: Pie chart of mode share
- **Quality Checks Summary**:
  - Low-volume days (<10k trips)
  - Missing weather data
  - Date gap count

#### 💡 Backfill Recommendations
- Intelligent detection of issues:
  - Months with <100k trips
  - Months with <30% of average volume
  - Weather coverage below 99%
- Severity levels (high/medium/low)
- Copy-paste backfill commands
- Actionable next steps

### Launch
```bash
poetry run streamlit run dashboard_data_quality.py
```

Opens at: http://localhost:8502

### Use Cases

#### Use Case 1: Verify Backfill Success
```bash
# Run backfill
poetry run dagster job launch backfill_monthly_data --config '{...}'

# Check dashboard
poetry run streamlit run dashboard_data_quality.py

# Look for:
# - Month appears in monthly breakdown
# - Trip count >100k
# - Weather coverage >99.99%
# - No date gaps
# - Status: ✅ Complete
```

#### Use Case 2: Identify Missing Months
1. Open dashboard
2. Check "Monthly Data Completeness" section
3. Look for:
   - Gaps in month sequence (e.g., June, July, September - missing August)
   - Low trip counts
   - ⚠️ warning indicators
4. Follow backfill recommendations at bottom

#### Use Case 3: Monitor Data Quality
1. Open dashboard
2. Navigate to "Data Quality Metrics"
3. Check:
   - Weather coverage by month (all should be green >99.99%)
   - Trip type distribution (stable proportions month-to-month)
   - Quality checks summary (all green ✅)

#### Use Case 4: Debug Pipeline Issues
1. Pipeline runs but no data appears
2. Open data quality dashboard
3. Check:
   - "Data Gap Detection" - are dates missing?
   - "Monthly Breakdown" - is the month showing 0 trips?
   - "Backfill Recommendations" - does it suggest full refresh?
4. Follow suggested backfill command

---

## Comparison Table

| Feature | Analytics Dashboard | Data Quality Dashboard |
|---------|---------------------|------------------------|
| **Purpose** | Business insights | Data operations |
| **Users** | Analysts, stakeholders | Engineers, operators |
| **Update Frequency** | Refreshes on demand | Auto-refresh every 5 min |
| **Focus** | Trip patterns, weather impact | Coverage, completeness, gaps |
| **Metrics** | 50 business metrics | 10 data quality metrics |
| **Visualizations** | Time series, scatter, heatmap | Bar, heatmap, pie, status |
| **Alerts** | None | ⚠️ Warnings for issues |
| **Actions** | Filter, explore | Backfill commands |

---

## Running Both Dashboards

You can run both dashboards simultaneously:

```bash
# Terminal 1: Analytics dashboard
poetry run streamlit run dashboard.py

# Terminal 2: Data quality dashboard
poetry run streamlit run dashboard_data_quality.py --server.port 8502
```

- Analytics: http://localhost:8501
- Data Quality: http://localhost:8502

---

## Dashboard Architecture

```
┌─────────────────────────────────────┐
│     data/nyc_mobility.duckdb        │
│         (Read-Only)                 │
└─────────────┬───────────────────────┘
              │
              ├─────────────────────────────┐
              │                             │
    ┌─────────▼──────────┐      ┌──────────▼─────────┐
    │  dashboard.py      │      │ dashboard_data_    │
    │  (Analytics)       │      │ quality.py         │
    │                    │      │ (Operations)       │
    │  - Plotly charts   │      │  - Status checks   │
    │  - Date filters    │      │  - Gap detection   │
    │  - Mode filters    │      │  - Recommendations │
    └────────────────────┘      └────────────────────┘
```

Both dashboards:
- Read from same DuckDB database
- Use `@st.cache_data` for performance
- Support concurrent access (read-only)
- Auto-refresh data on button click

---

## Performance

### Analytics Dashboard
- Initial load: <2 seconds
- Query execution: <1 second
- Chart rendering: <1 second
- Cache TTL: 600 seconds (10 minutes)

### Data Quality Dashboard
- Initial load: <3 seconds
- Query execution: <2 seconds
- Chart rendering: <1 second
- Cache TTL: 300 seconds (5 minutes)

### Optimization Tips
1. **Filter date ranges**: Reduces data scanned
2. **Use cache**: Don't click refresh unnecessarily
3. **Close unused dashboards**: Frees memory
4. **Run during off-hours**: Less database contention

---

## Troubleshooting

### Issue: Dashboard won't start
```bash
# Check if port is already in use
lsof -ti:8501  # Analytics dashboard
lsof -ti:8502  # Data quality dashboard

# Kill existing process
kill -9 $(lsof -ti:8501)
```

### Issue: "Database locked" error
- Both dashboards use read-only connections
- If you see this, check for write operations:
  ```bash
  # Check for running dbt jobs
  ps aux | grep dbt

  # Check for running DLT ingestion
  ps aux | grep dlt
  ```

### Issue: Stale data
- Click "🔄 Refresh Data" button
- Or restart dashboard to clear all caches

### Issue: Charts not loading
- Check browser console for errors
- Try a different browser (Chrome recommended)
- Clear browser cache

---

## Future Enhancements

### Analytics Dashboard
- [ ] Export to CSV/Excel
- [ ] Saved views/bookmarks
- [ ] Custom metric builder
- [ ] Email reports
- [ ] Mobile responsive layout

### Data Quality Dashboard
- [ ] Automated alerts (email/Slack)
- [ ] Historical quality trends
- [ ] SLA monitoring (freshness, completeness)
- [ ] Anomaly detection (ML-based)
- [ ] Integration with dbt test results
- [ ] Real-time pipeline status

---

## Contributing

To add features to dashboards:

1. **Edit Python file**: `dashboard.py` or `dashboard_data_quality.py`
2. **Test locally**: Run streamlit and verify changes
3. **Update this doc**: Document new features
4. **Submit PR**: Include screenshots

---

## Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Python](https://plotly.com/python/)
- [DuckDB Python API](https://duckdb.org/docs/api/python)
- [Project README](../README.md)
- [Backfill Guide](../orchestration/README.md#backfilling-historical-data)
