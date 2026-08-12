"""Tests for historical EIA Kafka replay."""

from datetime import datetime

import pytest

from gridpulse_intelligence.event_factory import (
    EIA_TOPIC,
)
from gridpulse_intelligence.events import EventEnvelope
from gridpulse_intelligence.models import GridRegionRecord
from gridpulse_intelligence.replay_eia import (
    calculate_replay_delay,
    replay_records,
    sort_records,
)


class FakeProducer:
    """Capture replayed events without Kafka."""

    def __init__(self) -> None:
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


def make_record(
    period: str,
    respondent: str,
    record_type: str = "D",
) -> GridRegionRecord:
    """Create a valid historical EIA record."""

    return GridRegionRecord.model_validate(
        {
            "period": period,
            "respondent": respondent,
            "respondent-name": (f"{respondent} Balancing Authority"),
            "type": record_type,
            "type-name": "Demand",
            "value": "1000",
            "value-units": "megawatthours",
        }
    )


def test_calculate_replay_delay() -> None:
    """Replay speed should scale source-time distance."""

    previous = datetime(
        2026,
        8,
        10,
        5,
    )

    current = datetime(
        2026,
        8,
        10,
        6,
    )

    assert (
        calculate_replay_delay(
            previous_period=previous,
            current_period=current,
            speed=3600,
        )
        == 1.0
    )


def test_same_period_has_no_delay() -> None:
    """Records within the same source hour should not sleep."""

    period = datetime(
        2026,
        8,
        10,
        5,
    )

    assert (
        calculate_replay_delay(
            previous_period=period,
            current_period=period,
            speed=3600,
        )
        == 0.0
    )


def test_sort_records_is_deterministic() -> None:
    """Replay records should be ordered by event-time and identity."""

    records = [
        make_record(
            "2026-08-10T06",
            "PJM",
        ),
        make_record(
            "2026-08-10T05",
            "MISO",
        ),
        make_record(
            "2026-08-10T05",
            "AECI",
        ),
    ]

    ordered = sort_records(records)

    assert [
        (
            record.period,
            record.respondent,
        )
        for record in ordered
    ] == [
        (
            datetime(
                2026,
                8,
                10,
                5,
            ),
            "AECI",
        ),
        (
            datetime(
                2026,
                8,
                10,
                5,
            ),
            "MISO",
        ),
        (
            datetime(
                2026,
                8,
                10,
                6,
            ),
            "PJM",
        ),
    ]


def test_replay_marks_events_as_historical() -> None:
    """Every replayed event must explicitly use replay=true."""

    records = [
        make_record(
            "2026-08-10T05",
            "PJM",
        )
    ]

    producer = FakeProducer()

    published = replay_records(
        records=records,
        producer=producer,  # type: ignore[arg-type]
        speed=3600,
        sleep_function=lambda _: None,
    )

    assert published == 1
    assert len(producer.messages) == 1

    topic, event = producer.messages[0]

    assert topic == EIA_TOPIC
    assert event.replay is True
    assert event.source_timestamp == "2026-08-10T05:00:00"


def test_replay_waits_between_source_hours() -> None:
    """Replay timing should follow event-time differences."""

    records = [
        make_record(
            "2026-08-10T05",
            "AECI",
        ),
        make_record(
            "2026-08-10T05",
            "PJM",
        ),
        make_record(
            "2026-08-10T06",
            "AECI",
        ),
    ]

    producer = FakeProducer()

    delays: list[float] = []

    replay_records(
        records=records,
        producer=producer,  # type: ignore[arg-type]
        speed=3600,
        sleep_function=delays.append,
    )

    assert delays == [
        1.0,
    ]

    assert len(producer.messages) == 3

    assert all(event.replay for _, event in producer.messages)


def test_invalid_speed_fails() -> None:
    """Replay speed must always be positive."""

    with pytest.raises(
        ValueError,
        match="speed",
    ):
        calculate_replay_delay(
            previous_period=datetime(
                2026,
                8,
                10,
                5,
            ),
            current_period=datetime(
                2026,
                8,
                10,
                6,
            ),
            speed=0,
        )
