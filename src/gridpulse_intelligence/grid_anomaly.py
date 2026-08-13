"""Grid risk intelligence for GridPulse."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

DEFAULT_DATABASE_PATH = Path("data/warehouse/gridpulse.duckdb")


@dataclass(frozen=True)
class GridAnomaly:
    """One scored balancing-authority observation."""

    period: str
    respondent: str
    respondent_name: str
    demand_mwh: float | None
    demand_forecast_mwh: float | None
    forecast_error_pct: float | None
    generation_gap_pct: float | None
    risk_score: float
    severity: str


def classify_severity(score: float) -> str:
    """Convert a 0-100 risk score into a severity."""

    if score >= 90:
        return "CRITICAL"

    if score >= 75:
        return "HIGH"

    if score >= 55:
        return "ELEVATED"

    return "NORMAL"


def load_grid_anomalies(
    database_path: Path = DEFAULT_DATABASE_PATH,
    limit: int = 100,
) -> list[GridAnomaly]:
    """Calculate peer-relative grid risk scores."""

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
                    respondent_name,
                    demand_mwh,
                    demand_forecast_mwh,
                    demand_forecast_error_pct,

                    CASE
                        WHEN demand_mwh IS NOT NULL
                         AND demand_mwh != 0
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
                    AND demand_forecast_mwh IS NOT NULL
                    AND demand_mwh > 0
                    AND demand_forecast_mwh > 0
            ),

            ranked AS (
                SELECT
                    *,

                    PERCENT_RANK() OVER (
                        ORDER BY ABS(demand_forecast_error_pct)
                    ) AS forecast_error_rank,

                    PERCENT_RANK() OVER (
                        ORDER BY COALESCE(generation_gap_pct, 0)
                    ) AS generation_gap_rank

                FROM base
            ),

            scored AS (
                SELECT
                    *,

                    (
                        forecast_error_rank * 0.70
                        +
                        generation_gap_rank * 0.30
                    ) * 100 AS risk_score

                FROM ranked
            )

            SELECT
                period,
                respondent,
                respondent_name,
                demand_mwh,
                demand_forecast_mwh,
                demand_forecast_error_pct,
                generation_gap_pct,
                risk_score

            FROM scored

            ORDER BY
                risk_score DESC,
                period DESC

            LIMIT ?
            """,
            [limit],
        ).fetchall()

    finally:
        connection.close()

    return [
        GridAnomaly(
            period=str(row[0]),
            respondent=row[1],
            respondent_name=row[2],
            demand_mwh=row[3],
            demand_forecast_mwh=row[4],
            forecast_error_pct=row[5],
            generation_gap_pct=row[6],
            risk_score=float(row[7] or 0),
            severity=classify_severity(float(row[7] or 0)),
        )
        for row in rows
    ]


def main() -> None:
    """Display highest GridPulse risk observations."""

    anomalies = load_grid_anomalies(limit=20)

    print()
    print("GRIDPULSE GRID RISK INTELLIGENCE")
    print("=" * 90)

    for anomaly in anomalies:
        forecast_error = (
            abs(anomaly.forecast_error_pct) if anomaly.forecast_error_pct is not None else 0
        )

        print(
            f"{anomaly.severity:10} "
            f"{anomaly.risk_score:6.1f}  "
            f"{anomaly.respondent:8} "
            f"{anomaly.respondent_name[:32]:32} "
            f"forecast error={forecast_error:7.2f}%  "
            f"generation gap={anomaly.generation_gap_pct or 0:7.2f}%"
        )


if __name__ == "__main__":
    main()
