# NYC Mobility & Weather Analytics Dashboard

Interactive Streamlit dashboard for visualizing 12.5M trips across NYC transportation modes with weather correlations.

**100% Open Source** | Built with Streamlit (Apache 2.0) + Plotly (MIT) + DuckDB (MIT)

## Features

### Key Metrics
- **Total Trips** - Trip volume for selected period
- **Avg Duration** - Average trip duration in minutes
- **Avg Distance** - Average trip distance in miles
- **Avg Fare** - Average fare amount (taxi/FHV)
- **Total Revenue** - Total revenue generated
- **Avg Speed** - Average trip speed in mph

### Interactive Filters
- **Date Range** - Select custom date range (Sept-Nov 2025)
- **Transportation Mode** - Filter by Yellow Taxi, FHV, CitiBike, or All
- **Weather Condition** - Filter by Pleasant, Adverse, Rainy, Snowy, or All

### 4 Analysis Tabs

#### 1. Overview
- Daily trip volume time series
- Mode share pie chart
- Hourly distribution

#### 2. Weather Impact
- Trips by weather description
- Temperature vs trip volume correlation
- Precipitation impact on trips/duration/speed
- Pleasant vs Adverse weather comparison

#### 3. Location Analysis
- Top 15 pickup locations by zone
- Top 15 dropoff locations by zone
- Borough distribution with statistics

#### 4. Time Patterns
- Day of week patterns (weekday vs weekend)
- Rush hour vs non-rush hour comparison
- Day part distribution (morning/afternoon/evening/night)
- **Trip heatmap** - Hour x Day of Week

## Quick Start

### Run the Dashboard

```bash
# From project root
poetry run streamlit run dashboard.py
```

The dashboard will automatically:
- Connect to `data/nyc_mobility.duckdb` (read-only)
- Load date range from your data
- Cache queries for fast performance
- Open in your default browser at http://localhost:8501

### ⚠️ Important: DuckDB Concurrency Limitation

**You cannot run the dashboard and data ingestion at the same time.**

DuckDB allows only one write connection. If you're loading data via Dagster or DLT, stop the dashboard first:

```bash
# Press Ctrl+C in the dashboard terminal
# Or kill the process:
pkill -f "streamlit run dashboard.py"
```

After data loading completes, you can restart the dashboard to see the new data.

### First Time Setup

If you haven't installed Streamlit yet:

```bash
# Streamlit and Plotly are already in pyproject.toml
poetry install
```

## Usage

### Basic Navigation

1. **Sidebar Filters** - Adjust filters in left sidebar
2. **Tab Navigation** - Click tabs to switch between analyses
3. **Interactive Charts** - Hover for details, click legend to toggle series
4. **Download Data** - Use Plotly's built-in export (camera icon)

### Example Workflows

#### Analyze Weather Impact on CitiBike
1. Set **Mode** filter to "CitiBike"
2. Go to **Weather Impact** tab
3. Compare Pleasant vs Adverse weather trip counts
4. Check temperature correlation

#### Find Rush Hour Patterns by Mode
1. Set **Mode** filter to specific mode
2. Go to **Time Patterns** tab
3. View rush hour comparison
4. Check heatmap for peak hours

#### Compare Boroughs
1. Set filters to desired period
2. Go to **Location Analysis** tab
3. View borough distribution table and chart
4. Compare pickup vs dropoff patterns

## Technical Details

### Data Model
- **Fact Table**: `core_core.fct_trips` (12.5M records)
- **Dimensions**: `dim_location`, `dim_date`, `dim_time`, `dim_weather`
- **Join Pattern**: Star schema with foreign keys

### Query Performance
- **Caching**: 10-minute TTL on all queries
- **Read-Only**: No database locks
- **Connection Pooling**: Single cached connection
- **Lazy Loading**: Queries execute only when tab is viewed

### Column Mappings
Dashboard uses these actual column names:
- `trip_distance` (miles)
- `revenue` (dollars, for taxi/FHV)
- `temperature_fahrenheit` (°F)
- `precipitation` (mm)
- `snowfall` (cm)
- `weather_description` (text)
- `is_pleasant_weather` / `is_adverse_weather` (boolean flags)

## Customization

### Modify Charts

