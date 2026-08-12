"""Validated Kafka consumer for GridPulse Intelligence."""

import json
from collections.abc import Callable
from typing import Final

import structlog
from confluent_kafka import Consumer, KafkaError, Message
from pydantic import ValidationError

from gridpulse_intelligence.config import get_settings
from gridpulse_intelligence.dead_letter import DeadLetterRecord
from gridpulse_intelligence.events import EventEnvelope
from gridpulse_intelligence.kafka_producer import KafkaEventProducer

logger = structlog.get_logger(__name__)

DEFAULT_TOPICS: Final[tuple[str, ...]] = (
    "gridpulse.eia.region-data.v1",
    "gridpulse.nws.forecast.v1",
    "gridpulse.afdc.ev-stations.v1",
)

DEAD_LETTER_TOPIC: Final[str] = "gridpulse.dead-letter.v1"

EventHandler = Callable[[EventEnvelope], None]


class KafkaConsumerError(Exception):
    """Raised when Kafka consumption cannot continue safely."""


def deserialize_event(
    raw_value: bytes | None,
) -> EventEnvelope:
    """Deserialize and validate one canonical GridPulse event."""

    if raw_value is None:
        raise KafkaConsumerError("Kafka message value is empty.")

    try:
        decoded = raw_value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise KafkaConsumerError("Kafka message is not valid UTF-8.") from exc

    try:
        payload: object = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise KafkaConsumerError("Kafka message contains invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise KafkaConsumerError("Kafka event root must be a JSON object.")

    try:
        return EventEnvelope.model_validate(payload)
    except ValidationError as exc:
        raise KafkaConsumerError("Kafka event failed EventEnvelope validation.") from exc


def default_event_handler(
    event: EventEnvelope,
) -> None:
    """Handle a validated GridPulse event."""

    logger.info(
        "gridpulse_event_processed",
        event_id=str(event.event_id),
        source=event.source,
        dataset=event.dataset,
        event_type=event.event_type,
        partition_key=event.partition_key,
        replay=event.replay,
    )


class GridPulseKafkaConsumer:
    """Consume, validate, process, and commit GridPulse events."""

    def __init__(
        self,
        group_id: str = "gridpulse-validation-consumer-v1",
        event_handler: EventHandler = default_event_handler,
    ) -> None:
        settings = get_settings()

        self._consumer = Consumer(
            {
                "bootstrap.servers": (settings.kafka_bootstrap_servers),
                "group.id": group_id,
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
                "client.id": "gridpulse-consumer",
            }
        )

        self._dead_letter_producer = KafkaEventProducer()

        self._event_handler = event_handler

    def subscribe(
        self,
        topics: tuple[str, ...] = DEFAULT_TOPICS,
    ) -> None:
        """Subscribe to GridPulse source topics."""

        if not topics:
            raise ValueError("At least one Kafka topic is required.")

        self._consumer.subscribe(list(topics))

        logger.info(
            "kafka_consumer_subscribed",
            topics=list(topics),
        )

    @staticmethod
    def _safe_decode(
        value: bytes | None,
    ) -> str | None:
        """Decode Kafka bytes safely for DLQ storage."""

        if value is None:
            return None

        return value.decode(
            "utf-8",
            errors="replace",
        )

    def _publish_dead_letter(
        self,
        message: Message,
        reason: str,
    ) -> None:
        """Publish an invalid source message to the DLQ."""

        dead_letter = DeadLetterRecord(
            original_topic=message.topic(),
            original_partition=message.partition(),
            original_offset=message.offset(),
            failure_reason=reason,
            raw_key=self._safe_decode(message.key()),
            raw_value=self._safe_decode(message.value()),
        )

        event = EventEnvelope(
            source="platform",
            dataset="gridpulse_dead_letter",
            event_type="gridpulse.dead_letter",
            partition_key=message.topic(),
            replay=False,
            payload=dead_letter.model_dump(mode="json"),
        )

        self._dead_letter_producer.publish(
            DEAD_LETTER_TOPIC,
            event,
        )

        self._dead_letter_producer.flush()

        logger.warning(
            "kafka_message_dead_lettered",
            original_topic=message.topic(),
            partition=message.partition(),
            offset=message.offset(),
            reason=reason,
        )

    def process_message(
        self,
        message: Message,
    ) -> EventEnvelope | None:
        """Validate, process, and safely commit one Kafka message."""

        error = message.error()

        if error is not None:
            if error.code() == KafkaError._PARTITION_EOF:
                return None

            raise KafkaConsumerError(f"Kafka consumer error: {error}")

        try:
            event = deserialize_event(message.value())

            self._event_handler(event)

        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"

            self._publish_dead_letter(
                message=message,
                reason=reason,
            )

            self._consumer.commit(
                message=message,
                asynchronous=False,
            )

            logger.info(
                "kafka_dlq_offset_committed",
                topic=message.topic(),
                partition=message.partition(),
                offset=message.offset(),
            )

            return None

        self._consumer.commit(
            message=message,
            asynchronous=False,
        )

        logger.info(
            "kafka_offset_committed",
            topic=message.topic(),
            partition=message.partition(),
            offset=message.offset(),
            event_id=str(event.event_id),
        )

        return event

    def run(
        self,
        max_messages: int | None = None,
        poll_timeout: float = 1.0,
    ) -> int:
        """Consume messages until interrupted or a limit is reached."""

        if max_messages is not None and max_messages < 1:
            raise ValueError("max_messages must be greater than zero")

        handled = 0

        try:
            while max_messages is None or handled < max_messages:
                message = self._consumer.poll(poll_timeout)

                if message is None:
                    continue

                self.process_message(message)

                handled += 1

        except KeyboardInterrupt:
            logger.info("kafka_consumer_interrupted")

        finally:
            self.close()

        return handled

    def close(self) -> None:
        """Close Kafka consumer resources."""

        self._consumer.close()

        logger.info("kafka_consumer_closed")
