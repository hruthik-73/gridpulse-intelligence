"""Verify that Spark can read GridPulse Kafka events."""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
EIA_TOPIC = "gridpulse.eia.region-data.v1"


def main() -> None:
    """Read a small sample of GridPulse events from Kafka."""

    spark = (
        SparkSession.builder.appName("gridpulse-spark-kafka-smoke")
        .master("local[2]")
        .config(
            "spark.sql.shuffle.partitions",
            "2",
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    kafka_dataframe = (
        spark.read.format("kafka")
        .option(
            "kafka.bootstrap.servers",
            KAFKA_BOOTSTRAP_SERVERS,
        )
        .option(
            "subscribe",
            EIA_TOPIC,
        )
        .option(
            "startingOffsets",
            "earliest",
        )
        .option(
            "endingOffsets",
            "latest",
        )
        .load()
    )

    events = kafka_dataframe.select(
        F.col("topic"),
        F.col("partition"),
        F.col("offset"),
        F.col("timestamp").alias("kafka_timestamp"),
        F.col("key").cast("string").alias("event_key"),
        F.col("value").cast("string").alias("event_json"),
    )

    sample = events.limit(5).cache()

    count = sample.count()

    print()
    print("=" * 60)
    print("GridPulse Spark ↔ Kafka smoke test")
    print("=" * 60)
    print(f"Spark version: {spark.version}")
    print(f"Kafka bootstrap: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Topic: {EIA_TOPIC}")
    print(f"Sample events read: {count}")
    print("=" * 60)
    print()

    sample.select(
        "partition",
        "offset",
        "kafka_timestamp",
        "event_key",
    ).show(
        truncate=False,
    )

    sample.unpersist()

    if count == 0:
        spark.stop()

        raise RuntimeError("Kafka topic contained no events.")

    print()
    print("Spark Kafka connector: PASS")
    print()

    spark.stop()


if __name__ == "__main__":
    main()
