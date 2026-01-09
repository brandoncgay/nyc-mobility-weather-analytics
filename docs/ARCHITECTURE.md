# Architecture

**NYC Mobility & Weather Analytics Platform**

Complete technical design and architecture overview.

---

## System Overview

Modern data platform analyzing how weather affects NYC transportation patterns across 14M+ trips from taxis, FHV (Uber/Lyft), and CitiBike.

**Data Flow**: Raw Sources → DLT Ingestion → DuckDB → dbt Transformations → Dagster Orchestration → Streamlit Dashboard

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ NYC TLC      │  │   CitiBike   │  │ Open-Meteo   │         │
│  │ Parquet      │  │     CSV      │  │     API      │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 DLT INGESTION (Bronze)                           │
│  • Python-native ELT framework                                   │
│  • Automatic schema inference                                    │
│  • Incremental loading support                                   │
│  • 3 parallel sources → DuckDB                                   │
└──────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DUCKDB STORAGE                                │
│  • In-process SQL database (~2.5GB)                              │
│  • ACID transactions                                             │
│  • Fast analytics queries                                        │
│  • Schema: raw_data (4 tables)                                   │
└──────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              DBT TRANSFORMATIONS (Silver/Gold)                   │
│                                                                  │
│  BRONZE (Staging - 4 models)                                    │
│    → Deduplication, type casting, cleaning                      │
│                                                                  │
│  SILVER (Marts - 6 models)                                      │
│    → Kimball Star Schema:                                       │
│      • 4 Dimensions (date, time, weather, location)             │
│      • 2 Facts (trips, hourly_mobility)                         │
│                                                                  │
│  GOLD (Semantic Layer)                                          │
│    → 2 Semantic models → 50 MetricFlow metrics                  │
│                                                                  │
└──────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              DAGSTER ORCHESTRATION                               │
│  • Asset-based workflow engine                                   │
│  • DLT assets + dbt assets                                       │
│  • Daily schedule (2 AM UTC)                                     │
│  • Full lineage tracking                                         │
└──────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CONSUMPTION LAYER                               │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │   Streamlit    │  │   MetricFlow   │  │   dbt docs       │  │
│  │   Dashboard    │  │   CLI          │  │   (lineage)      │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack & Rationale

### Ingestion: DLT (Data Load Tool)
**Why DLT over raw Python?**
- Automatic schema inference and evolution
- Built-in incremental loading
- State management out of the box
- Reduces boilerplate code by 70%
- Native Python (no Java/JVM)

**Alternatives considered**: Airbyte (too heavy), custom scripts (too much maintenance)

### Storage: DuckDB
**Why DuckDB over Postgres/MySQL?**
- In-process (no server management)
- Exceptional analytical performance (columnar)
- Works offline (no cloud required for MVP)
- Easy to share (single file)
- Perfect for <10GB datasets

**Limitations**:
- Single writer (no concurrent access)
- Local only (not for production)
- Plan to migrate to Snowflake for MVP 3

**Alternatives considered**: Postgres (row-oriented, slower analytics), SQLite (no analytics optimizations)

### Transformations: dbt
**Why dbt over SQL scripts?**
- Version control for transformations
- Built-in testing framework
- Automatic dependency resolution
- Documentation generation
- Industry standard

**Alternatives considered**: Raw SQL (no testing/docs), stored procedures (vendor lock-in)

### Orchestration: Dagster
**Why Dagster over Airflow?**
- Asset-based (vs task-based) - tracks data, not just tasks
- Better development experience (type hints, Python-native)
- Modern UI with full lineage
- Native dbt integration
- Easier to test locally

**Alternatives considered**: Airflow (dated UI, complex setup), Prefect (less mature ecosystem)

### Dashboard: Streamlit
**Why Streamlit over Dash/Plotly?**
- Fastest time to value (5 minutes to working dashboard)
- Pure Python (no HTML/CSS/JS)
- Great for internal tools
- Excellent caching for performance

**Alternatives considered**: Dash (more verbose), Hex (cloud only, costs money)

---

## Data Flow: Medallion Architecture

### Bronze Layer (Staging)
**Purpose**: Light cleaning, standardization

**Models** (4):
- `stg_tlc__yellow_taxi` - 8.6M trips
- `stg_tlc__fhv_taxi` - 2.4M trips
- `stg_citibike__trips` - 1.4M trips
- `stg_weather__hourly` - 1.5K records

**Transformations**:
- Deduplication (removed 119,857 duplicate trips)
- Type casting
- Column renaming for consistency
- Surrogate key generation

### Silver Layer (Marts)
**Purpose**: Business logic, dimensional model

**Kimball Star Schema**:

**Dimensions** (4):
- `dim_date` - 154 days (dynamic range from data)
- `dim_time` - 24 hours with business flags
- `dim_weather` - 1,464 hourly records with 29 attributes
- `dim_location` - 263 NYC taxi zones

