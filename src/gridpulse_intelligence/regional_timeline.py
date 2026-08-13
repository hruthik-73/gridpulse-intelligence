"""Historical regional pressure timeline for GridPulse."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean, median, stdev
from typing import Any

import duckdb

from gridpulse_intelligence.deployment_config import get_database_path
from gridpulse_intelligence.regional_grid import (
    DEMAND_WEIGHT,
    FORECAST_WEIGHT,
    GENERATION_WEIGHT,
    MAX_DEVIATION_SCORE,
    MIN_HISTORY_POINTS,
    classify_pressure,
)

DEFAULT_DATABASE_PATH = get_database_path()


@dataclass(frozen=True)
class RegionalTimelinePoint:
    """One historically scored regional grid observation."""

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

    contains_replay: bool


def _robust_deviation(
    current: float | None,
    history: list[float],
    *,
    high_only: bool = False,
) -> float:
    """Return a capped robust historical deviation score."""

    if current is None or len(history) < MIN_HISTORY_POINTS:
        return 0.0

    baseline = median(history)

    if high_only and current <= baseline:
        return 0.0

    difference = current - baseline if high_only else abs(current - baseline)

    absolute_deviations = [abs(value - baseline) for value in history]

    mad = median(absolute_deviations)

    if mad > 0:
        score = 0.6745 * difference / mad

    elif len(history) > 1:
        deviation = stdev(history)

        if deviation <= 0:
            return 0.0

        average = fmean(history)

        score = (current - average) / deviation if high_only else abs(current - average) / deviation

    else:
        return 0.0

    return min(
        MAX_DEVIATION_SCORE,
        max(
            0.0,
            score,
        ),
    )


def _generation_gap_pct(
    demand_mwh: float,
    generation_gap_mwh: float | None,
) -> float | None:
    """Convert generation-demand gap into absolute percent."""

    if demand_mwh <= 0 or generation_gap_mwh is None:
        return None

    return abs(generation_gap_mwh / demand_mwh) * 100


def load_regional_timeline(
    database_path: Path = DEFAULT_DATABASE_PATH,
    hours: int = 168,
) -> list[RegionalTimelinePoint]:
    """Build historically scored observations across all EIA regions."""

    connection = duckdb.connect(
        str(database_path),
        read_only=True,
    )

    try:
        rows = connection.execute(
            """
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

                demand_forecast_error_pct,
                generation_demand_gap_mwh,

                contains_replay

            FROM analytics.mart_grid_hourly

            WHERE
                entity_type = 'region'
                AND demand_mwh IS NOT NULL
                AND demand_mwh > 0

            ORDER BY
                respondent,
                period
            """
        ).fetchall()

    finally:
        connection.close()

    grouped: dict[
        str,
        list[tuple[Any, ...]],
    ] = defaultdict(list)

    for row in rows:
        grouped[str(row[1])].append(row)

    timeline: list[RegionalTimelinePoint] = []

    for region_rows in grouped.values():
        scored_region: list[RegionalTimelinePoint] = []

        demand_history: list[float] = []

        forecast_history: list[float] = []

        generation_history: list[float] = []

        previous_demand: float | None = None

        for row in region_rows:
            demand = float(row[3])

            forecast_error = abs(float(row[7])) if row[7] is not None else None

            generation_gap = _generation_gap_pct(
                demand,
                (float(row[8]) if row[8] is not None else None),
            )

            if len(demand_history) >= MIN_HISTORY_POINTS:
                demand_baseline = float(median(demand_history))

                demand_vs_baseline = (
                    (demand - demand_baseline) * 100.0 / demand_baseline
                    if demand_baseline > 0
                    else 0.0
                )

                demand_change = (
                    (demand - previous_demand) * 100.0 / previous_demand
                    if (previous_demand is not None and previous_demand > 0)
                    else None
                )

                demand_score = _robust_deviation(
                    demand,
                    demand_history,
                    high_only=True,
                )

                forecast_score = _robust_deviation(
                    forecast_error,
                    forecast_history,
                )

                generation_score = _robust_deviation(
                    generation_gap,
                    generation_history,
                )

                pressure_score = round(
                    min(
                        100.0,
                        25.0
                        * (
                            DEMAND_WEIGHT * demand_score
                            + FORECAST_WEIGHT * forecast_score
                            + GENERATION_WEIGHT * generation_score
                        ),
                    ),
                    1,
                )

                scored_region.append(
                    RegionalTimelinePoint(
                        period=str(row[0]),
                        region=str(row[1]),
                        region_name=str(row[2]),
                        demand_mwh=demand,
                        demand_forecast_mwh=(float(row[4]) if row[4] is not None else None),
                        net_generation_mwh=(float(row[5]) if row[5] is not None else None),
                        total_interchange_mwh=(float(row[6]) if row[6] is not None else None),
                        demand_baseline_mwh=round(
                            demand_baseline,
                            2,
                        ),
                        demand_vs_baseline_pct=round(
                            demand_vs_baseline,
                            2,
                        ),
                        demand_change_pct=(
                            round(
                                demand_change,
                                2,
                            )
                            if demand_change is not None
                            else None
                        ),
                        forecast_error_pct=forecast_error,
                        generation_gap_pct=generation_gap,
                        history_points=len(demand_history),
                        demand_deviation_score=round(
                            demand_score,
                            2,
                        ),
                        forecast_deviation_score=round(
                            forecast_score,
                            2,
                        ),
                        generation_deviation_score=round(
                            generation_score,
                            2,
                        ),
                        pressure_score=pressure_score,
                        severity=classify_pressure(pressure_score),
                        contains_replay=bool(row[9]),
                    )
                )

            demand_history.append(demand)

            if forecast_error is not None:
                forecast_history.append(forecast_error)

            if generation_gap is not None:
                generation_history.append(generation_gap)

            previous_demand = demand

        timeline.extend(scored_region[-hours:])

    return sorted(
        timeline,
        key=lambda point: (
            point.period,
            point.region,
        ),
    )
