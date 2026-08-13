"""Stream GridPulse Kafka events into local Bronze storage."""

import argparse
from pathlib import Path
from typing import Any

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.streaming import StreamingQuery

from gridpulse_intelligence.kafka_consumer import (
    DEFAULT_TOPICS,
)
from gridpulse_intelligence.spark_streaming import (
    parse_kafka_events,
)

DEFAULT_BRONZE_PATH = Path("data/raw/streaming/bronze_events")

DEFAULT_QUARANTINE_PATH = Path("data/quarantine/spark_kafka_events")

DEFAULT_BRONZE_CHECKPOINT = Path("data/checkpoints/spark_kafka_bronze")

DEFAULT_QUARANTINE_CHECKPOINT = Path("data/checkpoints/spark_kafka_quarantine")


def parse_topics(
    value: str,
) -> tuple[str, ...]:
    """Parse comma-separated Kafka topics."""

    topics = tuple(item.strip() for item in value.split(",") if item.strip())

    if not topics:
        raise argparse.ArgumentTypeError("At least one Kafka topic is required.")

    return topics


def build_spark_session() -> SparkSession:
    """Create the local GridPulse Spark session."""

    return (
        SparkSession.builder.appName("gridpulse-kafka-to-bronze")
        .master("local[2]")
        .config(
            "spark.sql.shuffle.partitions",
            "3",
        )
        .config(
            "spark.sql.streaming.numRecentProgressUpdates",
            "1000",
        )
        .getOrCreate()
    )


def input_rows_processed(
    query: StreamingQuery,
) -> int:
    """Return Kafka rows handled across available micro-batches."""

    total = 0

    for progress in query.recentProgress:
        progress_data: dict[
            str,
            Any,
        ] = progress

        value = progress_data.get(
            "numInputRows",
            0,
        )

        if isinstance(
            value,
            int | float,
        ):
            total += int(value)

    return total


def run_stream(
    bootstrap_servers: str,
    topics: tuple[str, ...],
) -> None:
    """Process currently available Kafka events."""

    spark = build_spark_session()

    spark.sparkContext.setLogLevel("WARN")

    topic_string = ",".join(topics)

    print()
    print("=" * 64)
    print("GridPulse Kafka → Spark → Bronze")
    print("=" * 64)
    print(f"Kafka: {bootstrap_servers}")
    print(f"Topics: {topic_string}")
    print("=" * 64)

    kafka_stream = (
        spark.readStream.format("kafka")
        .option(
            "kafka.bootstrap.servers",
            bootstrap_servers,
        )
        .option(
            "subscribe",
            topic_string,
        )
        .option(
            "startingOffsets",
            "earliest",
        )
        .load()
    )

    parsed = parse_kafka_events(kafka_stream)

    valid_events = parsed.filter(F.col("is_valid")).drop(
        "is_valid",
        "validation_error",
    )

    invalid_events = parsed.filter(~F.col("is_valid"))

    bronze_query = (
        valid_events.writeStream.queryName("gridpulse-bronze-events")
        .format("parquet")
        .outputMode("append")
        .option(
            "checkpointLocation",
            str(DEFAULT_BRONZE_CHECKPOINT),
        )
        .partitionBy(
            "source",
            "kafka_date",
        )
        .trigger(availableNow=True)
        .start(str(DEFAULT_BRONZE_PATH))
    )

    bronze_query.awaitTermination()

    kafka_input_rows = input_rows_processed(bronze_query)

    quarantine_query = (
        invalid_events.writeStream.queryName("gridpulse-quarantine-events")
        .format("parquet")
        .outputMode("append")
        .option(
            "checkpointLocation",
            str(DEFAULT_QUARANTINE_CHECKPOINT),
        )
        .trigger(availableNow=True)
        .start(str(DEFAULT_QUARANTINE_PATH))
    )

    quarantine_query.awaitTermination()

    print()
    print("=" * 64)
    print("KAFKA → BRONZE EXECUTION")
    print("=" * 64)
    print(
        "Kafka input records:",
        kafka_input_rows,
    )
    print(
        "Bronze:",
        DEFAULT_BRONZE_PATH,
    )
    print(
        "Quarantine:",
        DEFAULT_QUARANTINE_PATH,
    )
    print("Spark checkpoints preserved.")
    print("=" * 64)

    # Machine-readable marker consumed by
    # gridpulse_intelligence.pipeline_runs.
    #
    # This represents Kafka source records handled by
    # the primary Bronze streaming query. We intentionally
    # do not add quarantine-query input rows because that
    # query evaluates the same Kafka source independently.
    print(f"GRIDPULSE_RECORDS_PROCESSED={kafka_input_rows}")

    print()
    print("Structured Streaming run completed.")
    print()

    spark.stop()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Stream GridPulse Kafka events into local Bronze storage.")
    )

    parser.add_argument(
        "--bootstrap-servers",
        default="localhost:9092",
    )

    parser.add_argument(
        "--topics",
        type=parse_topics,
        default=DEFAULT_TOPICS,
        help=("Comma-separated Kafka topics."),
    )

    return parser.parse_args()


def main() -> None:
    """Application entry point."""

    args = parse_args()

    run_stream(
        bootstrap_servers=(args.bootstrap_servers),
        topics=args.topics,
    )


if __name__ == "__main__":
    main()