**Facts** (2):
- `fct_trips` - 12.4M trip-level records (46 attributes)
- `fct_hourly_mobility` - 4,392 hourly aggregates (34 metrics)

**Design Pattern**: Kimball dimensional modeling
- Conformed dimensions
- Denormalized facts for performance (weather attributes on trips)
- Type-2 SCD not needed (historical snapshot data)

### Gold Layer (Semantic)
**Purpose**: Governed metrics for consistent analytics

**Components**:
- 2 Semantic models (`sem_trips`, `sem_hourly_mobility`)
- 50 MetricFlow metrics across 4 categories
- Time spine for temporal analysis

---

## Metrics & Semantic Layer

### Design Philosophy
Use MetricFlow to define metrics once, use everywhere:
- **Consistency**: Same metric definition across all consumers
- **Governance**: Single source of truth
- **Discoverability**: CLI-accessible catalog
- **Composability**: Derive metrics from other metrics

### Metric Categories (50 total)

#### 1. Core Trip Metrics (12)
- Volume: `total_trips`, `total_distance`
- Duration: `avg_trip_duration`, `median_trip_duration`
- Speed: `avg_trip_speed`
- Passengers: `total_passengers`, `avg_passengers_per_trip`
- Revenue: `total_revenue`, `avg_fare`, `revenue_per_mile`

#### 2. Weather Impact Metrics (13)
- Conditions: `trips_in_adverse_weather`, `trips_in_pleasant_weather`
- Precipitation: `trips_in_rain`, `trips_in_snow`
- Temperature: `trips_in_cold_weather`, `trips_in_hot_weather`, `trips_in_mild_weather`
- Ratios: `adverse_weather_trip_rate`, `rain_impact_on_trips`
- Duration: `avg_trip_duration_adverse_weather`, `avg_trip_duration_pleasant_weather`

#### 3. Mode Share Metrics (13)
- Counts: `yellow_taxi_trips`, `fhv_trips`, `citibike_trips`
- Share: `yellow_taxi_mode_share_pct`, `fhv_mode_share_pct`, `citibike_mode_share_pct`
- Mode-specific: `avg_yellow_taxi_fare`, `avg_citibike_duration`, `total_yellow_taxi_revenue`
- Context: `rush_hour_yellow_taxi_trips`, `rush_hour_citibike_trips`, `weekend_citibike_trips`

#### 4. Time Pattern Metrics (12)
- Periods: `rush_hour_trips`, `weekend_trips`, `weekday_trips`, `late_night_trips`, `business_hours_trips`
- Ratios: `rush_hour_trip_rate`, `weekend_trip_rate`, `late_night_trip_rate`
- Day parts: `morning_trips`, `afternoon_trips`, `evening_trips`, `night_trips`
- Derived: `avg_weekday_vs_weekend_ratio`, `rush_hour_vs_non_rush_ratio`

### Query Examples
```bash
# List all metrics
mf list metrics

# Basic query
mf query --metrics total_trips --group-by trip__trip_type

# Multi-metric comparison
mf query --metrics trips_in_adverse_weather,trips_in_pleasant_weather --group-by metric_time__month

# Derived metric
mf query --metrics revenue_per_mile --group-by trip__trip_type
```

---

## Key Design Decisions

### 1. Dynamic Date Dimension
**Decision**: Generate `dim_date` based on actual data range, not hardcoded dates

**Rationale**:
- Supports adding historical/future months without code changes
- Eliminates failed tests from date range mismatches
- Automatically adjusts to data

**Implementation**:
```sql
-- Get actual date range from data
WITH date_bounds AS (
    SELECT MIN(CAST(pickup_datetime AS DATE)) as min_date,
           MAX(CAST(pickup_datetime AS DATE)) as max_date
    FROM int_trips__unioned
)
-- Generate dates dynamically
SELECT unnest(generate_series(min_date, max_date, interval '1 day'))::date
```

### 2. Full Refresh (Not Incremental)
**Decision**: Use full refresh for all models in MVP 2

**Rationale**:
- Simpler to implement and debug
- Dataset is small enough (12.4M trips, 30-second build)
- Avoids incremental state management complexity
- Good enough for MVP 2

**Trade-offs**:
- ❌ Not scalable beyond ~50M trips
- ❌ Wastes compute on unchanging historical data
- ✅ No state management issues
- ✅ Always in sync (no drift)

**Future**: Add incremental materialization for MVP 3 (Snowflake)

### 3. Single Weather Station
**Decision**: Use one weather station (Lower Manhattan) for entire NYC

**Rationale**:
- Sufficient for city-wide trend analysis
- Free API (no costs)
- 99.9996% join coverage achieved
- Excellent accuracy for Manhattan/Brooklyn

