"""Tests for GridPulse grid-risk intelligence."""

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
    """Risk-score thresholds should map to the correct severity."""

    assert classify_severity(score) == expected


def create_test_database(
    database_path: Path,
) -> None:
    """Create a minimal GridPulse analytics mart for risk tests."""

    connection = duckdb.connect(
        str(database_path),
    )

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
                demand_mwh DOUBLE,
                demand_forecast_mwh DOUBLE,
                demand_forecast_error_pct DOUBLE,
                generation_demand_gap_mwh DOUBLE
            )
            """
        )

        connection.execute(
            """
            INSERT INTO analytics.mart_grid_hourly
            VALUES
                (
                    '2026-08-10 09:00:00',
                    'LOW',
                    'Low Risk Authority',
                    100.0,
                    101.0,
                    -1.0,
                    1.0
                ),
                (
                    '2026-08-10 09:00:00',
                    'MED',
                    'Medium Risk Authority',
                    100.0,
                    105.0,
                    -5.0,
                    10.0
                ),
                (
                    '2026-08-10 09:00:00',
                    'ELEV',
                    'Elevated Risk Authority',
                    100.0,
                    110.0,
                    -10.0,
                    20.0
                ),
                (
                    '2026-08-10 09:00:00',
                    'CRIT',
                    'Critical Risk Authority',
                    100.0,
                    120.0,
                    -20.0,
                    40.0
                )
            """
        )

    finally:
        connection.close()


def test_load_grid_anomalies_orders_highest_risk_first(
    tmp_path: Path,
) -> None:
    """The most extreme peer-relative observation should rank first."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(
        database_path,
    )

    anomalies = load_grid_anomalies(
        database_path=database_path,
        limit=10,
    )

    assert len(anomalies) == 4

    assert anomalies[0].respondent == "CRIT"
    assert anomalies[0].risk_score == pytest.approx(
        100.0,
    )
    assert anomalies[0].severity == "CRITICAL"

    assert anomalies[-1].respondent == "LOW"
    assert anomalies[-1].risk_score == pytest.approx(
        0.0,
    )
    assert anomalies[-1].severity == "NORMAL"


def test_load_grid_anomalies_calculates_elevated_risk(
    tmp_path: Path,
) -> None:
    """Intermediate observations should receive peer-relative risk scores."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(
        database_path,
    )

    anomalies = load_grid_anomalies(
        database_path=database_path,
        limit=10,
    )

    elevated = next(anomaly for anomaly in anomalies if anomaly.respondent == "ELEV")

    assert elevated.risk_score == pytest.approx(
        66.6666666667,
    )

    assert elevated.severity == "ELEVATED"

    assert elevated.forecast_error_pct == pytest.approx(
        -10.0,
    )

    assert elevated.generation_gap_pct == pytest.approx(
        20.0,
    )


def test_load_grid_anomalies_respects_limit(
    tmp_path: Path,
) -> None:
    """The requested result limit should be applied."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_test_database(
        database_path,
    )

    anomalies = load_grid_anomalies(
        database_path=database_path,
        limit=2,
    )

    assert len(anomalies) == 2

    assert anomalies[0].respondent == "CRIT"
