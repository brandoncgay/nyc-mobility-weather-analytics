{{
    config(
        materialized='ephemeral',
        tags=['intermediate']
    )
}}

{#
    This is a shared transformation (internal plumbing) that unions all trip types
    with a standardized schema. This feeds multiple marts.

    NO BUSINESS LOGIC HERE - this is just schema standardization.
    Business logic (calculations, categorizations) lives in Silver/marts.
#}

with yellow_taxi as (
    select
        trip_id,
        'yellow_taxi' as trip_type,
        pickup_datetime,
        dropoff_datetime,
        pickup_location_id,
        dropoff_location_id,

        -- Yellow taxi specific fields (standardized to common schema)
        passenger_count,
        trip_distance,
        total_amount as revenue,
        payment_type,
        null as member_type,
        null::varchar as rideable_type

    from {{ ref('stg_tlc__yellow_taxi') }}
),

fhv_taxi as (
    select
        trip_id,
        'fhv' as trip_type,
        pickup_datetime,
        dropoff_datetime,
        pickup_location_id,
        dropoff_location_id,

        -- FHV doesn't have these fields - null for standardization
        null as passenger_count,
        null as trip_distance,
        null as revenue,
        null as payment_type,
        null as member_type,
        null::varchar as rideable_type

    from {{ ref('stg_tlc__fhv_taxi') }}
),

citibike as (
    select
        trip_id,
        'citibike' as trip_type,
        pickup_datetime,
        dropoff_datetime,
        pickup_location_id,
        dropoff_location_id,

        -- CitiBike doesn't have these fields - null for standardization
        null as passenger_count,
        null as trip_distance,
        null as revenue,
        null as payment_type,
        member_casual as member_type,
        rideable_type

    from {{ ref('stg_citibike__trips') }}
)

-- Simple union - this is internal plumbing, not business logic
select * from yellow_taxi
union all
select * from fhv_taxi
union all
select * from citibike
