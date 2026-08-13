"""Tests for GridPulse regional historical drill-down."""

from datetime import datetime, timedelta
from pathlib import Path

import duckdb

from gridpulse_intelligence.regional_history import (
    load_regional_history,
)


def create_database(
    database_path: Path,
) -> None:
    """Create a minimal normalized GridPulse mart."""

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
            demand = float(1000 + index * 10)

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
                    2.0,
                    30.0,
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
                '2026-07-01 10:00:00',
                'TVA',
                'Tennessee Valley Authority',
                'balancing_authority',
                25000,
                24500,
                24700,
                0,
                2,
                -300,
                TRUE
            )
            """
        )

    finally:
        connection.close()


def test_regional_history_returns_requested_region(
    tmp_path: Path,
) -> None:
    """History should contain only the requested regional entity."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_database(database_path)

    history = load_regional_history(
        database_path=database_path,
        region="TEN",
        hours=24,
    )

    assert len(history) == 24

    assert all(point.region == "TEN" for point in history)


def test_regional_history_is_chronological(
    tmp_path: Path,
) -> None:
    """Returned observations should be ordered oldest to newest."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_database(database_path)

    history = load_regional_history(
        database_path=database_path,
        region="TEN",
        hours=24,
    )

    periods = [point.period for point in history]

    assert periods == sorted(periods)


def test_regional_history_has_baselines(
    tmp_path: Path,
) -> None:
    """Recent observations should contain historical demand baselines."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_database(database_path)

    history = load_regional_history(
        database_path=database_path,
        region="TEN",
        hours=24,
    )

    assert history[-1].demand_baseline_mwh is not None

    assert history[-1].demand_vs_baseline_pct is not None

    assert history[-1].demand_change_pct is not None


def test_balancing_authority_is_not_returned_as_region(
    tmp_path: Path,
) -> None:
    """BA observations must remain outside regional history."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_database(database_path)

    history = load_regional_history(
        database_path=database_path,
        region="TVA",
        hours=24,
    )

    assert history == []
