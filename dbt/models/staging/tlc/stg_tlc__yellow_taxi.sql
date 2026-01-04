{{
    config(
        materialized='view',
        tags=['bronze', 'staging', 'tlc']
    )
}}

with source as (
    select * from {{ source('tlc', 'yellow_taxi') }}
),

cleaned as (
    select
        -- Generate surrogate key for trips
        {{ dbt_utils.generate_surrogate_key([
            'tpep_pickup_datetime',
            'tpep_dropoff_datetime',
            'vendor_id',
            'pu_location_id'
        ]) }} as trip_id,

        -- Timestamps (rename only, no transformation)
        tpep_pickup_datetime as pickup_datetime,
        tpep_dropoff_datetime as dropoff_datetime,

        -- Trip details (cast to proper types)
        cast(vendor_id as integer) as vendor_id,
        cast(passenger_count as integer) as passenger_count,
        cast(trip_distance as double) as trip_distance,
        cast(ratecode_id as integer) as ratecode_id,
        store_and_fwd_flag,

        -- Locations
        cast(pu_location_id as integer) as pickup_location_id,
        cast(do_location_id as integer) as dropoff_location_id,

        -- Payment
        cast(payment_type as integer) as payment_type,
        cast(fare_amount as double) as fare_amount,
        cast(extra as double) as extra,
        cast(mta_tax as double) as mta_tax,
        cast(tip_amount as double) as tip_amount,
        cast(tolls_amount as double) as tolls_amount,
        cast(improvement_surcharge as double) as improvement_surcharge,
        cast(total_amount as double) as total_amount,
        cast(congestion_surcharge as double) as congestion_surcharge,
        cast(airport_fee as double) as airport_fee,
        cast(cbd_congestion_fee as double) as cbd_congestion_fee

    from source
    where tpep_pickup_datetime >= '2025-01-01'  -- Filter out old data
    -- Remove DLT metadata columns automatically by explicit select
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by pickup_datetime, dropoff_datetime, vendor_id, pickup_location_id
            order by total_amount desc
        ) as row_num
    from cleaned
)

select * exclude (row_num) from deduplicated where row_num = 1
