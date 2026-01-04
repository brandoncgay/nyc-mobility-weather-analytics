{{
    config(
        materialized='view',
        tags=['bronze', 'staging', 'tlc']
    )
}}

with source as (
    select * from {{ source('tlc', 'fhv_taxi') }}
),

cleaned as (
    select
        -- Generate surrogate key for trips
        {{ dbt_utils.generate_surrogate_key([
            'pickup_datetime',
            'drop_off_datetime',
            'dispatching_base_num',
            'p_ulocation_id'
        ]) }} as trip_id,

        -- Base information
        dispatching_base_num,
        affiliated_base_number,

        -- Timestamps (rename for consistency)
        pickup_datetime,
        drop_off_datetime as dropoff_datetime,

        -- Locations (standardize column names)
        cast(p_ulocation_id as integer) as pickup_location_id,
        cast(d_olocation_id as integer) as dropoff_location_id

    from source
    where pickup_datetime >= '2025-01-01'  -- Filter out old data
    -- Remove DLT metadata columns automatically by explicit select
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by pickup_datetime, dropoff_datetime, dispatching_base_num, pickup_location_id
            order by dispatching_base_num
        ) as row_num
    from cleaned
)

select * exclude (row_num) from deduplicated where row_num = 1
