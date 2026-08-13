"""Historical regional grid drill-down for GridPulse."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

DEFAULT_DATABASE_PATH = Path("data/warehouse/gridpulse.duckdb")


@dataclass(frozen=True)
class RegionalHistoryPoint:
    """One historical regional grid observation."""

    period: str

    region: str
    region_name: str

    demand_mwh: float
    demand_forecast_mwh: float | None
    net_generation_mwh: float | None
    total_interchange_mwh: float | None

    demand_baseline_mwh: float | None

    demand_vs_baseline_pct: float | None
    demand_change_pct: float | None

    forecast_error_pct: float | None
    generation_gap_pct: float | None

    contains_replay: bool


def load_regional_history(
    database_path: Path = DEFAULT_DATABASE_PATH,
    region: str = "",
    hours: int = 168,
) -> list[RegionalHistoryPoint]:
    """Return recent history for one normalized EIA region."""

    normalized_region = region.strip().upper()

    if not normalized_region:
        return []

    connection = duckdb.connect(
        str(database_path),
        read_only=True,
    )

    try:
        rows = connection.execute(
            """
            WITH base AS (
                SELECT
                    period,

                    respondent,
                    COALESCE(
                        respondent_name,
                        respondent
                    ) AS respondent_name,

                    demand_mwh,
                    demand_forecast_mwh,
                    net_generation_mwh,
                    total_interchange_mwh,

                    ABS(
                        demand_forecast_error_pct
                    ) AS forecast_error_pct,

                    CASE
                        WHEN demand_mwh IS NOT NULL
                         AND demand_mwh > 0
                         AND generation_demand_gap_mwh IS NOT NULL
                        THEN
                            ABS(
                                generation_demand_gap_mwh
                                / demand_mwh
                            ) * 100
                    END AS generation_gap_pct,

                    contains_replay

                FROM analytics.mart_grid_hourly

                WHERE
                    entity_type = 'region'
                    AND respondent = ?
                    AND demand_mwh IS NOT NULL
                    AND demand_mwh > 0
            ),

            windowed AS (
                SELECT
                    *,

                    LAG(
                        demand_mwh
                    ) OVER (
                        ORDER BY period
                    ) AS previous_demand_mwh,

                    MEDIAN(
                        demand_mwh
                    ) OVER (
                        ORDER BY period
                        ROWS BETWEEN
                            UNBOUNDED PRECEDING
                            AND 1 PRECEDING
                    ) AS demand_baseline_mwh

                FROM base
            ),

            derived AS (
                SELECT
                    *,

                    CASE
                        WHEN demand_baseline_mwh IS NOT NULL
                         AND demand_baseline_mwh > 0
                        THEN
                            (
                                demand_mwh
                                - demand_baseline_mwh
                            )
                            * 100.0
                            / demand_baseline_mwh
                    END AS demand_vs_baseline_pct,

                    CASE
                        WHEN previous_demand_mwh IS NOT NULL
                         AND previous_demand_mwh > 0
                        THEN
                            (
                                demand_mwh
                                - previous_demand_mwh
                            )
                            * 100.0
                            / previous_demand_mwh
                    END AS demand_change_pct,

                    ROW_NUMBER() OVER (
                        ORDER BY period DESC
                    ) AS recency_rank

                FROM windowed
            )

            SELECT
                period,

                respondent,
                respondent_name,

                demand_mwh,
                demand_forecast_mwh,
                net_generation_mwh,
                total_interchange_mwh,

                demand_baseline_mwh,

                demand_vs_baseline_pct,
                demand_change_pct,

                forecast_error_pct,
                generation_gap_pct,

                contains_replay

            FROM derived

            WHERE recency_rank <= ?

            ORDER BY period
            """,
            [
                normalized_region,
                hours,
            ],
        ).fetchall()

    finally:
        connection.close()

    return [
        RegionalHistoryPoint(
            period=str(row[0]),
            region=row[1],
            region_name=row[2],
            demand_mwh=float(row[3]),
            demand_forecast_mwh=row[4],
            net_generation_mwh=row[5],
            total_interchange_mwh=row[6],
            demand_baseline_mwh=row[7],
            demand_vs_baseline_pct=row[8],
            demand_change_pct=row[9],
            forecast_error_pct=row[10],
            generation_gap_pct=row[11],
            contains_replay=bool(row[12]),
        )
        for row in rows
    ]
