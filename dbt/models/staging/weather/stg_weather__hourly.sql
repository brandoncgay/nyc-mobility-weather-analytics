{{
    config(
        materialized='view',
        tags=['bronze', 'staging', 'weather']
    )
}}

with source as (
    select * from {{ source('weather', 'hourly_weather') }}
),

cleaned as (
    select
        -- Timestamp
        timestamp,

        -- Temperature measurements (cast to double)
        cast(temp as double) as temp,
        cast(feels_like as double) as feels_like,
        cast(dew_point as double) as dew_point,

        -- Humidity
        cast(humidity as integer) as humidity,

        -- Precipitation measurements
        cast(precipitation as double) as precipitation,
        cast(rain as double) as rain,
        cast(snowfall as double) as snowfall,

        -- Cloud and atmosphere
        cast(cloud_cover as integer) as cloud_cover,
        cast(pressure as double) as pressure,

        -- Wind
        cast(wind_speed as double) as wind_speed,
        cast(wind_direction as integer) as wind_direction

    from source
    -- Remove DLT metadata columns automatically by explicit select
)

select * from cleaned
