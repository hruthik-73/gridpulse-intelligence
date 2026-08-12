"""Command-line entry point for AFDC EV charging station ingestion."""

import argparse

import structlog

from gridpulse_intelligence.afdc_client import AFDCClient
from gridpulse_intelligence.ev_bronze import (
    write_ev_bronze_snapshot,
)
from gridpulse_intelligence.quality_gate import (
    validate_or_quarantine_ev_snapshot,
)

logger = structlog.get_logger(__name__)


def state_code(value: str) -> str:
    """Parse and validate a two-letter U.S. state code."""

    normalized = value.strip().upper()

    if len(normalized) != 2 or not normalized.isalpha():
        raise argparse.ArgumentTypeError("State must be a two-letter code.")

    return normalized


def station_limit(value: str) -> int:
    """Parse an AFDC station result limit."""

    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Limit must be an integer.") from exc

    if not 1 <= result <= AFDCClient.MAX_LIMIT:
        raise argparse.ArgumentTypeError(f"Limit must be between 1 and {AFDCClient.MAX_LIMIT}.")

    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Ingest public EV charging stations from AFDC into the GridPulse Bronze layer."
        )
    )

    parser.add_argument(
        "--state",
        required=True,
        type=state_code,
        help="Two-letter U.S. state code, for example OH.",
    )

    parser.add_argument(
        "--limit",
        type=station_limit,
        default=50,
        help="Maximum number of stations to ingest.",
    )

    return parser.parse_args()


def run_ingestion(
    state: str,
    limit: int,
) -> None:
    """Run one AFDC EV charging station ingestion."""

    logger.info(
        "afdc_ingestion_started",
        state=state,
        requested_limit=limit,
    )

    client = AFDCClient()

    try:
        records, total_results = client.get_public_ev_stations(
            state=state,
            limit=limit,
        )

        if not records:
            raise RuntimeError("AFDC returned no public EV charging stations.")

        output_path = write_ev_bronze_snapshot(
            records=records,
            query_state=state,
            total_results=total_results,
        )

        validation_report = validate_or_quarantine_ev_snapshot(
            snapshot_path=output_path,
        )

    finally:
        client.close()

    logger.info(
        "afdc_ingestion_completed",
        state=state,
        records_received=len(records),
        total_results=total_results,
        records_validated=validation_report.record_count,
        output_path=str(output_path),
    )

    print()
    print("GridPulse AFDC EV ingestion completed")
    print(f"State: {state}")
    print(f"Records received: {len(records)}")
    print(f"Total matching stations: {total_results}")
    print(f"Records validated: {validation_report.record_count}")
    print(f"Unique keys: {validation_report.unique_key_count}")
    print("Contract validation: PASSED")
    print(f"Bronze file: {output_path}")


def main() -> None:
    """Application entry point."""

    args = parse_args()

    run_ingestion(
        state=args.state,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
