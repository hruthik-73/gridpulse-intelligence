"""Spark Structured Streaming transformations for GridPulse."""

from typing import Final

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    StringType,
    StructField,
    StructType,
)

VALID_EVENT_SOURCES: Final[tuple[str, ...]] = (
    "eia",
    "nws",
    "afdc",
    "platform",
)

EVENT_ENVELOPE_SCHEMA: Final[StructType] = StructType(
    [
        StructField(
            "event_id",
            StringType(),
            True,
        ),
        StructField(
            "event_version",
            StringType(),
            True,
        ),
        StructField(
            "source",
            StringType(),
            True,
        ),
        StructField(
            "dataset",
            StringType(),
            True,
        ),
        StructField(
            "event_type",
            StringType(),
            True,
        ),
        StructField(
            "partition_key",
            StringType(),
            True,
        ),
        StructField(
            "emitted_at",
            StringType(),
            True,
        ),
        StructField(
            "replay",
            BooleanType(),
            True,
        ),
        StructField(
            "source_timestamp",
            StringType(),
            True,
        ),
    ]
)


def parse_kafka_events(
    kafka_dataframe: DataFrame,
) -> DataFrame:
    """Parse Kafka records into the GridPulse Bronze schema."""

    raw = kafka_dataframe.select(
        F.col("topic"),
        F.col("partition"),
        F.col("offset"),
        F.col("timestamp").alias("kafka_timestamp"),
        F.col("key").cast("string").alias("kafka_key"),
        F.col("value").cast("string").alias("event_json"),
    )

    parsed = raw.withColumn(
        "envelope",
        F.from_json(
            F.col("event_json"),
            EVENT_ENVELOPE_SCHEMA,
        ),
    )

    flattened = parsed.select(
        "topic",
        "partition",
        "offset",
        "kafka_timestamp",
        "kafka_key",
        "event_json",
        F.col("envelope.event_id").alias("event_id"),
        F.col("envelope.event_version").alias("event_version"),
        F.col("envelope.source").alias("source"),
        F.col("envelope.dataset").alias("dataset"),
        F.col("envelope.event_type").alias("event_type"),
        F.col("envelope.partition_key").alias("partition_key"),
        F.col("envelope.emitted_at").alias("emitted_at"),
        F.col("envelope.replay").alias("replay"),
        F.col("envelope.source_timestamp").alias("source_timestamp"),
        F.get_json_object(
            F.col("event_json"),
            "$.payload",
        ).alias("payload_json"),
    )

    validation_error = (
        F.when(
            F.col("event_id").isNull() | (F.length(F.trim(F.col("event_id"))) == 0),
            F.lit("missing_or_invalid_event_id"),
        )
        .when(
            F.col("event_version").isNull() | (F.col("event_version") != "1.0"),
            F.lit("unsupported_event_version"),
        )
        .when(
            F.col("source").isNull() | (~F.col("source").isin(*VALID_EVENT_SOURCES)),
            F.lit("missing_or_invalid_source"),
        )
        .when(
            F.col("dataset").isNull() | (F.length(F.trim(F.col("dataset"))) == 0),
            F.lit("missing_or_invalid_dataset"),
        )
        .when(
            F.col("event_type").isNull() | (F.length(F.trim(F.col("event_type"))) == 0),
            F.lit("missing_or_invalid_event_type"),
        )
        .when(
            F.col("partition_key").isNull() | (F.length(F.trim(F.col("partition_key"))) == 0),
            F.lit("missing_or_invalid_partition_key"),
        )
        .when(
            F.col("emitted_at").isNull() | (F.length(F.trim(F.col("emitted_at"))) == 0),
            F.lit("missing_or_invalid_emitted_at"),
        )
        .when(
            F.col("replay").isNull(),
            F.lit("missing_or_invalid_replay"),
        )
        .when(
            F.col("payload_json").isNull(),
            F.lit("missing_or_invalid_payload"),
        )
    )

    return (
        flattened.withColumn(
            "validation_error",
            validation_error,
        )
        .withColumn(
            "is_valid",
            F.col("validation_error").isNull(),
        )
        .withColumn(
            "kafka_date",
            F.to_date(F.col("kafka_timestamp")),
        )
    )
