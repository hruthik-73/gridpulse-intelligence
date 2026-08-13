"""Tests for GridPulse regional pressure timeline."""

from datetime import datetime, timedelta
from pathlib import Path

import duckdb

from gridpulse_intelligence.regional_timeline import (
    load_regional_timeline,
)


def create_database(
    database_path: Path,
) -> None:
    """Create regional history with one final pressure spike."""

    connection = duckdb.connect(str(database_path))

    try:
        connection.execute(
            """
            CREATE SCHEMA analytics
            """
        )

        connection.execute(
            """
            CREATE TABLE analytics.mart_grid_hourly (
                period TIMESTAMP,

                respondent VARCHAR,
                respondent_name VARCHAR,
                entity_type VARCHAR,

                demand_mwh DOUBLE,
                demand_forecast_mwh DOUBLE,
                net_generation_mwh DOUBLE,
                total_interchange_mwh DOUBLE,

                demand_forecast_error_pct DOUBLE,
                generation_demand_gap_mwh DOUBLE,

                contains_replay BOOLEAN
            )
            """
        )

        start = datetime(
            2026,
            7,
            1,
        )

        rows = []

        for index in range(40):
            demand = float(980 + (index % 5) * 10)

            rows.append(
                (
                    start
                    + timedelta(
                        hours=index,
                    ),
                    "TEN",
                    "Tennessee",
                    "region",
                    demand,
                    demand - 20,
                    demand + 30,
                    0.0,
                    float(1 + index % 3),
                    30.0,
                    True,
                )
            )

        rows.append(
            (
                start
                + timedelta(
                    hours=40,
                ),
                "TEN",
                "Tennessee",
                "region",
                1700.0,
                1250.0,
                2600.0,
                0.0,
                30.0,
                900.0,
                True,
            )
        )

        connection.executemany(
            """
            INSERT INTO analytics.mart_grid_hourly
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            """,
            rows,
        )

        connection.execute(
            """
            INSERT INTO analytics.mart_grid_hourly
            VALUES (
                '2026-07-02 12:00:00',

                'TVA',
                'Tennessee Valley Authority',
                'balancing_authority',

                25000,
                24500,
                24700,
                0,

                2.0,
                -300,

                TRUE
            )
            """
        )

    finally:
        connection.close()


def test_timeline_contains_only_regions(
    tmp_path: Path,
) -> None:
    """Balancing-authority rows must not appear."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_database(database_path)

    timeline = load_regional_timeline(
        database_path=database_path,
        hours=168,
    )

    assert timeline

    assert all(point.region == "TEN" for point in timeline)


def test_timeline_is_chronological(
    tmp_path: Path,
) -> None:
    """Timeline observations should be chronological."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_database(database_path)

    timeline = load_regional_timeline(
        database_path=database_path,
        hours=168,
    )

    periods = [point.period for point in timeline]

    assert periods == sorted(periods)


def test_pressure_spike_scores_critical(
    tmp_path: Path,
) -> None:
    """A large late load and imbalance spike should become critical."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_database(database_path)

    timeline = load_regional_timeline(
        database_path=database_path,
        hours=168,
    )

    latest = timeline[-1]

    assert latest.pressure_score >= 90

    assert latest.severity == "CRITICAL"

    assert latest.demand_deviation_score == 4.0


def test_timeline_uses_prior_history(
    tmp_path: Path,
) -> None:
    """Scoring should begin only after sufficient prior history exists."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_database(database_path)

    timeline = load_regional_timeline(
        database_path=database_path,
        hours=168,
    )

    assert timeline[0].history_points >= 24
