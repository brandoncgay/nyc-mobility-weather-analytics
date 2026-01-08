# Semantic Models & Metrics Notebook - Quick Reference

## What Was Created

**File:** `notebooks/03_semantic_models_and_metrics.ipynb`

**Purpose:** Educational notebook explaining the dbt MetricFlow semantic layer implementation

## Notebook Contents

### 1. Introduction to Semantic Layers
- What is a semantic layer?
- Why use one?
- Benefits: consistency, efficiency, discoverability, governance

### 2. Semantic Model Documentation

#### Model #1: `trips`
- **Grain:** Trip-level (12.5M records)
- **Entities:** trip, date, time, pickup_location, dropoff_location
- **26 Measures:** Including trip counts, duration, distance, speed, passengers, revenue, weather
- **20+ Dimensions:** Including trip_type, temporal attributes, locations, weather conditions

#### Model #2: `hourly_mobility`
- **Grain:** One row per hour per trip_type
- **Purpose:** Pre-aggregated time-series analysis
- **Measures:** Hourly trip counts, mode share percentages, rush hour metrics
- **Use case:** Performance-optimized hourly trends

### 3. Complete Metrics Catalog (45 Metrics)

**Core Trip Metrics (13):**
- total_trips, avg_trip_duration_minutes, median_trip_duration_minutes
- avg_trip_distance_miles, total_trip_distance_miles, avg_trip_speed_mph
- total_passengers, avg_passengers_per_trip
- total_revenue, avg_fare, revenue_per_mile

**Mode Share Metrics (13):**
- Individual mode trip counts (yellow_taxi, fhv, citibike)
- Mode share percentages (derived metrics)
- Mode-specific averages (fare, duration)
- Rush hour mode breakdowns

**Time Pattern Metrics (16):**
- rush_hour_trips, weekend_trips, weekday_trips
- late_night_trips, business_hours_trips
- Day part breakdowns (morning, afternoon, evening, night)
- Derived ratios (weekday/weekend, rush hour intensity)

**Weather Impact Metrics (13):**
- Adverse weather trip counts
- Precipitation-specific metrics (rain, snow)
- Temperature category metrics (cold, hot, mild)
- Weather-segmented duration averages

### 4. Metric Types Explained

**Simple Metrics:**
```yaml
- name: total_trips
  type: simple
  type_params:
    measure: trip_count
```

**Derived Metrics:**
```yaml
- name: yellow_taxi_mode_share_pct
  type: derived
  type_params:
    expr: yellow_taxi_trips / total_trips * 100
    metrics:
      - yellow_taxi_trips
      - total_trips
```

**Filtered Metrics:**
```yaml
- name: rush_hour_trips
  type: simple
  type_params:
    measure: trip_count
  filter: |
    {{ Dimension('trip__is_rush_hour') }} = true
```

### 5. How to Query Metrics

**MetricFlow CLI:**
```bash
# List metrics
poetry run mf list metrics

# Query single metric
poetry run mf query --metrics total_trips --group-by trip__trip_type

# Query with time dimension
poetry run mf query \
  --metrics total_trips,avg_trip_duration_minutes \
  --group-by metric_time__day \
  --where "trip__trip_type = 'yellow_taxi'"
```

**Direct SQL (used in notebook):**
```sql
-- Equivalent to total_trips metric
SELECT trip_type, COUNT(*) as total_trips
FROM core_core.fct_trips
GROUP BY trip_type
```

### 6. Example Analyses Included

1. **Core Trip Metrics** - Trip counts, duration, distance, speed by mode
2. **Mode Share** - Transportation mode percentages with visualization
3. **Time Patterns** - Rush hour vs non-rush, weekend vs weekday
4. **Weather Impact** - Trip behavior in rain, snow, adverse weather
5. **Rush Hour Mode Share** - Which modes dominate during rush hour
6. **Day Part Distribution** - Morning, afternoon, evening, night patterns
7. **Temperature Categories** - Trip behavior across temperature ranges
8. **Revenue Metrics** - Total revenue, average fare, revenue per mile

Each example includes:
- SQL query mapping to semantic layer metrics
- Results display
- Some include visualizations (bar charts, pie charts)

### 7. Visualizations

The notebook includes matplotlib visualizations for:
- Mode share bar chart
- Day part distribution pie chart
- Other charts can be easily added

## How to Use This Notebook

1. **Start Jupyter:**
   ```bash
   cd /Users/brandoncgay/Documents/Projects/nyc-mobility-weather-analytics
   poetry run jupyter notebook
   ```

2. **Open the notebook:**
   - Navigate to `notebooks/`
   - Click `03_semantic_models_and_metrics.ipynb`

3. **Run cells in order:**
   - Execute setup cell to connect to DuckDB
   - Run analysis cells to see metric examples
   - Modify queries to explore different dimensions
   - Close connection when done

## Key Takeaways

### Benefits of Our Semantic Layer
1. **Centralized Business Logic** - Metrics defined once, used everywhere
2. **Self-Documenting** - Every metric has description and label
3. **Type Safety** - Simple vs Derived ensures correct calculations
4. **Reusability** - Derived metrics compose from simple metrics
5. **Governance** - Single source of truth

### When to Use Each Model

**Use `trips` model when:**
- Need trip-level detail
- Analyzing individual trip characteristics
- Joining with location/weather dimensions
- Calculating custom aggregations

**Use `hourly_mobility` model when:**
- Need time-series analysis by hour
- Performance is critical (pre-aggregated)
- Comparing mode share over time
- Analyzing rush hour patterns

## Files Referenced

**Semantic Models:**
- `dbt/models/marts/core/semantic_models/sem_trips.yml`
- `dbt/models/marts/core/semantic_models/sem_hourly_mobility.yml`

**Metric Definitions:**
- `dbt/models/marts/core/metrics/metrics_trips_core.yml`
- `dbt/models/marts/core/metrics/metrics_mode_share.yml`
- `dbt/models/marts/core/metrics/metrics_time_patterns.yml`
- `dbt/models/marts/core/metrics/metrics_weather_impact.yml`

**Data Sources:**
- `data/nyc_mobility.duckdb` - DuckDB database
- Fact table: `core_core.fct_trips`
- Dimension tables: `dim_date`, `dim_time`, `dim_location`

## Customization Ideas

1. **Add new analyses** - Pick a metric and explore across different dimensions
2. **Create new visualizations** - Add charts for other metrics
3. **Combine metrics** - Create new derived metrics by combining existing ones
4. **Export results** - Save analysis results to CSV for reporting
5. **Time-series plots** - Visualize metrics over time

## Next Steps

1. **Run the notebook** - Execute all cells to see the metrics in action
2. **Explore specific metrics** - Pick interesting metrics and dig deeper
3. **Create custom analyses** - Add your own SQL queries and visualizations
4. **Build dashboards** - Use these metrics in external BI tools
5. **Extend the semantic layer** - Add new metrics for new business questions

## Resources

- **MetricFlow Documentation:** https://docs.getdbt.com/docs/build/metricflow
- **dbt Semantic Layer:** https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl
- **Project Data Dictionary:** `docs/DATA_DICTIONARY.md`
- **Pipeline Operations Guide:** `docs/PIPELINE_OPERATIONS_GUIDE.md`
