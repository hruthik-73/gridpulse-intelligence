{{ config(materialized='table') }}

select
    concat(
        respondent,
        '|',
        cast(period as varchar)
    ) as grid_hour_key,

    period,
    period_date,
    hour_of_day,

    respondent,
    respondent_name,

    demand_mwh,
    demand_forecast_mwh,
    net_generation_mwh,
    total_interchange_mwh,

    demand_forecast_error_mwh,
    demand_forecast_abs_error_mwh,
    demand_forecast_error_pct,
    generation_demand_gap_mwh,

    metric_count,

    has_demand,
    has_demand_forecast,
    has_generation,
    has_interchange,

    contains_replay,
    latest_kafka_timestamp

from {{ ref('stg_eia_balancing_authority_hourly') }}
