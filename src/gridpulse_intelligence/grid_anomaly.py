"""Explainable historical grid anomaly intelligence for GridPulse."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

DEFAULT_DATABASE_PATH = Path("data/warehouse/gridpulse.duckdb")

MIN_HISTORY_POINTS = 24
MAX_DEVIATION_SCORE = 4.0

FORECAST_WEIGHT = 0.70
GENERATION_WEIGHT = 0.30


@dataclass(frozen=True)
class GridAnomaly:
    """Latest explainable historical anomaly score for one authority."""

    period: str
    respondent: str
    respondent_name: str

    demand_mwh: float | None
    demand_forecast_mwh: float | None

    forecast_error_pct: float | None
    generation_gap_pct: float | None

    history_points: int

    forecast_baseline_pct: float | None
    forecast_deviation_score: float

    generation_baseline_pct: float | None
    generation_deviation_score: float

    risk_score: float
    severity: str


def classify_severity(
    score: float,
) -> str:
    """Convert a displayed 0-100 risk score into severity."""

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


def load_grid_anomalies(
    database_path: Path = DEFAULT_DATABASE_PATH,
    limit: int = 100,
) -> list[GridAnomaly]:
    """Score each authority's latest observation against its own history."""

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
                    demand_forecast_error_pct,

                    ABS(
                        demand_forecast_error_pct
                    ) AS forecast_error_abs_pct,

                    CASE
                        WHEN demand_mwh IS NOT NULL
                         AND demand_mwh > 0
                         AND generation_demand_gap_mwh IS NOT NULL
                        THEN
                            ABS(
                                generation_demand_gap_mwh
                                / demand_mwh
                            ) * 100
                    END AS generation_gap_pct

                FROM analytics.mart_grid_hourly

                WHERE
                    demand_mwh IS NOT NULL
                    AND demand_mwh > 0
                    AND demand_forecast_mwh IS NOT NULL
                    AND demand_forecast_mwh > 0
                    AND demand_forecast_error_pct IS NOT NULL
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
                    demand_forecast_error_pct,

                    forecast_error_abs_pct,
                    generation_gap_pct

                FROM ordered

                WHERE observation_rank = 1
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
                        generation_gap_pct
                    ) AS generation_history_points,

                    AVG(
                        forecast_error_abs_pct
                    ) AS forecast_error_mean,

                    STDDEV_SAMP(
                        forecast_error_abs_pct
                    ) AS forecast_error_stddev,

                    MEDIAN(
                        forecast_error_abs_pct
                    ) AS forecast_error_median,

                    AVG(
                        generation_gap_pct
                    ) AS generation_gap_mean,

                    STDDEV_SAMP(
                        generation_gap_pct
                    ) AS generation_gap_stddev,

                    MEDIAN(
                        generation_gap_pct
                    ) AS generation_gap_median

                FROM history

                GROUP BY respondent
            ),

            historical_mad AS (
                SELECT
                    history.respondent,

                    MEDIAN(
                        ABS(
                            history.forecast_error_abs_pct
                            - stats.forecast_error_median
                        )
                    ) AS forecast_error_mad,

                    MEDIAN(
                        ABS(
                            history.generation_gap_pct
                            - stats.generation_gap_median
                        )
                    ) AS generation_gap_mad

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

                    latest.demand_forecast_error_pct,
                    latest.generation_gap_pct,

                    stats.history_points,

                    stats.forecast_error_median
                        AS forecast_baseline_pct,

                    stats.generation_gap_median
                        AS generation_baseline_pct,

                    CASE
                        WHEN stats.history_points < ?
                        THEN 0

                        WHEN mad.forecast_error_mad IS NOT NULL
                         AND mad.forecast_error_mad > 0
                        THEN
                            0.6745
                            * ABS(
                                latest.forecast_error_abs_pct
                                - stats.forecast_error_median
                            )
                            / mad.forecast_error_mad

                        WHEN stats.forecast_error_stddev IS NOT NULL
                         AND stats.forecast_error_stddev > 0
                        THEN
                            ABS(
                                latest.forecast_error_abs_pct
                                - stats.forecast_error_mean
                            )
                            / stats.forecast_error_stddev

                        ELSE 0
                    END AS forecast_error_z,

                    CASE
                        WHEN latest.generation_gap_pct IS NULL
                        THEN 0

                        WHEN stats.generation_history_points < ?
                        THEN 0

                        WHEN mad.generation_gap_mad IS NOT NULL
                         AND mad.generation_gap_mad > 0
                        THEN
                            0.6745
                            * ABS(
                                latest.generation_gap_pct
                                - stats.generation_gap_median
                            )
                            / mad.generation_gap_mad

                        WHEN stats.generation_gap_stddev IS NOT NULL
                         AND stats.generation_gap_stddev > 0
                        THEN
                            ABS(
                                latest.generation_gap_pct
                                - stats.generation_gap_mean
                            )
                            / stats.generation_gap_stddev

                        ELSE 0
                    END AS generation_gap_z

                FROM latest

                INNER JOIN historical_stats AS stats
                    ON latest.respondent
                        = stats.respondent

                INNER JOIN historical_mad AS mad
                    ON latest.respondent
                        = mad.respondent
            ),

            capped AS (
                SELECT
                    *,

                    LEAST(
                        forecast_error_z,
                        ?
                    ) AS forecast_deviation_score,

                    LEAST(
                        generation_gap_z,
                        ?
                    ) AS generation_deviation_score

                FROM normalized

                WHERE history_points >= ?
            ),

            scored AS (
                SELECT
                    period,
                    respondent,
                    respondent_name,

                    demand_mwh,
                    demand_forecast_mwh,

                    demand_forecast_error_pct,
                    generation_gap_pct,

                    history_points,

                    forecast_baseline_pct,
                    forecast_deviation_score,

                    generation_baseline_pct,
                    generation_deviation_score,

                    LEAST(
                        100.0,

                        25.0
                        * (
                            ?
                            * forecast_deviation_score

                            +

                            ?
                            * generation_deviation_score
                        )
                    ) AS risk_score

                FROM capped
            )

            SELECT
                period,
                respondent,
                respondent_name,

                demand_mwh,
                demand_forecast_mwh,

                demand_forecast_error_pct,
                generation_gap_pct,

                history_points,

                forecast_baseline_pct,
                forecast_deviation_score,

                generation_baseline_pct,
                generation_deviation_score,

                risk_score

            FROM scored

            ORDER BY
                risk_score DESC,
                period DESC,
                respondent

            LIMIT ?
            """,
            [
                MIN_HISTORY_POINTS,
                MIN_HISTORY_POINTS,
                MAX_DEVIATION_SCORE,
                MAX_DEVIATION_SCORE,
                MIN_HISTORY_POINTS,
                FORECAST_WEIGHT,
                GENERATION_WEIGHT,
                limit,
            ],
        ).fetchall()

    finally:
        connection.close()

    anomalies: list[GridAnomaly] = []

    for row in rows:
        risk_score = round(
            float(row[12] or 0),
            1,
        )

        anomalies.append(
            GridAnomaly(
                period=str(row[0]),
                respondent=row[1],
                respondent_name=row[2],
                demand_mwh=row[3],
                demand_forecast_mwh=row[4],
                forecast_error_pct=row[5],
                generation_gap_pct=row[6],
                history_points=int(row[7]),
                forecast_baseline_pct=row[8],
                forecast_deviation_score=round(
                    float(row[9] or 0),
                    2,
                ),
                generation_baseline_pct=row[10],
                generation_deviation_score=round(
                    float(row[11] or 0),
                    2,
                ),
                risk_score=risk_score,
                severity=classify_severity(risk_score),
            )
        )

    return anomalies


def main() -> None:
    """Display current explainable historical grid-risk signals."""

    anomalies = load_grid_anomalies(
        limit=20,
    )

    print()
    print("GRIDPULSE EXPLAINABLE HISTORICAL GRID RISK")
    print("=" * 115)

    if not anomalies:
        print("No authorities have enough historical observations for anomaly scoring.")

        return

    for anomaly in anomalies:
        forecast_error = (
            abs(anomaly.forecast_error_pct) if anomaly.forecast_error_pct is not None else 0
        )

        forecast_baseline = anomaly.forecast_baseline_pct or 0

        generation_gap = anomaly.generation_gap_pct or 0

        generation_baseline = anomaly.generation_baseline_pct or 0

        print(
            f"{anomaly.severity:10} "
            f"{anomaly.risk_score:6.1f}  "
            f"{anomaly.respondent:8} "
            f"{anomaly.respondent_name[:28]:28} "
            f"history={anomaly.history_points:3d}  "
            f"forecast={forecast_error:6.2f}%/"
            f"{forecast_baseline:6.2f}% "
            f"z={anomaly.forecast_deviation_score:4.2f}  "
            f"generation={generation_gap:7.2f}%/"
            f"{generation_baseline:7.2f}% "
            f"z={anomaly.generation_deviation_score:4.2f}"
        )


if __name__ == "__main__":
    main()
