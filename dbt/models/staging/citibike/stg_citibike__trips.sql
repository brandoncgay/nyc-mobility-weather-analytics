{{
    config(
        materialized='view',
        tags=['bronze', 'staging', 'citibike']
    )
}}

with source as (
    select * from {{ source('citibike', 'trips') }}
),

cleaned as (
    select
        -- Use ride_id as trip_id (already unique)
        ride_id as trip_id,

        -- Bike type
        rideable_type,

        -- Timestamps (rename for consistency with taxi data)
        started_at as pickup_datetime,
        ended_at as dropoff_datetime,

        -- Station information
        start_station_name,
        start_station_id as pickup_location_id,
        end_station_name,
        end_station_id as dropoff_location_id,

        -- Coordinates (cast to proper types)
        cast(start_lat as double) as start_lat,
        cast(start_lng as double) as start_lng,
        cast(end_lat as double) as end_lat,
        cast(end_lng as double) as end_lng,

        -- Rider type
        member_casual

    from source
    -- Remove DLT metadata columns automatically by explicit select
)

select * from cleaned
