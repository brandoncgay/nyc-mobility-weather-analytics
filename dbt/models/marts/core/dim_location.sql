{{
    config(
        materialized='table',
        tags=['silver', 'marts', 'dimension']
    )
}}

{#
    SILVER LAYER - Location Dimension
    This is where BUSINESS LOGIC lives for location categorizations.

    Authoritative location dimension built from TLC taxi zones seed data
    with business categorizations for zones and boroughs.
#}

with location_seed as (
    select * from {{ ref('tlc_taxi_zones') }}
),

location_dimension as (
    select
        -- Surrogate key
        cast(location_id as varchar) as location_key,

        -- Attributes from seed
        location_id,
        borough,
        zone as zone_name,
        service_zone,

        -- ============================================
        -- BUSINESS LOGIC: Borough categorizations
        -- ============================================

        -- Location tier (core vs outer boroughs)
        case
            when borough = 'Manhattan' then 'core'
            when borough in ('Brooklyn', 'Queens') then 'urban'
            when borough in ('Bronx', 'Staten Island') then 'outer'
            when borough = 'EWR' then 'airport'
            else 'unknown'
        end as location_tier,

        -- Borough region grouping
        case
            when borough = 'Manhattan' then 'Manhattan'
            when borough in ('Brooklyn', 'Queens') then 'Western_Boroughs'
            when borough in ('Bronx', 'Staten Island') then 'Outer_Boroughs'
            when borough = 'EWR' then 'Airport'
            else 'Other'
        end as borough_region,

        -- ============================================
        -- BUSINESS LOGIC: Service zone flags
        -- ============================================

        -- Yellow zone flag (where yellow taxis can pick up)
        case
            when service_zone = 'Yellow Zone' then true
            else false
        end as is_yellow_zone,

        -- Boro zone flag
        case
            when service_zone = 'Boro Zone' then true
            else false
        end as is_boro_zone,

        -- Airport flag
        case
            when service_zone = 'Airports' then true
            when borough = 'EWR' then true
            else false
        end as is_airport,

        -- ============================================
        -- BUSINESS LOGIC: High-demand zones
        -- ============================================

        -- Major commercial/tourist areas
        case
            when zone in (
                'Midtown Center',
                'Midtown East',
                'Midtown North',
                'Midtown South',
                'Times Sq/Theatre District',
                'Penn Station/Madison Sq West',
                'Financial District North',
                'Financial District South',
                'Upper East Side North',
                'Upper East Side South',
                'Upper West Side North',
                'Upper West Side South'
            ) then true
            else false
        end as is_high_demand_zone,

        -- Transportation hubs
        case
            when zone in (
                'JFK Airport',
                'LaGuardia Airport',
                'Newark Airport',
                'Penn Station/Madison Sq West',
                'Grand Central'
            ) then true
            else false
        end as is_transportation_hub,

        -- Tourist/entertainment areas
        case
            when zone in (
                'Times Sq/Theatre District',
                'Central Park',
                'SoHo',
                'Greenwich Village North',
                'Greenwich Village South',
                'East Village',
                'West Village',
                'Chinatown',
                'Little Italy/NoLiTa'
            ) then true
            else false
        end as is_tourist_area,

        -- Business districts
        case
            when zone in (
                'Financial District North',
                'Financial District South',
                'Midtown Center',
                'Midtown East',
                'Midtown North',
                'Midtown South'
            ) then true
            else false
        end as is_business_district

    from location_seed
)

select * from location_dimension
