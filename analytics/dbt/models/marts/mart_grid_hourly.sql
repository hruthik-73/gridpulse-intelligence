{{ config(materialized='table') }}

with hourly as (

    select *
    from {{ ref('stg_eia_balancing_authority_hourly') }}

),

respondent_types as (

    select
        respondent,
        entity_type

    from {{ ref('eia_respondent_types') }}

),

classified as (

    select
        hourly.*,

        coalesce(
            respondent_types.entity_type,
            'balancing_authority'
        ) as entity_type

    from hourly

    left join respondent_types
        on hourly.respondent
            = respondent_types.respondent

)

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
    entity_type,

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

from classified
