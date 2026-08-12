"""Command-line entry point for GridPulse Kafka consumption."""

import argparse
from threading import Thread
from wsgiref.simple_server import WSGIServer

from prometheus_client import start_http_server

from gridpulse_intelligence.kafka_consumer import (
    DEFAULT_TOPICS,
    GridPulseKafkaConsumer,
)


def topic_list(
    value: str,
) -> tuple[str, ...]:
    """Parse a comma-separated Kafka topic list."""

    topics = tuple(topic.strip() for topic in value.split(",") if topic.strip())

    if not topics:
        raise argparse.ArgumentTypeError("At least one Kafka topic is required.")

    return topics


def positive_integer(
    value: str,
) -> int:
    """Parse a positive integer."""

    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be an integer.") from exc

    if result < 1:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")

    return result


def positive_float(
    value: str,
) -> float:
    """Parse a positive floating-point value."""

    try:
        result = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Value must be numeric.") from exc

    if result <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than zero.")

    return result


def tcp_port(
    value: str,
) -> int:
    """Parse a valid TCP port."""

    result = positive_integer(value)

    if result > 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535.")

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

    parser.add_argument(
        "--metrics-port",
        type=tcp_port,
        default=None,
        help="Optional Prometheus metrics port.",
    )

    parser.add_argument(
        "--metrics-address",
        default="127.0.0.1",
        help=("Metrics HTTP bind address. Use 0.0.0.0 when Prometheus runs in Docker."),
    )

    return parser.parse_args()


def run_consumer(
    group_id: str,
    topics: tuple[str, ...],
    max_messages: int | None,
    poll_timeout: float,
    metrics_port: int | None = None,
    metrics_address: str = "127.0.0.1",
) -> int:
    """Run the validated GridPulse Kafka consumer."""

    normalized_group_id = group_id.strip()

    if not normalized_group_id:
        raise ValueError("group_id must not be empty")

    normalized_metrics_address = metrics_address.strip()

    if not normalized_metrics_address:
        raise ValueError("metrics_address must not be empty")

    consumer = GridPulseKafkaConsumer(
        group_id=normalized_group_id,
    )

    metrics_server: WSGIServer | None = None
    metrics_thread: Thread | None = None

    if metrics_port is not None:
        (
            metrics_server,
            metrics_thread,
        ) = start_http_server(
            port=metrics_port,
            addr=normalized_metrics_address,
        )

        print()
        print("Prometheus metrics exporter started")
        print(f"Address: {normalized_metrics_address}")
        print(f"Port: {metrics_port}")

    consumer.subscribe(
        topics=topics,
    )

    try:
        handled = consumer.run(
            max_messages=max_messages,
            poll_timeout=poll_timeout,
        )

    finally:
        if metrics_server is not None:
            metrics_server.shutdown()
            metrics_server.server_close()

        if metrics_thread is not None:
            metrics_thread.join(timeout=5)

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
        metrics_port=args.metrics_port,
        metrics_address=args.metrics_address,
    )


if __name__ == "__main__":
    main()
