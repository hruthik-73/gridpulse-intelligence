select
    city_state_key,
    station_count,
    level1_ports,
    level2_ports,
    dc_fast_ports,
    total_known_ports

from {{ ref('mart_ev_city_rankings') }}

where
    station_count < 0
    or level1_ports < 0
    or level2_ports < 0
    or dc_fast_ports < 0
    or total_known_ports < 0
