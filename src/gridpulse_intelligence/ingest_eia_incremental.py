"""Command-line entry point for incremental EIA ingestion."""

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import structlog

from gridpulse_intelligence.bronze import write_eia_bronze_snapshot
from gridpulse_intelligence.eia_client import EIAClient
from gridpulse_intelligence.incremental import (
    IncrementalWindow,
    calculate_incremental_window,
)
from gridpulse_intelligence.quality_gate import (
    validate_or_quarantine_eia_snapshot,
)
from gridpulse_intelligence.watermark import (
    DEFAULT_WATERMARK_PATH,
    read_watermark,
    write_watermark,
)

logger = structlog.get_logger(__name__)


def parse_hour(value: str) -> datetime:
    """Parse an hourly timestamp in YYYY-MM-DDTHH format."""

    try:
        return datetime.strptime(value, "%Y-%m-%dT%H")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Timestamp must use YYYY-MM-DDTHH format.") from exc


def cap_window(
    window: IncrementalWindow,
    max_window_hours: int,
) -> IncrementalWindow:
    """Limit an incremental run to a bounded number of hours."""

    if max_window_hours < 1:
        raise ValueError("max_window_hours must be greater than zero")

    maximum_end = window.start + timedelta(hours=max_window_hours - 1)

    return IncrementalWindow(
        start=window.start,
        end=min(window.end, maximum_end),
    )


def expected_periods(
    window: IncrementalWindow,
) -> set[datetime]:
    """Return every hourly period expected in an ingestion window."""

    periods: set[datetime] = set()
    current = window.start

    while current <= window.end:
        periods.add(current)
        current += timedelta(hours=1)

    return periods


def validate_period_coverage(
    window: IncrementalWindow,
    periods_received: set[datetime],
) -> None:
    """Ensure every requested hourly period was returned."""

    required_periods = expected_periods(window)

    missing_periods = sorted(required_periods - periods_received)

    if not missing_periods:
        return

    missing_values = ", ".join(period.strftime("%Y-%m-%dT%H") for period in missing_periods)

    raise RuntimeError(
        "EIA response is missing requested hourly periods: "
        f"{missing_values}. "
        "The watermark will not advance."
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Incrementally ingest EIA regional electricity data."
    )

    parser.add_argument(
        "--bootstrap-start",
        required=True,
        type=parse_hour,
        help="Initial start hour when no watermark exists.",
    )

    parser.add_argument(
        "--safety-lag-hours",
        type=int,
        default=2,
        help="Hours behind current UTC time considered safe to ingest.",
    )

    parser.add_argument(
        "--max-window-hours",
        type=int,
        default=6,
        help="Maximum number of hourly periods processed per run.",
    )

    parser.add_argument(
        "--page-size",
        type=int,
        default=5000,
        help="Number of EIA rows requested per API page.",
    )

    parser.add_argument(
        "--watermark-path",
        type=Path,
        default=DEFAULT_WATERMARK_PATH,
        help="Local path used to store incremental ingestion state.",
    )

    return parser.parse_args()


def run_incremental_ingestion(
    bootstrap_start: datetime,
    safety_lag_hours: int,
    max_window_hours: int,
    page_size: int,
    watermark_path: Path,
) -> None:
    """Run one incremental EIA ingestion window."""

    watermark = read_watermark(
        path=watermark_path,
    )

    available_window = calculate_incremental_window(
        watermark=watermark,
        bootstrap_start=bootstrap_start,
        safety_lag_hours=safety_lag_hours,
    )

    if available_window is None:
        print()
        print("GridPulse incremental ingestion")
        print("Status: UP TO DATE")

        if watermark is not None:
            print(f"Last successful period: {watermark:%Y-%m-%dT%H}")

        return

    window = cap_window(
        window=available_window,
        max_window_hours=max_window_hours,
    )

    logger.info(
        "eia_incremental_ingestion_started",
        watermark=(watermark.isoformat() if watermark is not None else None),
        window_start=window.start.isoformat(),
        window_end=window.end.isoformat(),
        window_hours=window.hour_count,
    )

    client = EIAClient()

    try:
        records = client.get_region_data(
            start=window.start,
            end=window.end,
            page_size=page_size,
        )

        if not records:
            raise RuntimeError("EIA returned no records for the incremental window.")

        periods_received = {record.period for record in records}

        validate_period_coverage(
            window=window,
            periods_received=periods_received,
        )

        output_path = write_eia_bronze_snapshot(
            records=records,
        )

        validation_report = validate_or_quarantine_eia_snapshot(
            snapshot_path=output_path,
        )

    finally:
        client.close()

    watermark_file = write_watermark(
        period=window.end,
        path=watermark_path,
    )

    logger.info(
        "eia_incremental_ingestion_completed",
        window_start=window.start.isoformat(),
        window_end=window.end.isoformat(),
        records_received=len(records),
        records_validated=validation_report.record_count,
        watermark=str(watermark_file),
    )

    print()
    print("GridPulse incremental EIA ingestion completed")
    print(f"Window start: {window.start:%Y-%m-%dT%H}")
    print(f"Window end: {window.end:%Y-%m-%dT%H}")
    print(f"Window hours: {window.hour_count}")
    print(f"Records received: {len(records)}")
    print(f"Records validated: {validation_report.record_count}")
    print(f"Unique keys: {validation_report.unique_key_count}")
    print("Contract validation: PASSED")
    print(f"Bronze file: {output_path}")
    print(f"Watermark: {watermark_file}")


def main() -> None:
    """Application entry point."""

    args = parse_args()

    run_incremental_ingestion(
        bootstrap_start=args.bootstrap_start,
        safety_lag_hours=args.safety_lag_hours,
        max_window_hours=args.max_window_hours,
        page_size=args.page_size,
        watermark_path=args.watermark_path,
    )


if __name__ == "__main__":
    main()
