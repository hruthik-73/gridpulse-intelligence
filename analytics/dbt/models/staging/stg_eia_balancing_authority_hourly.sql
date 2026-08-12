{{ config(materialized='view') }}

select
    cast(period as timestamp) as period,
    cast(period_date as date) as period_date,
    respondent,
    respondent_name,
    cast(hour_of_day as integer) as hour_of_day,

    cast(demand_mwh as double) as demand_mwh,
    cast(demand_forecast_mwh as double) as demand_forecast_mwh,
    cast(net_generation_mwh as double) as net_generation_mwh,
    cast(total_interchange_mwh as double) as total_interchange_mwh,

    cast(demand_forecast_error_mwh as double)
        as demand_forecast_error_mwh,

    cast(demand_forecast_abs_error_mwh as double)
        as demand_forecast_abs_error_mwh,

    cast(demand_forecast_error_pct as double)
        as demand_forecast_error_pct,

    cast(generation_demand_gap_mwh as double)
        as generation_demand_gap_mwh,

    cast(metric_count as integer) as metric_count,

    cast(has_demand as boolean) as has_demand,
    cast(has_demand_forecast as boolean) as has_demand_forecast,
    cast(has_generation as boolean) as has_generation,
    cast(has_interchange as boolean) as has_interchange,
    cast(contains_replay as boolean) as contains_replay,

    cast(latest_kafka_timestamp as timestamp)
        as latest_kafka_timestamp

from read_parquet(
    'data/processed/gold/eia_balancing_authority_hourly/**/*.parquet',
    hive_partitioning = true
)
