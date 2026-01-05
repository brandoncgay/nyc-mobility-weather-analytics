{{
    config(
        materialized='table',
        tags=['metricflow', 'time_spine']
    )
}}

{#
    MetricFlow Time Spine

    This model provides a continuous series of dates/times for MetricFlow to use
    when querying time-based metrics. It must be named exactly 'metricflow_time_spine'.

    Covers: Sept 1, 2025 - Dec 31, 2025 at daily granularity
#}

with date_spine as (
    {{
        dbt_utils.date_spine(
            datepart="day",
            start_date="cast('2025-09-01' as date)",
            end_date="cast('2026-01-01' as date)"
        )
    }}
)

select
    cast(date_day as date) as date_day
from date_spine
