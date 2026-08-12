"""Replay historical EIA records through Kafka."""

import argparse
import time
from collections.abc import Callable
from datetime import datetime

import structlog

from gridpulse_intelligence.eia_client import EIAClient
from gridpulse_intelligence.event_factory import (
    EIA_TOPIC,
    create_eia_event,
)
from gridpulse_intelligence.kafka_producer import (
    KafkaEventProducer,
)
from gridpulse_intelligence.models import GridRegionRecord

logger = structlog.get_logger(__name__)

SleepFunction = Callable[[float], None]


def parse_hour(value: str) -> datetime:
    """Parse YYYY-MM-DDTHH timestamps."""

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%dT%H",
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Timestamp must use YYYY-MM-DDTHH format.") from exc


def positive_float(value: str) -> float:
    """Parse a positive floating-point value."""

    try:
        result = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be numeric.") from exc

    if result <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")

    return result


def positive_integer(value: str) -> int:
    """Parse a positive integer."""

    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be an integer.") from exc

    if result < 1:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")

    return result


def calculate_replay_delay(
    previous_period: datetime,
    current_period: datetime,
    speed: float,
) -> float:
    """Convert source-time distance into replay delay."""

    if speed <= 0:
        raise ValueError("speed must be greater than zero")

    source_delay = (current_period - previous_period).total_seconds()

    if source_delay <= 0:
        return 0.0

    return source_delay / speed


def sort_records(
    records: list[GridRegionRecord],
) -> list[GridRegionRecord]:
    """Return records in deterministic event-time order."""

    return sorted(
        records,
        key=lambda record: (
            record.period,
            record.respondent,
            record.record_type,
        ),
    )


def replay_records(
    records: list[GridRegionRecord],
    producer: KafkaEventProducer,
    speed: float,
    sleep_function: SleepFunction = time.sleep,
) -> int:
    """Replay historical EIA records through Kafka."""

    if not records:
        return 0

    if speed <= 0:
        raise ValueError("speed must be greater than zero")

    ordered_records = sort_records(records)

    previous_period: datetime | None = None
    published = 0

    for record in ordered_records:
        if previous_period is not None and record.period != previous_period:
            producer.flush()

            delay = calculate_replay_delay(
                previous_period=previous_period,
                current_period=record.period,
                speed=speed,
            )

            if delay > 0:
                logger.info(
                    "eia_replay_waiting",
                    previous_period=(previous_period.isoformat()),
                    current_period=(record.period.isoformat()),
                    delay_seconds=delay,
                    speed=speed,
                )

                sleep_function(delay)

        event = create_eia_event(
            record=record,
            replay=True,
        )

        producer.publish(
            EIA_TOPIC,
            event,
        )

        published += 1
        previous_period = record.period

    producer.flush()

    logger.info(
        "eia_replay_completed",
        topic=EIA_TOPIC,
        records_published=published,
        speed=speed,
        first_period=ordered_records[0].period.isoformat(),
        last_period=ordered_records[-1].period.isoformat(),
    )

    return published


def run_replay(
    start: datetime,
    end: datetime,
    speed: float,
    page_size: int,
    max_records: int | None,
) -> int:
    """Retrieve historical EIA data and replay it."""

    if start > end:
        raise ValueError("start must be earlier than or equal to end")

    logger.info(
        "eia_replay_started",
        start=start.isoformat(),
        end=end.isoformat(),
        speed=speed,
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
    finally:
        client.close()

    if not records:
        raise RuntimeError("EIA returned no historical records to replay.")

    producer = KafkaEventProducer()

    published = replay_records(
        records=records,
        producer=producer,
        speed=speed,
    )

    print()
    print("GridPulse EIA Kafka replay completed")
    print(f"Start: {start:%Y-%m-%dT%H}")
    print(f"End: {end:%Y-%m-%dT%H}")
    print(f"Replay speed: {speed:g}x")
    print(f"Records published: {published}")
    print(f"Topic: {EIA_TOPIC}")
    print("Replay flag: TRUE")

    return published


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Replay historical EIA electricity records through GridPulse Kafka.")
    )

    parser.add_argument(
        "--start",
        required=True,
        type=parse_hour,
        help="Historical start hour in YYYY-MM-DDTHH format.",
    )

    parser.add_argument(
        "--end",
        required=True,
        type=parse_hour,
        help="Historical end hour in YYYY-MM-DDTHH format.",
    )

    parser.add_argument(
        "--speed",
        type=positive_float,
        default=3600.0,
        help=("Replay acceleration factor. 3600 means one historical hour per real second."),
    )

    parser.add_argument(
        "--page-size",
        type=positive_integer,
        default=5000,
        help="EIA API page size.",
    )

    parser.add_argument(
        "--max-records",
        type=positive_integer,
        default=None,
        help="Optional maximum number of historical records.",
    )

    return parser.parse_args()


def main() -> None:
    """Application entry point."""

    args = parse_args()

    run_replay(
        start=args.start,
        end=args.end,
        speed=args.speed,
        page_size=args.page_size,
        max_records=args.max_records,
    )


if __name__ == "__main__":
    main()
