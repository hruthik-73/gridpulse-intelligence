"""Tests for GridPulse source freshness intelligence."""

from datetime import UTC, datetime
from pathlib import Path

import duckdb

from gridpulse_intelligence.source_freshness import (
    classify_freshness,
    load_source_freshness,
)


def create_database(
    database_path: Path,
) -> None:
    """Create minimal marts with different freshness ages."""

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
                kafka_timestamp TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE analytics.mart_weather_forecast (
                kafka_timestamp TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE analytics.mart_ev_city_rankings (
                latest_station_update TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            INSERT INTO analytics.mart_grid_hourly
            VALUES ('2026-08-13 10:00:00')
            """
        )

        connection.execute(
            """
            INSERT INTO analytics.mart_weather_forecast
            VALUES ('2026-08-13 02:00:00')
            """
        )

        connection.execute(
            """
            INSERT INTO analytics.mart_ev_city_rankings
            VALUES ('2026-08-03 12:00:00')
            """
        )

    finally:
        connection.close()


def test_classify_freshness() -> None:
    """Freshness thresholds should classify operational states."""

    assert (
        classify_freshness(
            2.0,
            fresh_within_hours=6.0,
            stale_after_hours=24.0,
        )
        == "FRESH"
    )

    assert (
        classify_freshness(
            10.0,
            fresh_within_hours=6.0,
            stale_after_hours=24.0,
        )
        == "DELAYED"
    )

    assert (
        classify_freshness(
            30.0,
            fresh_within_hours=6.0,
            stale_after_hours=24.0,
        )
        == "STALE"
    )


def test_source_freshness_states(
    tmp_path: Path,
) -> None:
    """Sources should be independently classified."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_database(database_path)

    signals = load_source_freshness(
        database_path=database_path,
        now=datetime(
            2026,
            8,
            13,
            12,
            tzinfo=UTC,
        ),
    )

    states = {signal.source: signal.state for signal in signals}

    assert states["eia"] == "FRESH"

    assert states["nws"] == "DELAYED"

    assert states["afdc"] == "STALE"


def test_freshness_exposes_timestamp_basis(
    tmp_path: Path,
) -> None:
    """Freshness should explain which timestamp drives the signal."""

    database_path = tmp_path / "gridpulse.duckdb"

    create_database(database_path)

    signals = load_source_freshness(
        database_path=database_path,
        now=datetime(
            2026,
            8,
            13,
            12,
            tzinfo=UTC,
        ),
    )

    by_source = {signal.source: signal for signal in signals}

    assert by_source["eia"].timestamp_basis == "Kafka event timestamp"

    assert by_source["afdc"].timestamp_basis == "Latest station update"


def test_missing_table_becomes_unknown(
    tmp_path: Path,
) -> None:
    """Missing marts should not crash freshness intelligence."""

    database_path = tmp_path / "gridpulse.duckdb"

    connection = duckdb.connect(str(database_path))

    connection.execute(
        """
        CREATE SCHEMA analytics
        """
    )

    connection.close()

    signals = load_source_freshness(
        database_path=database_path,
        now=datetime(
            2026,
            8,
            13,
            12,
            tzinfo=UTC,
        ),
    )

    assert all(signal.state == "UNKNOWN" for signal in signals)
