{{ config(materialized='table') }}

with infrastructure as (

    select *
    from {{ ref('stg_afdc_city_infrastructure') }}

),

ranked as (

    select
        concat(
            city,
            '|',
            state,
            '|',
            country
        ) as city_state_key,

        city,
        state,
        country,

        station_count,

        level1_ports,
        level2_ports,
        dc_fast_ports,

        total_known_ports,

        dc_fast_station_count,
        network_count,

        ports_per_station,
        dc_fast_station_share_pct,

        latest_station_update,

        row_number() over (
            partition by state
            order by
                station_count desc,
                total_known_ports desc,
                city
        ) as state_station_rank,

        row_number() over (
            order by
                station_count desc,
                total_known_ports desc,
                state,
                city
        ) as national_station_rank,

        row_number() over (
            partition by state
            order by
                total_known_ports desc,
                station_count desc,
                city
        ) as state_port_rank

    from infrastructure

)

select *
from ranked
