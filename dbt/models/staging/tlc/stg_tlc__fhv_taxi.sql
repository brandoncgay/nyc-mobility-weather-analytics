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
    -- Remove DLT metadata columns automatically by explicit select
)

select * from cleaned
