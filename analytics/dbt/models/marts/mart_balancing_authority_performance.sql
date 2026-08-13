{{ config(materialized='table') }}

with hourly as (

    select *
    from {{ ref('mart_grid_hourly') }}

    where entity_type = 'balancing_authority'

),

aggregated as (

    select
        respondent,
        respondent_name,

        count(*) as observed_hours,

        sum(
            case
                when has_demand then 1
                else 0
            end
        ) as demand_hours,

        sum(
            case
                when demand_mwh is not null
                    and demand_forecast_mwh is not null
                    then 1
                else 0
            end
        ) as forecast_pair_hours,

        sum(
            case
                when demand_mwh is not null
                    and net_generation_mwh is not null
                    then 1
                else 0
            end
        ) as generation_pair_hours,

        avg(demand_mwh)
            as average_demand_mwh,

        max(demand_mwh)
            as peak_demand_mwh,

        avg(demand_forecast_abs_error_mwh)
            as mean_abs_forecast_error_mwh,

        avg(
            abs(demand_forecast_error_pct)
        ) as mean_abs_forecast_error_pct,

        avg(generation_demand_gap_mwh)
            as average_generation_demand_gap_mwh,

        max(latest_kafka_timestamp)
            as latest_kafka_timestamp,

        max(
            case
                when contains_replay then 1
                else 0
            end
        ) as contains_replay_int

    from hourly

    group by
        respondent,
        respondent_name

),

metrics as (

    select
        respondent,
        respondent_name,

        observed_hours,
        demand_hours,
        forecast_pair_hours,
        generation_pair_hours,

        average_demand_mwh,
        peak_demand_mwh,

        mean_abs_forecast_error_mwh,
        mean_abs_forecast_error_pct,

        average_generation_demand_gap_mwh,

        case
            when demand_hours > 0
                then (
                    forecast_pair_hours * 100.0
                    / demand_hours
                )
            else null
        end as forecast_coverage_pct,

        case
            when demand_hours > 0
                then (
                    generation_pair_hours * 100.0
                    / demand_hours
                )
            else null
        end as generation_coverage_pct,

        cast(
            contains_replay_int as boolean
        ) as contains_replay,

        latest_kafka_timestamp

    from aggregated

)

select
    *,

    dense_rank() over (
        order by
            mean_abs_forecast_error_pct asc nulls last
    ) as forecast_accuracy_rank,

    dense_rank() over (
        order by
            peak_demand_mwh desc nulls last
    ) as peak_demand_rank

from metrics
