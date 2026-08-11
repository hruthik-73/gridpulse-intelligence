"""Command-line entry point for historical EIA ingestion."""

import argparse
from datetime import datetime

import structlog

from gridpulse_intelligence.bronze import write_eia_bronze_snapshot
from gridpulse_intelligence.eia_client import EIAClient
from gridpulse_intelligence.quality_gate import (
    validate_or_quarantine_eia_snapshot,
)

logger = structlog.get_logger(__name__)


def parse_hour(value: str) -> datetime:
    """Parse an hourly timestamp in YYYY-MM-DDTHH format."""

    try:
        return datetime.strptime(value, "%Y-%m-%dT%H")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Timestamp must use YYYY-MM-DDTHH format.") from exc


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Ingest historical EIA regional electricity data.")

    parser.add_argument(
        "--start",
        required=True,
        type=parse_hour,
        help="Start hour in YYYY-MM-DDTHH format.",
    )

    parser.add_argument(
        "--end",
        required=True,
        type=parse_hour,
        help="End hour in YYYY-MM-DDTHH format.",
    )

    parser.add_argument(
        "--page-size",
        type=int,
        default=5000,
        help="Number of records requested per API page.",
    )

    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Optional maximum number of records to ingest.",
    )

    return parser.parse_args()


def run_historical_ingestion(
    start: datetime,
    end: datetime,
    page_size: int,
    max_records: int | None,
) -> None:
    """Run historical EIA ingestion through the Bronze quality gate."""

    logger.info(
        "eia_historical_ingestion_started",
        start=start.isoformat(),
        end=end.isoformat(),
        page_size=page_size,
        max_records=max_records,
    )

    client = EIAClient()

    try:
        records = client.get_region_data(
            start=start,
            end=end,
            page_size=page_size,
            max_records=max_records,
        )

        if not records:
            raise RuntimeError("EIA returned no records for the requested time range.")

        output_path = write_eia_bronze_snapshot(
            records=records,
        )

        validation_report = validate_or_quarantine_eia_snapshot(
            snapshot_path=output_path,
        )

    finally:
        client.close()

    logger.info(
        "eia_historical_ingestion_completed",
        start=start.isoformat(),
        end=end.isoformat(),
        records_received=len(records),
        records_validated=validation_report.record_count,
        output_path=str(output_path),
    )

    print()
    print("GridPulse historical EIA ingestion completed")
    print(f"Start: {start:%Y-%m-%dT%H}")
    print(f"End: {end:%Y-%m-%dT%H}")
    print(f"Records received: {len(records)}")
    print(f"Records validated: {validation_report.record_count}")
    print(f"Unique keys: {validation_report.unique_key_count}")
    print("Contract validation: PASSED")
    print(f"Bronze file: {output_path}")


def main() -> None:
    """Application entry point."""

    args = parse_args()

    run_historical_ingestion(
        start=args.start,
        end=args.end,
        page_size=args.page_size,
        max_records=args.max_records,
    )


if __name__ == "__main__":
    main()
