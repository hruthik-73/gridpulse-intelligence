"""Command-line entry point for EIA Bronze ingestion."""

import argparse

import structlog

from gridpulse_intelligence.bronze import write_eia_bronze_snapshot
from gridpulse_intelligence.eia_client import EIAClient
from gridpulse_intelligence.quality_gate import (
    validate_or_quarantine_eia_snapshot,
)

logger = structlog.get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Ingest EIA regional electricity data into the Bronze layer."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Number of EIA records to retrieve (default: 25).",
    )

    return parser.parse_args()


def run_ingestion(limit: int) -> None:
    """Run one EIA Bronze ingestion through the quality gate."""

    logger.info(
        "eia_ingestion_started",
        requested_records=limit,
    )

    client = EIAClient()

    try:
        records = client.get_latest_region_data(
            length=limit,
        )

        output_path = write_eia_bronze_snapshot(
            records=records,
        )

        validation_report = validate_or_quarantine_eia_snapshot(
            snapshot_path=output_path,
        )

    finally:
        client.close()

    logger.info(
        "eia_ingestion_completed",
        requested_records=limit,
        records_received=len(records),
        validated_records=validation_report.record_count,
        unique_keys=validation_report.unique_key_count,
        output_path=str(output_path),
    )

    print()
    print("GridPulse EIA ingestion completed")
    print(f"Records received: {len(records)}")
    print(f"Records validated: {validation_report.record_count}")
    print(f"Unique keys: {validation_report.unique_key_count}")
    print("Contract validation: PASSED")
    print(f"Bronze file: {output_path}")


def main() -> None:
    """Application entry point."""

    args = parse_args()

    run_ingestion(
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