Edit `dashboard.py` to customize:
- **Colors**: Update `color_discrete_map` dictionaries
- **Chart Types**: Swap `px.bar` for `px.scatter`, `px.line`, etc.
- **Filters**: Add new filter options in sidebar section
- **Metrics**: Add new metric cards in Key Metrics section

### Add New Tabs

```python
# In dashboard.py, add a new tab
tab5 = st.tabs(["📊 Overview", "🌤️ Weather", "📍 Location", "⏰ Time", "🆕 Custom"])

with tab5:
    st.header("My Custom Analysis")
    # Your queries and visualizations here
```

### Change Query Logic

All queries use f-strings with `where_clause` variable:
```python
query = f"""
    SELECT COUNT(*) as trips
    FROM core_core.fct_trips
    WHERE {where_clause}  -- Includes filters
"""
```

## Troubleshooting

### Dashboard Won't Start

**Error**: `ModuleNotFoundError: No module named 'streamlit'`

**Solution**:
```bash
poetry install
poetry run streamlit run dashboard.py
```

### Database Locked Error

**Error**: `duckdb.IOException: database is locked`

**Solution**: Close any other DuckDB connections:
```bash
# Kill DuckDB processes
pkill -f duckdb

# Or check what's using the database
lsof data/nyc_mobility.duckdb
```

### Slow Performance

**Solutions**:
1. Reduce date range in filters
2. Clear Streamlit cache: Press `C` in browser, then "Clear cache"
3. Restart dashboard: `Ctrl+C` then rerun

### Charts Not Showing

**Issue**: Empty DataFrames from queries

**Check**:
1. Verify filters aren't too restrictive
2. Ensure data exists for selected date range
3. Check browser console for JavaScript errors

## Export & Sharing

### Export Visualizations

**Option 1: Screenshot**
- Use Plotly's camera icon on each chart
- Saves as PNG with transparent background

**Option 2: HTML Report**
```bash
# Export notebook as HTML (if using Jupyter)
poetry run jupyter nbconvert --to html notebooks/your_analysis.ipynb
```

### Share Dashboard

**Option 1: Local Network**
```bash
# Run on all network interfaces
poetry run streamlit run dashboard.py --server.address=0.0.0.0
# Access from other devices: http://YOUR_IP:8501
```

**Option 2: Streamlit Cloud (Free Hosting)**
1. Push code to GitHub
2. Sign up at https://share.streamlit.io
3. Connect repository
4. Deploy (note: requires public DuckDB file or cloud database)

**Option 3: Docker**
```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install poetry && poetry install
CMD ["poetry", "run", "streamlit", "run", "dashboard.py"]
```

## Data Sources

- **NYC TLC Trip Records** (Yellow Taxi, FHV)
- **CitiBike System Data**
- **Open-Meteo Weather API**

**Pipeline**: DLT → DuckDB → dbt → Dagster → Dashboard

**Data Quality**: 99.9996% weather join coverage

## Architecture

```
dashboard.py
    ↓
DuckDB (read-only connection)
    ↓
core_core.fct_trips (12.5M records)
core_core.dim_location (263 zones)
core_core.dim_weather (1,464 hours)
    ↓
Streamlit Cache (10-min TTL)
    ↓
Plotly Visualizations
```

## Performance Tips

1. **Start with smaller date ranges** - Test with 1 week, then expand
2. **Use filters** - Mode and weather filters reduce query size
3. **Cache is your friend** - Revisiting tabs uses cached data
4. **Close when not using** - Free up database connection

## Next Steps

After exploring locally, consider:
1. **Deploy to Streamlit Cloud** - Free public hosting
2. **Migrate to cloud database** - Snowflake for production scale
3. **Add ML predictions** - Trip demand forecasting
4. **Real-time updates** - Live data streaming

## License

**100% Open Source Stack**:
- Streamlit: Apache 2.0
- Plotly: MIT
- DuckDB: MIT
- Pandas: BSD-3-Clause

## Questions?

Refer to:
- [Main README](README.md) - Project overview
- [MVP 2 Summary](docs/MVP2_COMPLETION_SUMMARY.md) - Data model details
- [Streamlit Docs](https://docs.streamlit.io) - Framework documentation
- [Plotly Docs](https://plotly.com/python/) - Visualization examples

---

**Built for MVP 2.5** - Local visualization before cloud deployment (MVP 3)
