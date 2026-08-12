{{ config(materialized='view') }}

select
    location_key,

    cast(latitude as double) as latitude,
    cast(longitude as double) as longitude,

    cast(period_start as timestamp) as period_start,
    cast(period_end as timestamp) as period_end,
    cast(forecast_date as date) as forecast_date,
    cast(forecast_hour as integer) as forecast_hour,

    cast(temperature as double) as temperature,
    temperature_unit,

    cast(temperature_f as double) as temperature_f,
    cast(temperature_c as double) as temperature_c,

    cast(precipitation_probability as double)
        as precipitation_probability,

    precipitation_risk,

    cast(relative_humidity as double)
        as relative_humidity,

    wind_speed,
    wind_direction,
    short_forecast,

    event_id,
    cast(replay as boolean) as replay,

    topic,

    cast("partition" as integer)
        as kafka_partition,

    cast("offset" as bigint)
        as kafka_offset,

    cast(kafka_timestamp as timestamp)
        as kafka_timestamp

from read_parquet(
    'data/processed/gold/nws_hourly_weather/**/*.parquet',
    hive_partitioning = true
)
