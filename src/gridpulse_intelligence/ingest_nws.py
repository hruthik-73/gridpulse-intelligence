"""Command-line entry point for NWS hourly forecast ingestion."""

import argparse

import structlog

from gridpulse_intelligence.nws_client import NWSClient
from gridpulse_intelligence.quality_gate import (
    validate_or_quarantine_nws_snapshot,
)
from gridpulse_intelligence.weather_bronze import (
    write_nws_bronze_snapshot,
)

logger = structlog.get_logger(__name__)


def latitude_value(value: str) -> float:
    """Parse and validate latitude."""

    try:
        latitude = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Latitude must be a number.") from exc

    if not -90 <= latitude <= 90:
        raise argparse.ArgumentTypeError("Latitude must be between -90 and 90.")

    return latitude


def longitude_value(value: str) -> float:
    """Parse and validate longitude."""

    try:
        longitude = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Longitude must be a number.") from exc

    if not -180 <= longitude <= 180:
        raise argparse.ArgumentTypeError("Longitude must be between -180 and 180.")

    return longitude


def positive_integer(value: str) -> int:
    """Parse a positive integer command-line value."""

    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be an integer.") from exc

    if result < 1:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")

    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Ingest an hourly National Weather Service forecast into the GridPulse Bronze layer."
        )
    )

    parser.add_argument(
        "--latitude",
        required=True,
        type=latitude_value,
        help="Forecast latitude.",
    )

    parser.add_argument(
        "--longitude",
        required=True,
        type=longitude_value,
        help="Forecast longitude.",
    )

    parser.add_argument(
        "--hours",
        type=positive_integer,
        default=24,
        help="Maximum number of hourly forecast periods to ingest.",
    )

    parser.add_argument(
        "--location-name",
        default=None,
        help="Optional human-readable location label for logging.",
    )

    return parser.parse_args()


def run_ingestion(
    latitude: float,
    longitude: float,
    hours: int,
    location_name: str | None = None,
) -> None:
    """Run one NWS forecast ingestion."""

    logger.info(
        "nws_ingestion_started",
        latitude=latitude,
        longitude=longitude,
        hours=hours,
        location_name=location_name,
    )

    client = NWSClient()

    try:
        records = client.get_hourly_forecast(
            latitude=latitude,
            longitude=longitude,
            limit=hours,
        )

        if not records:
            raise RuntimeError("NWS returned no hourly forecast records.")

        output_path = write_nws_bronze_snapshot(
            records=records,
        )

        validation_report = validate_or_quarantine_nws_snapshot(
            snapshot_path=output_path,
        )

    finally:
        client.close()

    logger.info(
        "nws_ingestion_completed",
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        records_received=len(records),
        records_validated=validation_report.record_count,
        output_path=str(output_path),
    )

    print()
    print("GridPulse NWS ingestion completed")

    if location_name:
        print(f"Location: {location_name}")

    print(f"Coordinates: {latitude}, {longitude}")
    print(f"Records received: {len(records)}")
    print(f"Records validated: {validation_report.record_count}")
    print(f"Unique keys: {validation_report.unique_key_count}")
    print("Contract validation: PASSED")
    print(f"Bronze file: {output_path}")


def main() -> None:
    """Application entry point."""

    args = parse_args()

    run_ingestion(
        latitude=args.latitude,
        longitude=args.longitude,
        hours=args.hours,
        location_name=args.location_name,
    )


if __name__ == "__main__":
    main()
