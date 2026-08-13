"""Tests for explainable historical GridPulse grid-risk intelligence."""

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
def test_classify_severity(
    score: float,
    expected: str,
) -> None:
    """Displayed risk thresholds should map correctly."""

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
    """Insert historical observations and one latest observation."""

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
            float,
            float,
            float,
            float,
        ]
    ] = []

    for index in range(history_points):
        demand = 1000.0

        forecast_error_pct = float(1 + (index % 3))

        forecast = demand / (1 + forecast_error_pct / 100)

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

    rows.append(
        (
            start
            + timedelta(
                hours=history_points,
            ),
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
    """Create stable, anomalous, and insufficient-history examples."""

    connection = duckdb.connect(str(database_path))

    try:
        create_schema(connection)

        insert_history(
            connection,
            "STABLE",
            "Stable Authority",
            2.0,
            30.0,
        )

        insert_history(
            connection,
            "SPIKE",
            "Spike Authority",
            40.0,
            800.0,
        )

        insert_history(
            connection,
            "SHORT",
            "Short History",
            80.0,
            900.0,
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

    spike = anomalies[0]

    assert spike.respondent == "SPIKE"
    assert spike.risk_score == pytest.approx(100.0)
    assert spike.severity == "CRITICAL"

    assert spike.history_points == 30

    assert spike.forecast_baseline_pct == pytest.approx(2.0)

    assert spike.generation_baseline_pct == pytest.approx(3.0)

    assert spike.forecast_deviation_score == pytest.approx(4.0)

    assert spike.generation_deviation_score == pytest.approx(4.0)


def test_stable_authority_has_explainable_normal_score(
    tmp_path: Path,
) -> None:
    """Stable observations should remain near their historical baseline."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(database_path)

    anomalies = load_grid_anomalies(
        database_path=database_path,
        limit=10,
    )

    stable = next(anomaly for anomaly in anomalies if anomaly.respondent == "STABLE")

    assert stable.history_points == 30

    assert stable.forecast_baseline_pct == pytest.approx(2.0)

    assert stable.generation_baseline_pct == pytest.approx(3.0)

    assert stable.forecast_deviation_score == pytest.approx(0.0)

    assert stable.generation_deviation_score == pytest.approx(0.0)

    assert stable.risk_score == pytest.approx(0.0)

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


def test_one_result_per_authority(
    tmp_path: Path,
) -> None:
    """Only each authority's latest usable observation should be returned."""

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
        limit=1,
    )

    assert len(anomalies) == 1

    assert anomalies[0].respondent == "SPIKE"
