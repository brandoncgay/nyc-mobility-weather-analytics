{{
    config(
        materialized='incremental',
        unique_key='hour_key',
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns',
        tags=['silver', 'marts', 'fact']
    )
}}

{#
    SILVER LAYER - Hourly Mobility Fact Table
    This is where BUSINESS LOGIC lives for hourly aggregated metrics.

    Authoritative hourly mobility fact table with:
    - Trip counts and metrics aggregated by hour
    - Trip type breakdowns
    - Weather-mobility relationships

    INCREMENTAL STRATEGY:
    - On first run: Full refresh (loads all historical data)
    - On subsequent runs: Only process hours with trips newer than max hour in table
    - Uses delete+insert strategy for idempotent behavior
    - Recomputes entire hour aggregate if any new trips arrive for that hour

    BACKFILL SUPPORT:
    To backfill historical months, use one of these options:
    1. Full refresh: dbt run --full-refresh --select fct_hourly_mobility
    2. Date range: dbt run --select fct_hourly_mobility --vars '{"backfill_start_date": "2025-05-01"}'
#}

with trips as (
    select * from {{ ref('fct_trips') }}

    {% if is_incremental() %}
        {# Check if we're doing a targeted backfill with a specific start date #}
        {% if var('backfill_start_date', None) %}
            -- Backfill mode: Process data from specified start date onwards
            where date_trunc('hour', pickup_datetime) >= '{{ var("backfill_start_date") }}'::timestamp
        {% else %}
            -- Normal incremental mode: Only process trips from hours not yet in the table
            -- This speeds up daily runs by only aggregating new hourly data
            where date_trunc('hour', pickup_datetime) > (select max(hour_timestamp) from {{ this }})
        {% endif %}
    {% endif %}
),

hourly_aggregates as (
    select
        -- ============================================
        -- Surrogate key (unique identifier for each hour aggregate)
        -- ============================================
        {{ dbt_utils.generate_surrogate_key([
            'date_trunc(\'hour\', pickup_datetime)',
            'trip_type',
            'temp_category',
            'precipitation_type',
            'is_weekend',
            'day_part'
        ]) }} as hour_key,

        -- ============================================
        -- Foreign keys to dimensions
        -- ============================================
        date_key,
        time_key,

        -- ============================================
        -- Dimensions for slicing
        -- ============================================
        trip_type,
        temp_category,
        precipitation_type,
        is_weekend,
        day_part,

        -- ============================================
        -- Timestamp
        -- ============================================
        date_trunc('hour', pickup_datetime) as hour_timestamp,

        -- ============================================
        -- BUSINESS LOGIC: Aggregated trip metrics
        -- ============================================
        count(*) as trip_count,
        sum(revenue) as total_revenue,
        avg(trip_duration_minutes) as avg_trip_duration_minutes,
        avg(trip_distance) as avg_trip_distance_miles,
        avg(avg_speed_mph) as avg_speed_mph,
        sum(passenger_count) as total_passengers,

        -- Percentile metrics
        percentile_cont(0.5) within group (order by trip_duration_minutes) as median_trip_duration_minutes,
        percentile_cont(0.5) within group (order by trip_distance) as median_trip_distance_miles,

        -- ============================================
        -- BUSINESS LOGIC: Weather metrics (hourly averages)
        -- ============================================
        avg(temperature_celsius) as avg_temperature_celsius,
        avg(temperature_fahrenheit) as avg_temperature_fahrenheit,
        avg(precipitation) as avg_precipitation_mm,
        avg(wind_speed_mph) as avg_wind_speed_mph,
        avg(humidity) as avg_humidity_pct,

        -- ============================================
        -- BUSINESS LOGIC: Trip type breakdown
        -- ============================================
        sum(case when trip_type = 'yellow_taxi' then 1 else 0 end) as yellow_taxi_count,
        sum(case when trip_type = 'fhv' then 1 else 0 end) as fhv_count,
        sum(case when trip_type = 'citibike' then 1 else 0 end) as citibike_count,

        -- ============================================
        -- BUSINESS LOGIC: Revenue breakdown (only taxis have revenue)
        -- ============================================
        sum(case when trip_type = 'yellow_taxi' then revenue else 0 end) as yellow_taxi_revenue,
        avg(case when trip_type = 'yellow_taxi' then revenue else null end) as avg_yellow_taxi_fare,

        -- ============================================
        -- BUSINESS LOGIC: Mode share calculations
        -- ============================================
        (sum(case when trip_type = 'citibike' then 1 else 0 end) * 100.0) / count(*) as citibike_mode_share_pct,
        (sum(case when trip_type = 'yellow_taxi' then 1 else 0 end) * 100.0) / count(*) as yellow_taxi_mode_share_pct,
        (sum(case when trip_type = 'fhv' then 1 else 0 end) * 100.0) / count(*) as fhv_mode_share_pct,

        -- ============================================
        -- BUSINESS LOGIC: Rush hour metrics
        -- ============================================
        sum(case when is_rush_hour then 1 else 0 end) as rush_hour_trip_count,
        (sum(case when is_rush_hour then 1 else 0 end) * 100.0) / count(*) as rush_hour_pct,

        -- ============================================
        -- BUSINESS LOGIC: Weather impact flags
        -- ============================================
        max(case when is_adverse_weather then 1 else 0 end) as has_adverse_weather,
        max(case when is_pleasant_weather then 1 else 0 end) as has_pleasant_weather,
        max(case when is_good_cycling_weather then 1 else 0 end) as has_good_cycling_weather

    from trips
    group by
        date_key,
        time_key,
        trip_type,
        temp_category,
        precipitation_type,
        is_weekend,
        day_part,
        date_trunc('hour', pickup_datetime)
)

select * from hourly_aggregates
