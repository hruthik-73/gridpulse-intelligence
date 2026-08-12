select
    grid_hour_key,
    demand_mwh,
    demand_forecast_mwh,
    demand_forecast_error_mwh

from {{ ref('mart_grid_hourly') }}

where
    demand_mwh is not null
    and demand_forecast_mwh is not null
    and (
        demand_forecast_error_mwh is null
        or abs(
            demand_forecast_error_mwh
            - (
                demand_mwh
                - demand_forecast_mwh
            )
        ) > 0.000001
    )
