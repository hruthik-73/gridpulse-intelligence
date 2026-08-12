"""Tests for the validated GridPulse Kafka consumer."""

from typing import Any

import pytest

from gridpulse_intelligence.events import EventEnvelope
from gridpulse_intelligence.kafka_consumer import (
    DEAD_LETTER_TOPIC,
    GridPulseKafkaConsumer,
    KafkaConsumerError,
    deserialize_event,
)
from gridpulse_intelligence.kafka_producer import KafkaPublishError


class FakeMessage:
    """Minimal Kafka message implementation for consumer tests."""

    def __init__(
        self,
        value: bytes | None,
        topic: str = "gridpulse.eia.region-data.v1",
        partition: int = 0,
        offset: int = 10,
        key: bytes | None = b"PJM",
        error: Any = None,
    ) -> None:
        self._value = value
        self._topic = topic
        self._partition = partition
        self._offset = offset
        self._key = key
        self._error = error

    def value(self) -> bytes | None:
        return self._value

    def key(self) -> bytes | None:
        return self._key

    def topic(self) -> str:
        return self._topic

    def partition(self) -> int:
        return self._partition

    def offset(self) -> int:
        return self._offset

    def error(self) -> Any:
        return self._error


class FakeConsumer:
    """Capture manual Kafka offset commits."""

    def __init__(self) -> None:
        self.commits: list[dict[str, object]] = []

    def commit(
        self,
        message: object,
        asynchronous: bool,
    ) -> None:
        self.commits.append(
            {
                "message": message,
                "asynchronous": asynchronous,
            }
        )

    def close(self) -> None:
        pass


class FakeDeadLetterProducer:
    """Capture dead-letter events without a real Kafka broker."""

    def __init__(
        self,
        fail_flush: bool = False,
    ) -> None:
        self.fail_flush = fail_flush
        self.messages: list[tuple[str, EventEnvelope]] = []
        self.flush_count = 0

    def publish(
        self,
        topic: str,
        event: EventEnvelope,
    ) -> None:
        self.messages.append(
            (
                topic,
                event,
            )
        )

    def flush(self) -> None:
        self.flush_count += 1

        if self.fail_flush:
            raise KafkaPublishError("Simulated DLQ delivery failure.")


def valid_event_bytes() -> bytes:
    """Return a valid serialized GridPulse event."""

    event = EventEnvelope(
        source="eia",
        dataset="eia_region_data",
        event_type="eia.region_data.observed",
        partition_key="PJM",
        replay=False,
        source_timestamp="2026-08-12T01:00:00",
        payload={
            "respondent": "PJM",
            "value": 1000.0,
        },
    )

    return event.model_dump_json().encode("utf-8")


def make_consumer(
    event_handler: Any = None,
    dlq_failure: bool = False,
) -> tuple[
    GridPulseKafkaConsumer,
    FakeConsumer,
    FakeDeadLetterProducer,
]:
    """Create a Kafka consumer without connecting to Kafka."""

    consumer = object.__new__(GridPulseKafkaConsumer)

    fake_consumer = FakeConsumer()

    dead_letter_producer = FakeDeadLetterProducer(
        fail_flush=dlq_failure,
    )

    consumer._consumer = fake_consumer  # type: ignore[assignment]
    consumer._dead_letter_producer = dead_letter_producer  # type: ignore[assignment]

    if event_handler is None:
        consumer._event_handler = lambda event: None
    else:
        consumer._event_handler = event_handler

    return (
        consumer,
        fake_consumer,
        dead_letter_producer,
    )


def test_deserialize_valid_event() -> None:
    """Valid canonical JSON should deserialize successfully."""

    event = deserialize_event(valid_event_bytes())

    assert event.source == "eia"
    assert event.dataset == "eia_region_data"
    assert event.partition_key == "PJM"


def test_deserialize_invalid_json_fails() -> None:
    """Invalid JSON should never enter event processing."""

    with pytest.raises(
        KafkaConsumerError,
        match="invalid JSON",
    ):
        deserialize_event(b"{invalid-json")


def test_empty_message_value_fails() -> None:
    """Kafka tombstones are invalid for source event topics."""

    with pytest.raises(
        KafkaConsumerError,
        match="value is empty",
    ):
        deserialize_event(None)


def test_valid_message_is_processed_then_committed() -> None:
    """Valid events should commit only after the handler succeeds."""

    processed: list[EventEnvelope] = []

    def handler(
        event: EventEnvelope,
    ) -> None:
        processed.append(event)

    (
        consumer,
        fake_consumer,
        dead_letter_producer,
    ) = make_consumer(
        event_handler=handler,
    )

    message = FakeMessage(
        value=valid_event_bytes(),
    )

    result = consumer.process_message(  # type: ignore[arg-type]
        message
    )

    assert result is not None
    assert len(processed) == 1

    assert len(fake_consumer.commits) == 1
    assert fake_consumer.commits[0]["asynchronous"] is False

    assert dead_letter_producer.messages == []


def test_invalid_message_is_dead_lettered_before_commit() -> None:
    """Invalid events should enter the DLQ before their offset commits."""

    (
        consumer,
        fake_consumer,
        dead_letter_producer,
    ) = make_consumer()

    message = FakeMessage(
        value=b"{invalid-json",
        topic="gridpulse.eia.region-data.v1",
        partition=2,
        offset=42,
        key=b"PJM",
    )

    result = consumer.process_message(  # type: ignore[arg-type]
        message
    )

    assert result is None

    assert len(dead_letter_producer.messages) == 1

    topic, event = dead_letter_producer.messages[0]

    assert topic == DEAD_LETTER_TOPIC

    assert event.source == "platform"
    assert event.dataset == "gridpulse_dead_letter"
    assert event.event_type == "gridpulse.dead_letter"

    assert event.payload["original_topic"] == "gridpulse.eia.region-data.v1"

    assert event.payload["original_partition"] == 2

    assert event.payload["original_offset"] == 42
    assert event.payload["raw_key"] == "PJM"
    assert event.payload["raw_value"] == "{invalid-json"

    assert dead_letter_producer.flush_count == 1

    assert len(fake_consumer.commits) == 1
    assert fake_consumer.commits[0]["asynchronous"] is False


def test_dlq_failure_does_not_commit_source_offset() -> None:
    """A failed DLQ publish must leave the source message retryable."""

    (
        consumer,
        fake_consumer,
        dead_letter_producer,
    ) = make_consumer(
        dlq_failure=True,
    )

    message = FakeMessage(
        value=b"{invalid-json",
        offset=99,
    )

    with pytest.raises(
        KafkaPublishError,
        match="Simulated DLQ delivery failure",
    ):
        consumer.process_message(  # type: ignore[arg-type]
            message
        )

    assert dead_letter_producer.flush_count == 1

    assert fake_consumer.commits == []
