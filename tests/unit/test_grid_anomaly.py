"""Tests for historical GridPulse grid-risk intelligence."""

from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pytest

from gridpulse_intelligence.grid_anomaly import (
    classify_severity,
    load_grid_anomalies,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, "NORMAL"),
        (54.9, "NORMAL"),
        (55.0, "ELEVATED"),
        (74.9, "ELEVATED"),
        (75.0, "HIGH"),
        (89.9, "HIGH"),
        (90.0, "CRITICAL"),
        (100.0, "CRITICAL"),
    ],
)
def test_classify_severity(
    score: float,
    expected: str,
) -> None:
    """Risk-score thresholds should map correctly."""

    assert classify_severity(score) == expected


def create_schema(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    """Create the minimal Grid mart used by anomaly tests."""

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
            demand_mwh DOUBLE,
            demand_forecast_mwh DOUBLE,
            demand_forecast_error_pct DOUBLE,
            generation_demand_gap_mwh DOUBLE
        )
        """
    )


def insert_history(
    connection: duckdb.DuckDBPyConnection,
    respondent: str,
    respondent_name: str,
    latest_forecast_error_pct: float,
    latest_generation_gap_mwh: float,
    history_points: int = 30,
) -> None:
    """Insert historical observations followed by one latest observation."""

    start = datetime(
        2026,
        7,
        1,
        0,
        0,
    )

    rows: list[
        tuple[
            datetime,
            str,
            str,
            float,
            float,
            float,
            float,
        ]
    ] = []

    for index in range(history_points):
        demand = 1000.0

        forecast_error_pct = float(1 + (index % 3))

        forecast = demand / (1 + (forecast_error_pct / 100))

        generation_gap_mwh = float(20 + (index % 3) * 10)

        rows.append(
            (
                start
                + timedelta(
                    hours=index,
                ),
                respondent,
                respondent_name,
                demand,
                forecast,
                forecast_error_pct,
                generation_gap_mwh,
            )
        )

    latest_period = start + timedelta(
        hours=history_points,
    )

    rows.append(
        (
            latest_period,
            respondent,
            respondent_name,
            1000.0,
            900.0,
            latest_forecast_error_pct,
            latest_generation_gap_mwh,
        )
    )

    connection.executemany(
        """
        INSERT INTO analytics.mart_grid_hourly
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def create_test_database(
    database_path: Path,
) -> None:
    """Create authorities with stable and anomalous histories."""

    connection = duckdb.connect(str(database_path))

    try:
        create_schema(connection)

        insert_history(
            connection=connection,
            respondent="STABLE",
            respondent_name=("Stable Authority"),
            latest_forecast_error_pct=2.0,
            latest_generation_gap_mwh=30.0,
        )

        insert_history(
            connection=connection,
            respondent="SPIKE",
            respondent_name=("Spike Authority"),
            latest_forecast_error_pct=40.0,
            latest_generation_gap_mwh=800.0,
        )

        insert_history(
            connection=connection,
            respondent="ELEV",
            respondent_name=("Elevated Authority"),
            latest_forecast_error_pct=5.5,
            latest_generation_gap_mwh=65.0,
        )

        insert_history(
            connection=connection,
            respondent="SHORT",
            respondent_name=("Insufficient History Authority"),
            latest_forecast_error_pct=80.0,
            latest_generation_gap_mwh=900.0,
            history_points=5,
        )

    finally:
        connection.close()


def test_historical_model_ranks_spike_first(
    tmp_path: Path,
) -> None:
    """A large deviation from personal history should rank first."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    anomalies = load_grid_anomalies(
        database_path=database_path,
        limit=10,
    )

    assert anomalies

    assert anomalies[0].respondent == "SPIKE"

    assert anomalies[0].risk_score >= 90

    assert anomalies[0].severity == "CRITICAL"


def test_stable_authority_remains_normal(
    tmp_path: Path,
) -> None:
    """An observation close to its history should remain normal."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    anomalies = load_grid_anomalies(
        database_path=database_path,
        limit=10,
    )

    stable = next(anomaly for anomaly in anomalies if anomaly.respondent == "STABLE")

    assert stable.risk_score < 55

    assert stable.severity == "NORMAL"


def test_insufficient_history_is_excluded(
    tmp_path: Path,
) -> None:
    """Authorities without enough baseline history should not be scored."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    anomalies = load_grid_anomalies(
        database_path=database_path,
        limit=10,
    )

    respondents = {anomaly.respondent for anomaly in anomalies}

    assert "SHORT" not in respondents


def test_results_use_latest_observation(
    tmp_path: Path,
) -> None:
    """Each authority should return only its latest usable observation."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    anomalies = load_grid_anomalies(
        database_path=database_path,
        limit=10,
    )

    respondents = [anomaly.respondent for anomaly in anomalies]

    assert respondents.count("STABLE") == 1

    assert respondents.count("SPIKE") == 1


def test_limit_is_respected(
    tmp_path: Path,
) -> None:
    """Requested result limit should be respected."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    anomalies = load_grid_anomalies(
        database_path=database_path,
        limit=2,
    )

    assert len(anomalies) == 2
