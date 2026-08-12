{{ config(materialized='view') }}

select
    city,
    state,
    country,

    cast(station_count as bigint)
        as station_count,

    cast(level1_ports as bigint)
        as level1_ports,

    cast(level2_ports as bigint)
        as level2_ports,

    cast(dc_fast_ports as bigint)
        as dc_fast_ports,

    cast(total_known_ports as bigint)
        as total_known_ports,

    cast(dc_fast_station_count as bigint)
        as dc_fast_station_count,

    cast(network_count as bigint)
        as network_count,

    cast(ports_per_station as double)
        as ports_per_station,

    cast(dc_fast_station_share_pct as double)
        as dc_fast_station_share_pct,

    cast(latest_station_update as timestamp)
        as latest_station_update

from read_parquet(
    'data/processed/gold/afdc_city_infrastructure/**/*.parquet',
    hive_partitioning = true
)
