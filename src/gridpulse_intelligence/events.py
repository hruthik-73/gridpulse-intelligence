"""Canonical event models for GridPulse streaming."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

type EventSource = Literal["eia", "nws", "afdc"]


class EventEnvelope(BaseModel):
    """Canonical envelope shared by GridPulse Kafka events."""

    model_config = ConfigDict(
        extra="forbid",
    )

    event_id: UUID = Field(
        default_factory=uuid4,
    )

    event_version: Literal["1.0"] = "1.0"

    source: EventSource
    dataset: str
    event_type: str
    partition_key: str

    emitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    replay: bool = False

    source_timestamp: str | None = None

    payload: dict[str, Any]

    @field_validator(
        "dataset",
        "event_type",
        "partition_key",
    )
    @classmethod
    def validate_non_empty_text(
        cls,
        value: str,
    ) -> str:
        """Reject empty event identifiers."""

        cleaned = value.strip()

        if not cleaned:
            raise ValueError("event identifier fields must not be empty")

        return cleaned

    @field_validator("emitted_at")
    @classmethod
    def require_timezone(
        cls,
        value: datetime,
    ) -> datetime:
        """Require an unambiguous event emission timestamp."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("emitted_at must be timezone-aware")

        return value
