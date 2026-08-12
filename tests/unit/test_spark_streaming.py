"""Tests for GridPulse Spark streaming transformations."""

import json

import pytest
from pyspark.sql import SparkSession

from gridpulse_intelligence.spark_streaming import (
    parse_kafka_events,
)


@pytest.fixture(scope="module")
def spark() -> SparkSession:
    """Create a local Spark session for transformation tests."""

    session = (
        SparkSession.builder.master("local[2]")
        .appName("gridpulse-spark-streaming-tests")
        .config(
            "spark.sql.shuffle.partitions",
            "2",
        )
        .getOrCreate()
    )

    session.sparkContext.setLogLevel("ERROR")

    yield session

    session.stop()


def make_event_json(
    source: str = "eia",
) -> str:
    """Create a canonical GridPulse event JSON document."""

    return json.dumps(
        {
            "event_id": ("550e8400-e29b-41d4-a716-446655440000"),
            "event_version": "1.0",
            "source": source,
            "dataset": "eia_region_data",
            "event_type": ("eia.region_data.observed"),
            "partition_key": "PJM",
            "emitted_at": ("2026-08-11T20:00:00+00:00"),
            "replay": True,
            "source_timestamp": ("2026-08-10T05:00:00"),
            "payload": {
                "respondent": "PJM",
                "value": 1000.0,
            },
        }
    )


def test_valid_event_is_parsed(
    spark: SparkSession,
) -> None:
    """A canonical event should enter the valid Bronze path."""

    dataframe = spark.createDataFrame(
        [
            (
                "gridpulse.eia.region-data.v1",
                0,
                12,
                None,
                b"PJM",
                make_event_json().encode("utf-8"),
            )
        ],
        schema=(
            "topic string, "
            "partition int, "
            "offset long, "
            "timestamp timestamp, "
            "key binary, "
            "value binary"
        ),
    )

    result = parse_kafka_events(dataframe).collect()[0]

    assert result["is_valid"] is True
    assert result["validation_error"] is None
    assert result["source"] == "eia"
    assert result["partition_key"] == "PJM"
    assert result["replay"] is True


def test_payload_json_is_preserved(
    spark: SparkSession,
) -> None:
    """Bronze should preserve the source-specific payload."""

    dataframe = spark.createDataFrame(
        [
            (
                "gridpulse.eia.region-data.v1",
                0,
                13,
                None,
                b"PJM",
                make_event_json().encode("utf-8"),
            )
        ],
        schema=(
            "topic string, "
            "partition int, "
            "offset long, "
            "timestamp timestamp, "
            "key binary, "
            "value binary"
        ),
    )

    result = parse_kafka_events(dataframe).collect()[0]

    payload = json.loads(result["payload_json"])

    assert payload["respondent"] == "PJM"
    assert payload["value"] == 1000.0


def test_invalid_json_is_quarantined(
    spark: SparkSession,
) -> None:
    """Malformed JSON should fail Bronze validation."""

    dataframe = spark.createDataFrame(
        [
            (
                "gridpulse.eia.region-data.v1",
                1,
                20,
                None,
                b"PJM",
                b"{invalid-json",
            )
        ],
        schema=(
            "topic string, "
            "partition int, "
            "offset long, "
            "timestamp timestamp, "
            "key binary, "
            "value binary"
        ),
    )

    result = parse_kafka_events(dataframe).collect()[0]

    assert result["is_valid"] is False
    assert result["validation_error"] == "missing_or_invalid_event_id"


def test_unknown_source_is_rejected(
    spark: SparkSession,
) -> None:
    """Unknown event sources must not enter Bronze."""

    dataframe = spark.createDataFrame(
        [
            (
                "gridpulse.unknown.v1",
                0,
                30,
                None,
                b"UNKNOWN",
                make_event_json(source="unknown").encode("utf-8"),
            )
        ],
        schema=(
            "topic string, "
            "partition int, "
            "offset long, "
            "timestamp timestamp, "
            "key binary, "
            "value binary"
        ),
    )

    result = parse_kafka_events(dataframe).collect()[0]

    assert result["is_valid"] is False

    assert result["validation_error"] == "missing_or_invalid_source"
