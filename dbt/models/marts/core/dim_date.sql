{{
    config(
        materialized='table',
        tags=['silver', 'marts', 'dimension']
    )
}}

{#
    SILVER LAYER - Date Dimension
    This is where BUSINESS LOGIC lives for date attributes.

    Authoritative date dimension with calendar attributes and business flags.
#}

with date_spine as (
    {{
        dbt_utils.date_spine(
            datepart="day",
            start_date="cast('2025-09-01' as date)",
            end_date="cast('2025-12-31' as date)"
        )
    }}
),

date_dimension as (
    select
        -- Surrogate key
        cast(cast(date_day as date) as varchar) as date_key,

        -- Date value
        cast(date_day as date) as date,

        -- Year attributes
        extract(year from date_day) as year,
        extract(quarter from date_day) as quarter,

        -- Month attributes
        extract(month from date_day) as month,
        strftime(date_day, '%B') as month_name,
        strftime(date_day, '%b') as month_name_short,

        -- Week attributes
        extract(week from date_day) as week_of_year,
        extract(week from date_day) - extract(week from date_trunc('month', date_day)) + 1 as week_of_month,

        -- Day attributes
        extract(day from date_day) as day_of_month,
        extract(dow from date_day) as day_of_week,  -- 0=Sunday, 6=Saturday
        strftime(date_day, '%A') as day_name,
        strftime(date_day, '%a') as day_name_short,
        extract(doy from date_day) as day_of_year,

        -- BUSINESS LOGIC: Weekend flag
        case
            when extract(dow from date_day) in (0, 6) then true
            else false
        end as is_weekend,

        -- BUSINESS LOGIC: Weekday flag
        case
            when extract(dow from date_day) between 1 and 5 then true
            else false
        end as is_weekday,

        -- BUSINESS LOGIC: Month start/end flags
        case
            when extract(day from date_day) = 1 then true
            else false
        end as is_month_start,

        case
            when date_day = last_day(date_day) then true
            else false
        end as is_month_end,

        -- BUSINESS LOGIC: Quarter start/end flags
        case
            when extract(month from date_day) in (1, 4, 7, 10)
                and extract(day from date_day) = 1 then true
            else false
        end as is_quarter_start,

        case
            when extract(month from date_day) in (3, 6, 9, 12)
                and date_day = last_day(date_day) then true
            else false
        end as is_quarter_end,

        -- BUSINESS LOGIC: Year start/end flags
        case
            when extract(month from date_day) = 1
                and extract(day from date_day) = 1 then true
            else false
        end as is_year_start,

        case
            when extract(month from date_day) = 12
                and extract(day from date_day) = 31 then true
            else false
        end as is_year_end

    from date_spine
)

select * from date_dimension
