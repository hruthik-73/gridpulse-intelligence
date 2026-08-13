"""Source freshness intelligence for GridPulse."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import duckdb

DEFAULT_DATABASE_PATH = Path("data/warehouse/gridpulse.duckdb")


@dataclass(frozen=True)
class FreshnessRule:
    """Operational freshness rule for one GridPulse source."""

    source: str
    display_name: str
    dataset: str
    table_name: str
    timestamp_columns: tuple[str, ...]
    fresh_within_hours: float
    stale_after_hours: float


@dataclass(frozen=True)
class SourceFreshnessSignal:
    """Latest freshness state for one source."""

    source: str
    display_name: str
    dataset: str

    state: str

    latest_timestamp: datetime | None
    age_hours: float | None

    timestamp_basis: str

    fresh_within_hours: float
    stale_after_hours: float


FRESHNESS_RULES = (
    FreshnessRule(
        source="eia",
        display_name="EIA Grid",
        dataset="Electricity regional operations",
        table_name="analytics.mart_grid_hourly",
        timestamp_columns=(
            "kafka_timestamp",
            "source_timestamp",
            "period",
        ),
        fresh_within_hours=6.0,
        stale_after_hours=24.0,
    ),
    FreshnessRule(
        source="nws",
        display_name="NWS Weather",
        dataset="Hourly weather forecast",
        table_name="analytics.mart_weather_forecast",
        timestamp_columns=(
            "kafka_timestamp",
            "period_start",
        ),
        fresh_within_hours=6.0,
        stale_after_hours=24.0,
    ),
    FreshnessRule(
        source="afdc",
        display_name="AFDC EV",
        dataset="EV charging infrastructure",
        table_name="analytics.mart_ev_city_rankings",
        timestamp_columns=(
            "latest_kafka_timestamp",
            "kafka_timestamp",
            "latest_station_update",
        ),
        fresh_within_hours=48.0,
        stale_after_hours=168.0,
    ),
)


TIMESTAMP_BASIS = {
    "kafka_timestamp": "Kafka event timestamp",
    "latest_kafka_timestamp": "Latest Kafka event timestamp",
    "source_timestamp": "Upstream source timestamp",
    "period": "Latest analytical period",
    "period_start": "Forecast period start",
    "latest_station_update": "Latest station update",
}


def _split_table_name(
    table_name: str,
) -> tuple[str, str]:
    """Split schema-qualified table name."""

    schema_name, relation_name = table_name.split(
        ".",
        maxsplit=1,
    )

    return (
        schema_name,
        relation_name,
    )


def _table_columns(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
) -> set[str]:
    """Return available columns for a DuckDB table."""

    schema_name, relation_name = _split_table_name(table_name)

    rows = connection.execute(
        """
        SELECT column_name

        FROM information_schema.columns

        WHERE
            table_schema = ?
            AND table_name = ?
        """,
        [
            schema_name,
            relation_name,
        ],
    ).fetchall()

    return {str(row[0]) for row in rows}


def _latest_value(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    column_name: str,
) -> Any:
    """Return the latest value from one known timestamp column."""

    schema_name, relation_name = _split_table_name(table_name)

    query = f'SELECT MAX("{column_name}") FROM "{schema_name}"."{relation_name}"'

    row = connection.execute(query).fetchone()

    if row is None:
        return None

    return row[0]


def _as_utc_datetime(
    value: Any,
) -> datetime | None:
    """Normalize a dynamic DuckDB timestamp value to UTC."""

    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):
        timestamp = value

    elif isinstance(
        value,
        date,
    ):
        timestamp = datetime(
            value.year,
            value.month,
            value.day,
            tzinfo=UTC,
        )

    elif isinstance(
        value,
        str,
    ):
        normalized = value.replace(
            "Z",
            "+00:00",
        )

        try:
            timestamp = datetime.fromisoformat(normalized)
        except ValueError:
            return None

    else:
        return None

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)

    return timestamp.astimezone(UTC)


def classify_freshness(
    age_hours: float | None,
    *,
    fresh_within_hours: float,
    stale_after_hours: float,
) -> str:
    """Classify source freshness using GridPulse operational SLAs."""

    if age_hours is None:
        return "UNKNOWN"

    if age_hours <= fresh_within_hours:
        return "FRESH"

    if age_hours <= stale_after_hours:
        return "DELAYED"

    return "STALE"


def load_source_freshness(
    database_path: Path = DEFAULT_DATABASE_PATH,
    *,
    now: datetime | None = None,
) -> list[SourceFreshnessSignal]:
    """Return freshness intelligence across GridPulse sources."""

    current_time = now or datetime.now(UTC)

    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    else:
        current_time = current_time.astimezone(UTC)

    connection = duckdb.connect(
        str(database_path),
        read_only=True,
    )

    signals: list[SourceFreshnessSignal] = []

    try:
        for rule in FRESHNESS_RULES:
            columns = _table_columns(
                connection,
                rule.table_name,
            )

            timestamp_column = next(
                (column for column in rule.timestamp_columns if column in columns),
                None,
            )

            if timestamp_column is None:
                signals.append(
                    SourceFreshnessSignal(
                        source=rule.source,
                        display_name=rule.display_name,
                        dataset=rule.dataset,
                        state="UNKNOWN",
                        latest_timestamp=None,
                        age_hours=None,
                        timestamp_basis=("No supported timestamp column"),
                        fresh_within_hours=(rule.fresh_within_hours),
                        stale_after_hours=(rule.stale_after_hours),
                    )
                )

                continue

            latest_value = _latest_value(
                connection,
                rule.table_name,
                timestamp_column,
            )

            latest_timestamp = _as_utc_datetime(latest_value)

            age_hours: float | None = None

            if latest_timestamp is not None:
                age_hours = max(
                    0.0,
                    (current_time - latest_timestamp).total_seconds() / 3600.0,
                )

            state = classify_freshness(
                age_hours,
                fresh_within_hours=(rule.fresh_within_hours),
                stale_after_hours=(rule.stale_after_hours),
            )

            signals.append(
                SourceFreshnessSignal(
                    source=rule.source,
                    display_name=rule.display_name,
                    dataset=rule.dataset,
                    state=state,
                    latest_timestamp=latest_timestamp,
                    age_hours=(
                        round(
                            age_hours,
                            2,
                        )
                        if age_hours is not None
                        else None
                    ),
                    timestamp_basis=(
                        TIMESTAMP_BASIS.get(
                            timestamp_column,
                            timestamp_column,
                        )
                    ),
                    fresh_within_hours=(rule.fresh_within_hours),
                    stale_after_hours=(rule.stale_after_hours),
                )
            )

    finally:
        connection.close()

    return signals
