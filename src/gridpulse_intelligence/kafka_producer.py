"""Kafka event producer for GridPulse Intelligence."""

import json

import structlog
from confluent_kafka import (
    KafkaError,
    Message,
    Producer,
)

from gridpulse_intelligence.config import get_settings
from gridpulse_intelligence.events import EventEnvelope

logger = structlog.get_logger(__name__)


class KafkaPublishError(Exception):
    """Raised when an event cannot be delivered to Kafka."""


class KafkaEventProducer:
    """Publish canonical GridPulse events to Kafka."""

    def __init__(self) -> None:
        settings = get_settings()

        self._delivery_errors: list[str] = []

        self._producer = Producer(
            {
                "bootstrap.servers": (settings.kafka_bootstrap_servers),
                "client.id": "gridpulse-intelligence",
                "enable.idempotence": True,
                "acks": "all",
            }
        )

    def _delivery_callback(
        self,
        error: KafkaError | None,
        message: Message,
    ) -> None:
        """Handle asynchronous Kafka delivery reports."""

        if error is not None:
            error_message = str(error)

            self._delivery_errors.append(error_message)

            logger.error(
                "kafka_delivery_failed",
                error=error_message,
            )

            return

        logger.info(
            "kafka_event_delivered",
            topic=message.topic(),
            partition=message.partition(),
            offset=message.offset(),
        )

    @staticmethod
    def serialize_event(
        event: EventEnvelope,
    ) -> bytes:
        """Serialize a canonical event to deterministic JSON."""

        payload = event.model_dump(
            mode="json",
        )

        return json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    def publish(
        self,
        topic: str,
        event: EventEnvelope,
    ) -> None:
        """Queue an event for Kafka delivery."""

        if not topic.strip():
            raise ValueError("Kafka topic must not be empty")

        try:
            self._producer.produce(
                topic=topic,
                key=event.partition_key.encode("utf-8"),
                value=self.serialize_event(event),
                on_delivery=self._delivery_callback,
            )

        except BufferError as exc:
            raise KafkaPublishError("Kafka producer queue is full.") from exc

        self._producer.poll(0)

        logger.info(
            "kafka_event_queued",
            topic=topic,
            event_id=str(event.event_id),
            source=event.source,
            dataset=event.dataset,
            partition_key=event.partition_key,
            replay=event.replay,
        )

    def flush(
        self,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Wait for queued events to be delivered."""

        remaining = self._producer.flush(timeout_seconds)

        if remaining != 0:
            raise KafkaPublishError(
                f"{remaining} Kafka message(s) were not delivered before timeout."
            )

        if self._delivery_errors:
            errors = "; ".join(self._delivery_errors)

            self._delivery_errors.clear()

            raise KafkaPublishError(f"Kafka delivery failed: {errors}")

        logger.info("kafka_flush_completed")
