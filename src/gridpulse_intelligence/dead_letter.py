"""Dead-letter records for failed GridPulse Kafka messages."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeadLetterRecord(BaseModel):
    """Message captured after Kafka event processing fails."""

    model_config = ConfigDict(
        extra="forbid",
    )

    original_topic: str
    original_partition: int
    original_offset: int

    failure_reason: str

    failed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    raw_key: str | None = None
    raw_value: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
