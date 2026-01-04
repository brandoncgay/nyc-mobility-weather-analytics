{{
    config(
        materialized='table',
        tags=['silver', 'marts', 'dimension']
    )
}}

{#
    SILVER LAYER - Weather Dimension
    This is where ALL BUSINESS LOGIC lives for weather categorizations.

    Authoritative weather dimension with hourly grain and comprehensive
    business categorizations for temperature, precipitation, wind, etc.
#}

with weather_source as (
    select * from {{ ref('stg_weather__hourly') }}
),

weather_dimension as (
    select
        -- Surrogate key (timestamp at hourly grain)
        timestamp as weather_key,

        -- Raw measurements from Bronze
        timestamp,
        temp,
        feels_like,
        humidity,
        dew_point,
        precipitation,
        rain,
        snowfall,
        cloud_cover,
        pressure,
        wind_speed,
        wind_direction,

        -- ============================================
        -- BUSINESS LOGIC: Temperature categorizations
        -- ============================================

        case
            when temp < 0 then 'cold'
            when temp < 10 then 'cool'
            when temp < 20 then 'mild'
            when temp < 30 then 'warm'
            else 'hot'
        end as temp_category,

        case
            when feels_like < 0 then 'very_cold'
            when feels_like < 10 then 'cold'
            when feels_like < 20 then 'comfortable'
            when feels_like < 30 then 'warm'
            else 'hot'
        end as feels_like_category,

        -- Temperature in Fahrenheit (for US audiences)
        round((temp * 9.0 / 5.0) + 32, 1) as temp_fahrenheit,
        round((feels_like * 9.0 / 5.0) + 32, 1) as feels_like_fahrenheit,

        -- ============================================
        -- BUSINESS LOGIC: Precipitation categorizations
        -- ============================================

        case
            when precipitation = 0 then 'none'
            when snowfall > 0 and rain > 0 then 'mixed'
            when snowfall > 0 then 'snow'
            when rain > 0 then 'rain'
            else 'none'
        end as precipitation_type,

        case
            when precipitation = 0 then 'none'
            when precipitation < 2.5 then 'light'
            when precipitation < 7.6 then 'moderate'
            when precipitation < 50 then 'heavy'
            else 'extreme'
        end as precipitation_intensity,

        -- Flag for any precipitation
        case
            when precipitation > 0 then true
            else false
        end as has_precipitation,

        -- ============================================
        -- BUSINESS LOGIC: Wind categorizations
        -- ============================================

        case
            when wind_speed < 5 then 'calm'
            when wind_speed < 10 then 'breezy'
            when wind_speed < 15 then 'windy'
            when wind_speed < 20 then 'very_windy'
            else 'strong'
        end as wind_category,

        -- Wind in mph (for US audiences)
        round(wind_speed * 2.237, 1) as wind_speed_mph,

        -- Wind direction cardinal
        case
            when wind_direction >= 337.5 or wind_direction < 22.5 then 'N'
            when wind_direction >= 22.5 and wind_direction < 67.5 then 'NE'
            when wind_direction >= 67.5 and wind_direction < 112.5 then 'E'
            when wind_direction >= 112.5 and wind_direction < 157.5 then 'SE'
            when wind_direction >= 157.5 and wind_direction < 202.5 then 'S'
            when wind_direction >= 202.5 and wind_direction < 247.5 then 'SW'
            when wind_direction >= 247.5 and wind_direction < 292.5 then 'W'
            when wind_direction >= 292.5 and wind_direction < 337.5 then 'NW'
            else 'VARIABLE'
        end as wind_direction_cardinal,

        -- ============================================
        -- BUSINESS LOGIC: Cloud cover categorizations
        -- ============================================

        case
            when cloud_cover < 25 then 'clear'
            when cloud_cover < 50 then 'partly_cloudy'
            when cloud_cover < 75 then 'mostly_cloudy'
            else 'overcast'
        end as cloud_cover_category,

        -- ============================================
        -- BUSINESS LOGIC: Humidity categorizations
        -- ============================================

        case
            when humidity < 30 then 'dry'
            when humidity < 60 then 'comfortable'
            when humidity < 80 then 'humid'
            else 'very_humid'
        end as humidity_category,

        -- ============================================
        -- BUSINESS LOGIC: Overall weather description
        -- ============================================

        case
            -- Severe conditions
            when precipitation > 10 and temp < 0 then 'blizzard'
            when precipitation > 10 then 'severe_storm'

            -- Snow conditions
            when snowfall > 5 then 'heavy_snow'
            when snowfall > 0 then 'snow'

            -- Rain conditions
            when rain > 7.6 then 'heavy_rain'
            when rain > 2.5 then 'moderate_rain'
            when rain > 0 then 'light_rain'

            -- Clear/cloudy conditions
            when cloud_cover > 75 then 'cloudy'
            when cloud_cover > 50 then 'partly_cloudy'
            else 'clear'
        end as weather_description,

        -- ============================================
        -- BUSINESS LOGIC: Comfort/safety flags
        -- ============================================

        -- Good weather for outdoor activities
        case
            when temp between 15 and 25
                and precipitation = 0
                and wind_speed < 10
                and cloud_cover < 50
            then true
            else false
        end as is_pleasant_weather,

        -- Adverse conditions that might impact mobility
        case
            when precipitation > 5 then true
            when temp < -5 or temp > 35 then true
            when wind_speed > 15 then true
            else false
        end as is_adverse_weather,

        -- Ideal cycling weather
        case
            when temp between 10 and 25
                and precipitation = 0
                and wind_speed < 15
            then true
            else false
        end as is_good_cycling_weather

    from weather_source
)

select * from weather_dimension
