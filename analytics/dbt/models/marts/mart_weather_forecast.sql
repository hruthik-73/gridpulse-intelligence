{{ config(materialized='table') }}

with weather as (

    select *
    from {{ ref('stg_nws_hourly_weather') }}

),

sequenced as (

    select
        concat(
            location_key,
            '|',
            cast(period_start as varchar)
        ) as weather_forecast_key,

        location_key,

        latitude,
        longitude,

        period_start,
        period_end,
        forecast_date,
        forecast_hour,

        temperature_f,
        temperature_c,

        precipitation_probability,
        precipitation_risk,

        relative_humidity,

        wind_speed,
        wind_direction,
        short_forecast,

        replay,

        topic,
        kafka_partition,
        kafka_offset,
        kafka_timestamp,

        row_number() over (
            partition by location_key
            order by period_start
        ) as forecast_sequence

    from weather

)

select *
from sequenced
