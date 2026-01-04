{{
    config(
        materialized='table',
        tags=['silver', 'marts', 'dimension']
    )
}}

{#
    SILVER LAYER - Time Dimension
    This is where BUSINESS LOGIC lives for time-of-day attributes.

    Authoritative time dimension with hourly grain and business categorizations.
#}

with hours as (
    -- Generate all 24 hours
    select unnest(generate_series(0, 23)) as hour
),

time_dimension as (
    select
        -- Surrogate key
        cast(hour as varchar) as time_key,

        -- Hour value (24-hour format)
        hour,

        -- BUSINESS LOGIC: 12-hour format conversion
        case
            when hour = 0 then 12
            when hour <= 12 then hour
            else hour - 12
        end as hour_12,

        -- BUSINESS LOGIC: AM/PM indicator
        case
            when hour < 12 then 'AM'
            else 'PM'
        end as am_pm,

        -- BUSINESS LOGIC: Day part categorization
        case
            when hour between 6 and 11 then 'morning'
            when hour between 12 and 17 then 'afternoon'
            when hour between 18 and 21 then 'evening'
            else 'night'
        end as day_part,

        -- BUSINESS LOGIC: Business hours flag (9am-5pm)
        case
            when hour between 9 and 17 then true
            else false
        end as is_business_hours,

        -- BUSINESS LOGIC: Rush hour flag (7-9am, 5-7pm)
        case
            when hour between 7 and 9 then true
            when hour between 17 and 19 then true
            else false
        end as is_rush_hour,

        -- BUSINESS LOGIC: Late night flag (11pm-5am)
        case
            when hour >= 23 or hour < 5 then true
            else false
        end as is_late_night,

        -- BUSINESS LOGIC: Peak dining hours (12-2pm, 6-9pm)
        case
            when hour between 12 and 14 then true
            when hour between 18 and 21 then true
            else false
        end as is_dining_hours,

        -- BUSINESS LOGIC: Detailed time period
        case
            when hour between 0 and 5 then 'overnight'
            when hour between 6 and 8 then 'early_morning'
            when hour between 9 and 11 then 'late_morning'
            when hour between 12 and 14 then 'early_afternoon'
            when hour between 15 and 17 then 'late_afternoon'
            when hour between 18 and 20 then 'early_evening'
            when hour between 21 and 22 then 'late_evening'
            else 'late_night'
        end as time_period

    from hours
)

select * from time_dimension
