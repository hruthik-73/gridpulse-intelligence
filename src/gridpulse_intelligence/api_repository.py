"""Read-only DuckDB access for the GridPulse API."""

from pathlib import Path
from typing import Any

import duckdb
from duckdb import DuckDBPyConnection

from gridpulse_intelligence.deployment_config import get_database_path

DEFAULT_DATABASE_PATH = get_database_path()


class GridPulseRepositoryError(Exception):
    """Raised when the serving warehouse cannot be queried."""


class GridPulseRepository:
    """Read GridPulse dbt marts from DuckDB."""

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE_PATH,
    ) -> None:
        self.database_path = database_path

    def connect(
        self,
    ) -> DuckDBPyConnection:
        """Open the analytics warehouse read-only."""

        if not self.database_path.exists():
            raise GridPulseRepositoryError(
                "GridPulse analytics warehouse does not exist. Run `make analytics` first."
            )

        try:
            return duckdb.connect(
                str(self.database_path),
                read_only=True,
            )
        except duckdb.Error as exc:
            raise GridPulseRepositoryError("Unable to open GridPulse analytics warehouse.") from exc

    @staticmethod
    def _rows_to_dicts(
        connection: DuckDBPyConnection,
        query: str,
        parameters: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute SQL and map result rows to dictionaries."""

        cursor = connection.execute(
            query,
            parameters or [],
        )

        columns = [item[0] for item in cursor.description]

        return [
            dict(
                zip(
                    columns,
                    row,
                    strict=True,
                )
            )
            for row in cursor.fetchall()
        ]

    def platform_status(
        self,
    ) -> dict[str, int]:
        """Return serving-layer row counts."""

        with self.connect() as connection:
            result = connection.execute(
                """
                select
                    (
                        select count(*)
                        from analytics.mart_grid_hourly
                    ) as grid_hourly_rows,

                    (
                        select count(*)
                        from analytics.mart_balancing_authority_performance
                    ) as balancing_authorities,

                    (
                        select count(*)
                        from analytics.mart_ev_city_rankings
                    ) as ev_cities,

                    (
                        select count(*)
                        from analytics.mart_weather_forecast
                    ) as weather_forecasts
                """
            ).fetchone()

        if result is None:
            raise GridPulseRepositoryError("Unable to calculate platform status.")

        return {
            "grid_hourly_rows": int(result[0]),
            "balancing_authorities": int(result[1]),
            "ev_cities": int(result[2]),
            "weather_forecasts": int(result[3]),
        }

    def balancing_authorities(
        self,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return balancing-authority analytics rankings."""

        with self.connect() as connection:
            return self._rows_to_dicts(
                connection,
                """
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

                    forecast_coverage_pct,
                    generation_coverage_pct,

                    forecast_accuracy_rank,
                    peak_demand_rank,

                    contains_replay,
                    latest_kafka_timestamp

                from analytics.mart_balancing_authority_performance

                order by
                    peak_demand_rank,
                    respondent

                limit ?
                """,
                [
                    limit,
                ],
            )

    def ev_cities(
        self,
        *,
        state: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return EV charging infrastructure rankings."""

        query = """
            select
                city_state_key,

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

                state_station_rank,
                national_station_rank,
                state_port_rank,

                latest_station_update

            from analytics.mart_ev_city_rankings
        """

        parameters: list[Any] = []

        if state is not None:
            query += """
                where upper(state) = ?
            """

            parameters.append(state.upper())

        query += """
            order by
                national_station_rank,
                state,
                city

            limit ?
        """

        parameters.append(limit)

        with self.connect() as connection:
            return self._rows_to_dicts(
                connection,
                query,
                parameters,
            )

    def weather_forecasts(
        self,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return ordered hourly weather forecasts."""

        with self.connect() as connection:
            return self._rows_to_dicts(
                connection,
                """
                select
                    weather_forecast_key,
                    location_key,

                    latitude,
                    longitude,

                    period_start,
                    period_end,

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

                    kafka_partition,
                    kafka_offset,
                    kafka_timestamp

                from analytics.mart_weather_forecast

                order by
                    location_key,
                    period_start

                limit ?
                """,
                [
                    limit,
                ],
            )
