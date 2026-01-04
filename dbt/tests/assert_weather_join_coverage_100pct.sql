{{
    config(
        severity='error',
        tags=['data_quality', 'custom']
    )
}}

{#
    Custom Test: Assert High Join Coverage Between Trips and Weather

    This test validates that trips have matching weather data.
    Success criteria: Require 99.99% or better coverage.

    Known data gap: 53 trips from Sept 30 before 5pm (weather data starts at 5pm).
    Current coverage: 99.9996% (12,353,330 / 12,353,383 trips).

    Test fails if coverage drops below 99.99%.
#}

with trips_with_weather as (
    select
        count(*) as total_trips,
        sum(case when temp_category is not null then 1 else 0 end) as trips_with_weather
    from {{ ref('fct_trips') }}
)

select
    total_trips,
    trips_with_weather,
    (trips_with_weather * 100.0 / total_trips) as coverage_pct
from trips_with_weather
where (trips_with_weather * 100.0 / total_trips) < 99.99  -- Fail if coverage < 99.99%
