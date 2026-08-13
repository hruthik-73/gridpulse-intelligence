"""Current data-quality intelligence for the GridPulse lakehouse."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb

BRONZE_ROOT = Path("data/raw/streaming/bronze_events")

SILVER_ROOT = Path("data/processed/silver")

GOLD_ROOT = Path("data/processed/gold")

SILVER_QUARANTINE_ROOT = Path("data/quarantine/silver_events")


SILVER_DATASETS = {
    "EIA Grid": SILVER_ROOT / "eia_region_data",
    "NWS Weather": SILVER_ROOT / "nws_hourly_forecast",
    "AFDC EV": SILVER_ROOT / "afdc_ev_stations",
}


GOLD_DATASETS = {
    "EIA Grid": GOLD_ROOT / "eia_balancing_authority_hourly",
    "NWS Weather": GOLD_ROOT / "nws_hourly_weather",
    "AFDC EV": GOLD_ROOT / "afdc_city_infrastructure",
}


@dataclass(frozen=True)
class DataQualityDatasetCount:
    """Current row count for one materialized dataset."""

    dataset: str
    layer: str
    rows: int | None


@dataclass(frozen=True)
class DataQualityMetrics:
    """Derived Bronze → Silver quality metrics."""

    removed_before_silver: int | None
    quality_failure_rows: int | None
    deduplicated_rows: int | None

    silver_retention_pct: float | None
    quality_failure_pct: float | None

    conservation_state: str


@dataclass(frozen=True)
class DataQualitySnapshot:
    """Current GridPulse lakehouse quality snapshot."""

    evaluated_at: datetime

    status: str

    bronze_input_rows: int | None
    silver_output_rows: int | None
    gold_output_rows: int | None

    removed_before_silver: int | None

    quality_failure_rows: int | None
    deduplicated_rows: int | None

    silver_retention_pct: float | None
    quality_failure_pct: float | None

    conservation_state: str

    silver_datasets: tuple[
        DataQualityDatasetCount,
        ...,
    ]

    gold_datasets: tuple[
        DataQualityDatasetCount,
        ...,
    ]

    detail: str


def _count_parquet_rows(
    root: Path,
) -> int | None:
    """Count rows across all Parquet files beneath a dataset root."""

    files = sorted(str(path) for path in root.rglob("*.parquet"))

    if not files:
        return None

    connection = duckdb.connect(
        database=":memory:",
    )

    try:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM read_parquet(?)
            """,
            [files],
        ).fetchone()

    finally:
        connection.close()

    if row is None:
        return None

    return int(row[0])


def derive_data_quality_metrics(
    *,
    bronze_rows: int | None,
    silver_rows: int | None,
    quality_failure_rows: int | None,
) -> DataQualityMetrics:
    """Derive quality metrics without inventing unexplained removals."""

    if bronze_rows is None or silver_rows is None:
        return DataQualityMetrics(
            removed_before_silver=None,
            quality_failure_rows=(quality_failure_rows),
            deduplicated_rows=None,
            silver_retention_pct=None,
            quality_failure_pct=None,
            conservation_state="UNKNOWN",
        )

    removed = bronze_rows - silver_rows

    if bronze_rows > 0:
        retention_pct = round(
            (silver_rows / bronze_rows) * 100.0,
            3,
        )

    else:
        retention_pct = None

    if quality_failure_rows is not None and bronze_rows > 0:
        quality_failure_pct = round(
            (quality_failure_rows / bronze_rows) * 100.0,
            3,
        )

    else:
        quality_failure_pct = None

    if removed < 0:
        return DataQualityMetrics(
            removed_before_silver=removed,
            quality_failure_rows=(quality_failure_rows),
            deduplicated_rows=None,
            silver_retention_pct=(retention_pct),
            quality_failure_pct=(quality_failure_pct),
            conservation_state="CHECK",
        )

    if quality_failure_rows is None:
        return DataQualityMetrics(
            removed_before_silver=removed,
            quality_failure_rows=None,
            deduplicated_rows=None,
            silver_retention_pct=(retention_pct),
            quality_failure_pct=None,
            conservation_state="PARTIAL",
        )

    remaining = removed - quality_failure_rows

    if remaining < 0:
        return DataQualityMetrics(
            removed_before_silver=removed,
            quality_failure_rows=(quality_failure_rows),
            deduplicated_rows=None,
            silver_retention_pct=(retention_pct),
            quality_failure_pct=(quality_failure_pct),
            conservation_state="CHECK",
        )

    return DataQualityMetrics(
        removed_before_silver=removed,
        quality_failure_rows=(quality_failure_rows),
        deduplicated_rows=remaining,
        silver_retention_pct=(retention_pct),
        quality_failure_pct=(quality_failure_pct),
        conservation_state="BALANCED",
    )


def build_data_quality_snapshot() -> DataQualitySnapshot:
    """Build current quality intelligence from materialized lakehouse data."""

    bronze_rows = _count_parquet_rows(BRONZE_ROOT)

    silver_counts = tuple(
        DataQualityDatasetCount(
            dataset=dataset,
            layer="SILVER",
            rows=_count_parquet_rows(path),
        )
        for dataset, path in (SILVER_DATASETS.items())
    )

    gold_counts = tuple(
        DataQualityDatasetCount(
            dataset=dataset,
            layer="GOLD",
            rows=_count_parquet_rows(path),
        )
        for dataset, path in (GOLD_DATASETS.items())
    )

    silver_values = [item.rows for item in silver_counts]

    gold_values = [item.rows for item in gold_counts]

    silver_rows = (
        sum(row for row in silver_values if row is not None)
        if any(row is not None for row in silver_values)
        else None
    )

    gold_rows = (
        sum(row for row in gold_values if row is not None)
        if any(row is not None for row in gold_values)
        else None
    )

    quality_failure_rows = _count_parquet_rows(SILVER_QUARANTINE_ROOT)

    metrics = derive_data_quality_metrics(
        bronze_rows=bronze_rows,
        silver_rows=silver_rows,
        quality_failure_rows=(quality_failure_rows),
    )

    if bronze_rows is None or silver_rows is None:
        status = "UNKNOWN"

        detail = "Current Bronze or Silver materialization is unavailable."

    elif metrics.conservation_state == "CHECK":
        status = "CHECK"

        detail = (
            "Current materialized counts do not "
            "fully reconcile. Review transformation "
            "and quarantine semantics."
        )

    else:
        status = "MEASURED"

        detail = (
            "Bronze → Silver quality metrics are "
            "derived from current materialized "
            "Parquet datasets. Gold rows represent "
            "analytical aggregation and are not part "
            "of the conservation check."
        )

    return DataQualitySnapshot(
        evaluated_at=datetime.now(UTC),
        status=status,
        bronze_input_rows=(bronze_rows),
        silver_output_rows=(silver_rows),
        gold_output_rows=(gold_rows),
        removed_before_silver=(metrics.removed_before_silver),
        quality_failure_rows=(metrics.quality_failure_rows),
        deduplicated_rows=(metrics.deduplicated_rows),
        silver_retention_pct=(metrics.silver_retention_pct),
        quality_failure_pct=(metrics.quality_failure_pct),
        conservation_state=(metrics.conservation_state),
        silver_datasets=(silver_counts),
        gold_datasets=(gold_counts),
        detail=detail,
    )
