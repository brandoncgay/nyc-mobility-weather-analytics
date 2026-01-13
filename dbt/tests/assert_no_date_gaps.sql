{{
    config(
        severity='warn',
        tags=['data_quality', 'backfill_validation']
    )
}}

{#
    Custom Test: Assert No Significant Date Gaps in fct_trips

    This test detects if there are large gaps in the date range of trip data,
    which could indicate:
    1. A failed backfill (historical month missing)
    2. Data ingestion issues
    3. Incremental filter excluding historical data

    Success criteria: No gaps larger than 3 days between consecutive months.
#}

with date_range as (
    select
        min(cast(pickup_datetime as date)) as min_date,
        max(cast(pickup_datetime as date)) as max_date
    from {{ ref('fct_trips') }}
),

-- Generate expected date spine (all days in range)
expected_dates as (
    select unnest(
        generate_series(
            (select min_date from date_range),
            (select max_date from date_range),
            interval '1 day'
        )
    )::date as expected_date
),

-- Get actual dates with data
actual_dates as (
    select distinct cast(pickup_datetime as date) as actual_date
    from {{ ref('fct_trips') }}
),

-- Find missing dates
missing_dates as (
    select
        e.expected_date,
        case when a.actual_date is null then 1 else 0 end as is_missing
    from expected_dates e
    left join actual_dates a on e.expected_date = a.actual_date
),

-- Find consecutive missing date spans (gaps)
gaps_summary as (
    select
        count(*) as consecutive_missing_days,
        min(expected_date) as gap_start,
        max(expected_date) as gap_end
    from (
        select
            expected_date,
            is_missing,
            sum(case when is_missing = 0 then 1 else 0 end)
                over (order by expected_date) as group_id
        from missing_dates
    ) grouped
    where is_missing = 1
    group by group_id
    having count(*) > 3  -- Flag gaps larger than 3 days
)

-- Return gaps that exceed threshold
select
    gap_start,
    gap_end,
    consecutive_missing_days,
    'Large date gap detected - possible backfill failure or data ingestion issue' as warning_message
from gaps_summary
order by gap_start
