{{
    config(
        severity='warn',
        tags=['data_quality', 'backfill_validation']
    )
}}

{#
    Custom Test: Assert Monthly Data Completeness

    This test checks if each month in the data range has a reasonable number of trips.
    A month with 0 or very few trips likely indicates a backfill failure.

    Success criteria: Every month should have at least 100,000 trips.
    (NYC processes millions of trips per month, so <100k indicates missing data)
#}

with monthly_counts as (
    select
        date_trunc('month', pickup_datetime) as month,
        count(*) as trip_count
    from {{ ref('fct_trips') }}
    group by date_trunc('month', pickup_datetime)
),

months_with_low_data as (
    select
        month,
        trip_count,
        'Month has suspiciously low trip count - check for backfill issues' as warning_message
    from monthly_counts
    where trip_count < 100000  -- Threshold: 100k trips minimum per month
)

-- Return months that fail the check
select * from months_with_low_data
order by month
