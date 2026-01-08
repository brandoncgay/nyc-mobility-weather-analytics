{{
    config(
        materialized='incremental',
        unique_key='trip_key',
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns',
        tags=['silver', 'marts', 'fact']
    )
}}

{#
    SILVER LAYER - Trips Fact Table
    This is where ALL BUSINESS LOGIC lives for trip metrics and calculations.

    Authoritative trips fact table with:
    - Trip duration and speed calculations
    - Time-based attributes and flags
    - Weather enrichment
    - Foreign keys to all dimensions

    INCREMENTAL STRATEGY:
    - On first run: Full refresh (loads all historical data)
    - On subsequent runs: Only process trips with pickup_datetime newer than max in table
    - Uses delete+insert strategy for idempotent behavior
    - Handles late-arriving data by reprocessing based on unique_key
#}

with trips_unioned as (
    select * from {{ ref('int_trips__unioned') }}

    {% if is_incremental() %}
    -- Only process new trips (incremental mode)
    -- This dramatically speeds up daily runs by only processing new data
    where pickup_datetime > (select max(pickup_datetime) from {{ this }})
    {% endif %}
),

trips_with_metrics as (
    select
        *,

        -- ============================================
        -- BUSINESS LOGIC: Trip duration calculation
        -- ============================================
        datediff('minute', pickup_datetime, dropoff_datetime) as trip_duration_minutes,

        -- ============================================
        -- BUSINESS LOGIC: Speed calculation
        -- ============================================
        case
            when trip_distance is not null
                and datediff('minute', pickup_datetime, dropoff_datetime) > 0
            then (trip_distance / datediff('minute', pickup_datetime, dropoff_datetime)) * 60
            else null
        end as avg_speed_mph,

        -- ============================================
        -- BUSINESS LOGIC: Time attributes extraction
        -- ============================================
        extract(hour from pickup_datetime) as pickup_hour,
        extract(dow from pickup_datetime) as day_of_week,

        -- ============================================
        -- BUSINESS LOGIC: Weekend flag
        -- ============================================
        case
            when extract(dow from pickup_datetime) in (0, 6) then true
            else false
        end as is_weekend,

        -- ============================================
        -- BUSINESS LOGIC: Day part categorization
        -- ============================================
        case
            when extract(hour from pickup_datetime) between 6 and 11 then 'morning'
            when extract(hour from pickup_datetime) between 12 and 17 then 'afternoon'
            when extract(hour from pickup_datetime) between 18 and 21 then 'evening'
            else 'night'
        end as day_part,

        -- ============================================
        -- BUSINESS LOGIC: Rush hour flag
        -- ============================================
        case
            when extract(hour from pickup_datetime) between 7 and 9 then true
            when extract(hour from pickup_datetime) between 17 and 19 then true
            else false
        end as is_rush_hour,

        -- ============================================
        -- BUSINESS LOGIC: Business hours flag
        -- ============================================
        case
            when extract(hour from pickup_datetime) between 9 and 17 then true
            else false
        end as is_business_hours,

        -- ============================================
        -- BUSINESS LOGIC: Late night flag
        -- ============================================
        case
            when extract(hour from pickup_datetime) >= 23 or extract(hour from pickup_datetime) < 5 then true
            else false
        end as is_late_night

    from trips_unioned
),

trips_with_weather as (
    select
        -- ============================================
        -- Surrogate key
        -- ============================================
        {{ dbt_utils.generate_surrogate_key(['t.trip_id']) }} as trip_key,

        -- ============================================
        -- Foreign keys to dimensions (Kimball modeling)
        -- ============================================
        cast(cast(t.pickup_datetime as date) as varchar) as date_key,
        cast(extract(hour from t.pickup_datetime) as varchar) as time_key,
        cast(t.pickup_location_id as varchar) as pickup_location_key,
        cast(t.dropoff_location_id as varchar) as dropoff_location_key,

        -- ============================================
        -- Degenerate dimensions (attributes on fact)
        -- ============================================
        t.trip_id,
        t.trip_type,
        t.payment_type,
        t.member_type,
        t.rideable_type,

        -- ============================================
        -- Timestamps
        -- ============================================
        t.pickup_datetime,
        t.dropoff_datetime,

        -- ============================================
        -- Calculated metrics (business logic from above)
        -- ============================================
        t.trip_duration_minutes,
        t.trip_distance,
        t.avg_speed_mph,
        t.passenger_count,
        t.revenue,

        -- ============================================
        -- Time attributes (business logic from above)
        -- ============================================
        t.pickup_hour,
        t.day_of_week,
        t.is_weekend,
        t.day_part,
        t.is_rush_hour,
        t.is_business_hours,
        t.is_late_night,

        -- ============================================
        -- Weather attributes (denormalized for convenience)
        -- Join to dim_weather on hourly grain
        -- ============================================
        w.temp as temperature_celsius,
        w.temp_fahrenheit as temperature_fahrenheit,
        w.feels_like,
        w.feels_like_fahrenheit,
        w.humidity,
        w.precipitation,
        w.rain,
        w.snowfall,
        w.wind_speed,
        w.wind_speed_mph,

        -- Weather categorizations (from dim_weather business logic)
        w.temp_category,
        w.feels_like_category,
        w.precipitation_type,
        w.precipitation_intensity,
        w.wind_category,
        w.wind_direction_cardinal,
        w.cloud_cover_category,
        w.humidity_category,
        w.weather_description,
        w.is_pleasant_weather,
        w.is_adverse_weather,
        w.is_good_cycling_weather

    from trips_with_metrics t
    left join {{ ref('dim_weather') }} w
        on date_trunc('hour', t.pickup_datetime) = date_trunc('hour', w.timestamp)
)

select * from trips_with_weather