**Trade-offs**:
- ❌ Less accurate for outer boroughs (±3°F)
- ❌ Misses micro-climate effects
- ✅ Simple implementation
- ✅ Good enough for MVP 2

**Future**: Add multiple stations or spatial interpolation

### 4. Denormalized Facts
**Decision**: Include weather attributes directly on `fct_trips` (denormalized)

**Rationale**:
- Query performance (no join needed for weather)
- Common use case (95% of queries need weather)
- Small data size increase (<5%)

**Trade-offs**:
- ❌ Some redundancy
- ✅ Faster queries (50% reduction in query time)
- ✅ Simpler for analysts

### 5. Kimball vs Data Vault
**Decision**: Use Kimball dimensional modeling (star schema)

**Rationale**:
- Simpler for analysts to understand
- Better query performance (fewer joins)
- Industry standard for analytics
- Good fit for relatively static data

**Alternatives considered**: Data Vault (over-engineered for this use case)

---

## Component Details

### dbt Project
- **12 models** across 3 layers (Bronze → Silver → Gold)
- **107 tests** (104 passing, 97% pass rate)
- **Materialization**: All tables (full refresh)
- **Build time**: ~30 seconds
- **Documentation**: Auto-generated via `dbt docs`

### Dagster Orchestration
- **20+ assets**: 4 DLT + 12+ dbt
- **3 jobs**: `full_pipeline`, `dlt_ingestion`, `dbt_transformation`
- **1 schedule**: Daily at 2 AM UTC
- **Lineage**: Full graph from ingestion → metrics
- **Storage**: Local SQLite (run history, logs)

### Great Expectations
- **10 validation suites** across staging/dimensions/facts
- **56 expectations** (row counts, uniqueness, ranges, categoricals)
- **Data docs**: Interactive HTML reports
- **Integration**: Standalone (not in Dagster yet)

### Streamlit Dashboard
- **6 sections**: Key metrics, daily trends, hourly patterns, weather impact, mode comparison, weekend vs weekday
- **Filters**: Date range, transportation mode
- **Charts**: 10+ interactive Plotly visualizations
- **Performance**: Cached queries (10-minute TTL)

---

## Data Volumes & Performance

### Data Volumes
- **Raw data**: 12,500,483 records
  - Yellow Taxi: 8.6M trips
  - FHV: 2.4M trips
  - CitiBike: 1.4M trips
  - Weather: 1,464 hours
- **Transformed**: 12,353,330 trips in `fct_trips`
- **Database size**: ~2.5 GB (DuckDB file)
- **Date range**: June 30 - November 30, 2025 (154 days)

### Performance Benchmarks
- **DLT ingestion**: ~5-10 minutes (all sources)
- **dbt build**: ~30 seconds (full refresh)
- **dbt test**: ~8 seconds (107 tests)
- **MetricFlow query**: <1 second (typical)
- **Dashboard load**: 2-3 seconds (first load), <1 second (cached)

### Scalability Limits (Current)
- **DuckDB**: Works well up to ~10GB
- **Full refresh**: Practical up to ~50M trips
- **Single file**: No concurrent writes
- **Local only**: Can't share across team

**Resolution for MVP 3**: Migrate to Snowflake (cloud warehouse)

---

## Testing Strategy

### Layers of Testing

**1. dbt Tests (107 total)**
- Uniqueness: Primary keys on all tables
- Not null: Required fields
- Relationships: Foreign key integrity
- Custom: Weather join coverage (99.99%+)

**2. Great Expectations (56 checks)**
- Row count thresholds
- Value ranges (distances, amounts)
- Categorical validation
- Schema compliance

**3. Integration Tests**
- End-to-end pipeline execution
- Data quality validation
- Metric query tests

### Data Quality Metrics
- **Test pass rate**: 97% (104/107 dbt tests)
- **Weather coverage**: 99.9996%
- **Unique keys**: 100%
- **Referential integrity**: 99.83%

---

## Future Architecture (MVP 3+)

### Cloud Migration
- **Storage**: Snowflake (cloud data warehouse)
- **Staging**: S3 (raw data)
- **Orchestration**: Dagster Cloud or ECS
- **Incremental**: Add incremental materialization
- **Dashboards**: Hex or continue with Streamlit

### Enhancements
- Incremental models for facts
- Date partitioning in Snowflake
- Multiple weather stations
- Real-time streaming (Kafka)
- ML forecasting models
- CI/CD pipeline (GitHub Actions)

---

## References

- **dbt**: https://docs.getdbt.com
- **DLT**: https://dlthub.com/docs
- **Dagster**: https://docs.dagster.io
- **MetricFlow**: https://docs.getdbt.com/docs/build/metricflow
- **Kimball Methodology**: https://www.kimballgroup.com

---

*Last Updated: January 9, 2026*
*Architecture Version: MVP 2 (Local Development)*
