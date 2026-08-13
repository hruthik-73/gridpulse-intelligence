"""Historical regional grid-pressure intelligence for GridPulse."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

DEFAULT_DATABASE_PATH = Path("data/warehouse/gridpulse.duckdb")

MIN_HISTORY_POINTS = 24
MAX_DEVIATION_SCORE = 4.0

DEMAND_WEIGHT = 0.50
FORECAST_WEIGHT = 0.30
GENERATION_WEIGHT = 0.20


@dataclass(frozen=True)
class RegionalGridSignal:
    """Latest explainable grid-pressure signal for one EIA region."""

    period: str

    region: str
    region_name: str

    demand_mwh: float
    demand_forecast_mwh: float | None
    net_generation_mwh: float | None
    total_interchange_mwh: float | None

    demand_baseline_mwh: float

    demand_vs_baseline_pct: float
    demand_change_pct: float | None

    forecast_error_pct: float | None
    generation_gap_pct: float | None

    history_points: int

    demand_deviation_score: float
    forecast_deviation_score: float
    generation_deviation_score: float

    pressure_score: float
    severity: str


def classify_pressure(
    score: float,
) -> str:
    """Convert a displayed pressure score into a severity level."""

    normalized_score = round(
        score,
        1,
    )

    if normalized_score >= 90:
        return "CRITICAL"

    if normalized_score >= 75:
        return "HIGH"

    if normalized_score >= 55:
        return "ELEVATED"

    return "NORMAL"


def load_regional_grid_signals(
    database_path: Path = DEFAULT_DATABASE_PATH,
    limit: int = 25,
) -> list[RegionalGridSignal]:
    """Score each EIA region's latest load state against its own history."""

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
                    ) AS forecast_error_abs_pct,

                    CASE
                        WHEN demand_mwh > 0
                         AND generation_demand_gap_mwh IS NOT NULL
                        THEN
                            ABS(
                                generation_demand_gap_mwh
                                / demand_mwh
                            ) * 100
                    END AS generation_gap_pct

                FROM analytics.mart_grid_hourly

                WHERE
                    entity_type = 'region'
                    AND demand_mwh IS NOT NULL
                    AND demand_mwh > 0
            ),

            ordered AS (
                SELECT
                    *,

                    ROW_NUMBER() OVER (
                        PARTITION BY respondent
                        ORDER BY period DESC
                    ) AS observation_rank

                FROM base
            ),

            latest AS (
                SELECT
                    period,
                    respondent,
                    respondent_name,

                    demand_mwh,
                    demand_forecast_mwh,
                    net_generation_mwh,
                    total_interchange_mwh,

                    forecast_error_abs_pct,
                    generation_gap_pct

                FROM ordered

                WHERE observation_rank = 1
            ),

            previous AS (
                SELECT
                    respondent,
                    demand_mwh
                        AS previous_demand_mwh

                FROM ordered

                WHERE observation_rank = 2
            ),

            history AS (
                SELECT
                    historical.*

                FROM base AS historical

                INNER JOIN latest
                    ON historical.respondent
                        = latest.respondent
                   AND historical.period
                        < latest.period
            ),

            historical_stats AS (
                SELECT
                    respondent,

                    COUNT(*) AS history_points,

                    COUNT(
                        forecast_error_abs_pct
                    ) AS forecast_history_points,

                    COUNT(
                        generation_gap_pct
                    ) AS generation_history_points,

                    AVG(
                        demand_mwh
                    ) AS demand_mean,

                    STDDEV_SAMP(
                        demand_mwh
                    ) AS demand_stddev,

                    MEDIAN(
                        demand_mwh
                    ) AS demand_median,

                    AVG(
                        forecast_error_abs_pct
                    ) AS forecast_mean,

                    STDDEV_SAMP(
                        forecast_error_abs_pct
                    ) AS forecast_stddev,

                    MEDIAN(
                        forecast_error_abs_pct
                    ) AS forecast_median,

                    AVG(
                        generation_gap_pct
                    ) AS generation_mean,

                    STDDEV_SAMP(
                        generation_gap_pct
                    ) AS generation_stddev,

                    MEDIAN(
                        generation_gap_pct
                    ) AS generation_median

                FROM history

                GROUP BY respondent
            ),

            historical_mad AS (
                SELECT
                    history.respondent,

                    MEDIAN(
                        ABS(
                            history.demand_mwh
                            - stats.demand_median
                        )
                    ) AS demand_mad,

                    MEDIAN(
                        ABS(
                            history.forecast_error_abs_pct
                            - stats.forecast_median
                        )
                    ) AS forecast_mad,

                    MEDIAN(
                        ABS(
                            history.generation_gap_pct
                            - stats.generation_median
                        )
                    ) AS generation_mad

                FROM history

                INNER JOIN historical_stats AS stats
                    ON history.respondent
                        = stats.respondent

                GROUP BY history.respondent
            ),

            normalized AS (
                SELECT
                    latest.period,

                    latest.respondent,
                    latest.respondent_name,

                    latest.demand_mwh,
                    latest.demand_forecast_mwh,
                    latest.net_generation_mwh,
                    latest.total_interchange_mwh,

                    stats.demand_median
                        AS demand_baseline_mwh,

                    (
                        latest.demand_mwh
                        - stats.demand_median
                    )
                    * 100.0
                    / NULLIF(
                        stats.demand_median,
                        0
                    ) AS demand_vs_baseline_pct,

                    CASE
                        WHEN previous.previous_demand_mwh IS NOT NULL
                         AND previous.previous_demand_mwh > 0
                        THEN
                            (
                                latest.demand_mwh
                                - previous.previous_demand_mwh
                            )
                            * 100.0
                            / previous.previous_demand_mwh
                    END AS demand_change_pct,

                    latest.forecast_error_abs_pct,
                    latest.generation_gap_pct,

                    stats.history_points,

                    CASE
                        WHEN latest.demand_mwh
                            <= stats.demand_median
                        THEN 0

                        WHEN mad.demand_mad IS NOT NULL
                         AND mad.demand_mad > 0
                        THEN
                            0.6745
                            * (
                                latest.demand_mwh
                                - stats.demand_median
                            )
                            / mad.demand_mad

                        WHEN stats.demand_stddev IS NOT NULL
                         AND stats.demand_stddev > 0
                        THEN
                            (
                                latest.demand_mwh
                                - stats.demand_mean
                            )
                            / stats.demand_stddev

                        ELSE 0
                    END AS demand_z,

                    CASE
                        WHEN latest.forecast_error_abs_pct IS NULL
                        THEN 0

                        WHEN stats.forecast_history_points
                            < ?
                        THEN 0

                        WHEN mad.forecast_mad IS NOT NULL
                         AND mad.forecast_mad > 0
                        THEN
                            0.6745
                            * ABS(
                                latest.forecast_error_abs_pct
                                - stats.forecast_median
                            )
                            / mad.forecast_mad

                        WHEN stats.forecast_stddev IS NOT NULL
                         AND stats.forecast_stddev > 0
                        THEN
                            ABS(
                                latest.forecast_error_abs_pct
                                - stats.forecast_mean
                            )
                            / stats.forecast_stddev

                        ELSE 0
                    END AS forecast_z,

                    CASE
                        WHEN latest.generation_gap_pct IS NULL
                        THEN 0

                        WHEN stats.generation_history_points
                            < ?
                        THEN 0

                        WHEN mad.generation_mad IS NOT NULL
                         AND mad.generation_mad > 0
                        THEN
                            0.6745
                            * ABS(
                                latest.generation_gap_pct
                                - stats.generation_median
                            )
                            / mad.generation_mad

                        WHEN stats.generation_stddev IS NOT NULL
                         AND stats.generation_stddev > 0
                        THEN
                            ABS(
                                latest.generation_gap_pct
                                - stats.generation_mean
                            )
                            / stats.generation_stddev

                        ELSE 0
                    END AS generation_z

                FROM latest

                INNER JOIN historical_stats AS stats
                    ON latest.respondent
                        = stats.respondent

                INNER JOIN historical_mad AS mad
                    ON latest.respondent
                        = mad.respondent

                LEFT JOIN previous
                    ON latest.respondent
                        = previous.respondent

                WHERE
                    stats.history_points >= ?
            ),

            scored AS (
                SELECT
                    *,

                    LEAST(
                        demand_z,
                        ?
                    ) AS demand_deviation_score,

                    LEAST(
                        forecast_z,
                        ?
                    ) AS forecast_deviation_score,

                    LEAST(
                        generation_z,
                        ?
                    ) AS generation_deviation_score

                FROM normalized
            ),

            pressure AS (
                SELECT
                    *,

                    LEAST(
                        100.0,

                        25.0
                        * (
                            ?
                            * demand_deviation_score

                            +

                            ?
                            * forecast_deviation_score

                            +

                            ?
                            * generation_deviation_score
                        )
                    ) AS pressure_score

                FROM scored
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

                forecast_error_abs_pct,
                generation_gap_pct,

                history_points,

                demand_deviation_score,
                forecast_deviation_score,
                generation_deviation_score,

                pressure_score

            FROM pressure

            ORDER BY
                pressure_score DESC,
                demand_vs_baseline_pct DESC,
                respondent

            LIMIT ?
            """,
            [
                MIN_HISTORY_POINTS,
                MIN_HISTORY_POINTS,
                MIN_HISTORY_POINTS,
                MAX_DEVIATION_SCORE,
                MAX_DEVIATION_SCORE,
                MAX_DEVIATION_SCORE,
                DEMAND_WEIGHT,
                FORECAST_WEIGHT,
                GENERATION_WEIGHT,
                limit,
            ],
        ).fetchall()

    finally:
        connection.close()

    signals: list[RegionalGridSignal] = []

    for row in rows:
        pressure_score = round(
            float(row[16] or 0),
            1,
        )

        signals.append(
            RegionalGridSignal(
                period=str(row[0]),
                region=row[1],
                region_name=row[2],
                demand_mwh=float(row[3]),
                demand_forecast_mwh=row[4],
                net_generation_mwh=row[5],
                total_interchange_mwh=row[6],
                demand_baseline_mwh=float(row[7]),
                demand_vs_baseline_pct=round(
                    float(row[8] or 0),
                    2,
                ),
                demand_change_pct=(
                    round(
                        float(row[9]),
                        2,
                    )
                    if row[9] is not None
                    else None
                ),
                forecast_error_pct=row[10],
                generation_gap_pct=row[11],
                history_points=int(row[12]),
                demand_deviation_score=round(
                    float(row[13] or 0),
                    2,
                ),
                forecast_deviation_score=round(
                    float(row[14] or 0),
                    2,
                ),
                generation_deviation_score=round(
                    float(row[15] or 0),
                    2,
                ),
                pressure_score=pressure_score,
                severity=classify_pressure(pressure_score),
            )
        )

    return signals


def main() -> None:
    """Display current regional grid-pressure intelligence."""

    signals = load_regional_grid_signals(
        limit=25,
    )

    print()
    print("GRIDPULSE REGIONAL GRID INTELLIGENCE")
    print("=" * 118)

    if not signals:
        print("No regions have enough historical observations for pressure scoring.")

        return

    for signal in signals:
        demand_change = (
            f"{signal.demand_change_pct:+6.2f}%"
            if signal.demand_change_pct is not None
            else "     —"
        )

        forecast_error = signal.forecast_error_pct or 0

        generation_gap = signal.generation_gap_pct or 0

        print(
            f"{signal.severity:10} "
            f"{signal.pressure_score:6.1f}  "
            f"{signal.region:6} "
            f"{signal.region_name[:20]:20} "
            f"demand={signal.demand_mwh:10.0f} "
            f"baseline={signal.demand_baseline_mwh:10.0f} "
            f"vs_base={signal.demand_vs_baseline_pct:+7.2f}% "
            f"1h={demand_change} "
            f"forecast={forecast_error:7.2f}% "
            f"gen_gap={generation_gap:7.2f}% "
            f"history={signal.history_points:3d}"
        )


if __name__ == "__main__":
    main()
