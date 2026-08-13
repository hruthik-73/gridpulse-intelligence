"""Tests for GridPulse regional grid-pressure intelligence."""

from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pytest

from gridpulse_intelligence.regional_grid import (
    classify_pressure,
    load_regional_grid_signals,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, "NORMAL"),
        (54.94, "NORMAL"),
        (54.96, "ELEVATED"),
        (55.0, "ELEVATED"),
        (74.9, "ELEVATED"),
        (75.0, "HIGH"),
        (89.9, "HIGH"),
        (90.0, "CRITICAL"),
        (100.0, "CRITICAL"),
    ],
)
def test_classify_pressure(
    score: float,
    expected: str,
) -> None:
    """Displayed pressure thresholds should map correctly."""

    assert classify_pressure(score) == expected


def create_schema(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    """Create the minimal hourly mart used by regional tests."""

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
            generation_demand_gap_mwh DOUBLE
        )
        """
    )


def insert_region_history(
    connection: duckdb.DuckDBPyConnection,
    region: str,
    region_name: str,
    latest_demand: float,
    latest_forecast_error_pct: float,
    latest_generation_gap_mwh: float,
    history_points: int = 30,
) -> None:
    """Insert historical regional observations plus a latest point."""

    start = datetime(
        2026,
        7,
        1,
    )

    rows: list[
        tuple[
            datetime,
            str,
            str,
            str,
            float,
            float,
            float,
            float,
            float,
            float,
        ]
    ] = []

    for index in range(history_points):
        demand = float(980 + (index % 5) * 10)

        forecast_error_pct = float(1 + (index % 3))

        generation_gap = float(20 + (index % 3) * 10)

        rows.append(
            (
                start
                + timedelta(
                    hours=index,
                ),
                region,
                region_name,
                "region",
                demand,
                demand / (1 + forecast_error_pct / 100),
                demand + generation_gap,
                0.0,
                forecast_error_pct,
                generation_gap,
            )
        )

    rows.append(
        (
            start
            + timedelta(
                hours=history_points,
            ),
            region,
            region_name,
            "region",
            latest_demand,
            latest_demand / (1 + latest_forecast_error_pct / 100),
            latest_demand + latest_generation_gap_mwh,
            0.0,
            latest_forecast_error_pct,
            latest_generation_gap_mwh,
        )
    )

    connection.executemany(
        """
        INSERT INTO analytics.mart_grid_hourly
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def create_test_database(
    database_path: Path,
) -> None:
    """Create regional, BA, and short-history examples."""

    connection = duckdb.connect(str(database_path))

    try:
        create_schema(connection)

        insert_region_history(
            connection=connection,
            region="SPIKE",
            region_name="High Pressure Region",
            latest_demand=1700.0,
            latest_forecast_error_pct=30.0,
            latest_generation_gap_mwh=900.0,
        )

        insert_region_history(
            connection=connection,
            region="STABLE",
            region_name="Stable Region",
            latest_demand=1000.0,
            latest_forecast_error_pct=2.0,
            latest_generation_gap_mwh=30.0,
        )

        insert_region_history(
            connection=connection,
            region="SHORT",
            region_name="Short Region",
            latest_demand=1800.0,
            latest_forecast_error_pct=50.0,
            latest_generation_gap_mwh=1000.0,
            history_points=5,
        )

        connection.execute(
            """
            INSERT INTO analytics.mart_grid_hourly
            VALUES (
                '2026-07-02 12:00:00',
                'TVA',
                'Tennessee Valley Authority',
                'balancing_authority',
                20000,
                19500,
                19800,
                0,
                2.5,
                -200
            )
            """
        )

    finally:
        connection.close()


def test_high_pressure_region_ranks_first(
    tmp_path: Path,
) -> None:
    """A major regional load deviation should rank first."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    signals = load_regional_grid_signals(
        database_path=database_path,
        limit=10,
    )

    assert signals

    spike = signals[0]

    assert spike.region == "SPIKE"

    assert spike.pressure_score >= 90

    assert spike.severity == "CRITICAL"

    assert spike.history_points == 30

    assert spike.demand_vs_baseline_pct > 50

    assert spike.demand_deviation_score == pytest.approx(4.0)


def test_stable_region_remains_normal(
    tmp_path: Path,
) -> None:
    """A region close to its normal historical load should stay normal."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    signals = load_regional_grid_signals(
        database_path=database_path,
        limit=10,
    )

    stable = next(signal for signal in signals if signal.region == "STABLE")

    assert stable.pressure_score < 55

    assert stable.severity == "NORMAL"

    assert abs(stable.demand_vs_baseline_pct) < 5


def test_balancing_authorities_are_excluded(
    tmp_path: Path,
) -> None:
    """Regional intelligence must not include BA observations."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    signals = load_regional_grid_signals(
        database_path=database_path,
        limit=10,
    )

    regions = {signal.region for signal in signals}

    assert "TVA" not in regions


def test_short_history_region_is_excluded(
    tmp_path: Path,
) -> None:
    """Regions require enough historical observations before scoring."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    signals = load_regional_grid_signals(
        database_path=database_path,
        limit=10,
    )

    regions = {signal.region for signal in signals}

    assert "SHORT" not in regions


def test_limit_is_respected(
    tmp_path: Path,
) -> None:
    """Requested result limit should be respected."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    signals = load_regional_grid_signals(
        database_path=database_path,
        limit=1,
    )

    assert len(signals) == 1

    assert signals[0].region == "SPIKE"
