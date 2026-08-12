"""Command-line entry point for GridPulse Kafka consumption."""

import argparse

from gridpulse_intelligence.kafka_consumer import (
    DEFAULT_TOPICS,
    GridPulseKafkaConsumer,
)


def topic_list(value: str) -> tuple[str, ...]:
    """Parse a comma-separated Kafka topic list."""

    topics = tuple(topic.strip() for topic in value.split(",") if topic.strip())

    if not topics:
        raise argparse.ArgumentTypeError("At least one Kafka topic is required.")

    return topics


def positive_integer(value: str) -> int:
    """Parse a positive integer."""

    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be an integer.") from exc

    if result < 1:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")

    return result


def positive_float(value: str) -> float:
    """Parse a positive floating-point value."""

    try:
        result = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be numeric.") from exc

    if result <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")

    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=("Consume and validate GridPulse Kafka events."))

    parser.add_argument(
        "--group-id",
        default="gridpulse-validation-consumer-v1",
        help="Kafka consumer group ID.",
    )

    parser.add_argument(
        "--topics",
        type=topic_list,
        default=DEFAULT_TOPICS,
        help=("Comma-separated Kafka topics. Defaults to all GridPulse source topics."),
    )

    parser.add_argument(
        "--max-messages",
        type=positive_integer,
        default=None,
        help=("Optional number of Kafka messages to handle before exiting."),
    )

    parser.add_argument(
        "--poll-timeout",
        type=positive_float,
        default=1.0,
        help="Kafka polling timeout in seconds.",
    )

    return parser.parse_args()


def run_consumer(
    group_id: str,
    topics: tuple[str, ...],
    max_messages: int | None,
    poll_timeout: float,
) -> int:
    """Run the validated GridPulse Kafka consumer."""

    normalized_group_id = group_id.strip()

    if not normalized_group_id:
        raise ValueError("group_id must not be empty")

    consumer = GridPulseKafkaConsumer(
        group_id=normalized_group_id,
    )

    consumer.subscribe(
        topics=topics,
    )

    handled = consumer.run(
        max_messages=max_messages,
        poll_timeout=poll_timeout,
    )

    print()
    print("GridPulse Kafka consumer completed")
    print(f"Consumer group: {normalized_group_id}")
    print(f"Messages handled: {handled}")

    return handled


def main() -> None:
    """Application entry point."""

    args = parse_args()

    run_consumer(
        group_id=args.group_id,
        topics=args.topics,
        max_messages=args.max_messages,
        poll_timeout=args.poll_timeout,
    )


if __name__ == "__main__":
    main()
