"""Tests for canonical GridPulse event envelopes."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from gridpulse_intelligence.events import EventEnvelope


def test_event_envelope_generates_metadata() -> None:
    """Canonical events should receive IDs and emission timestamps."""

    event = EventEnvelope(
        source="eia",
        dataset="eia_region_data",
        event_type="eia.region_data.observed",
        partition_key="PJM",
        replay=False,
        source_timestamp="2026-08-12T00:00:00",
        payload={
            "respondent": "PJM",
            "value": 1000.0,
        },
    )

    assert event.event_version == "1.0"
    assert event.event_id is not None
    assert event.emitted_at.tzinfo is not None


def test_historical_event_can_be_marked_as_replay() -> None:
    """Historical replay must be explicitly represented."""

    event = EventEnvelope(
        source="eia",
        dataset="eia_region_data",
        event_type="eia.region_data.observed",
        partition_key="PJM",
        replay=True,
        source_timestamp="2026-08-10T05:00:00",
        payload={
            "respondent": "PJM",
            "value": 950.0,
        },
    )

    assert event.replay is True


def test_empty_partition_key_fails() -> None:
    """Events without partition keys should be rejected."""

    with pytest.raises(
        ValidationError,
        match="event identifier",
    ):
        EventEnvelope(
            source="nws",
            dataset="nws_hourly_forecast",
            event_type="nws.forecast.hourly",
            partition_key=" ",
            payload={
                "temperature": 80,
            },
        )


def test_naive_emitted_at_fails() -> None:
    """Emission timestamps must identify an absolute instant."""

    with pytest.raises(
        ValidationError,
        match="timezone-aware",
    ):
        EventEnvelope(
            source="afdc",
            dataset="afdc_ev_stations",
            event_type="afdc.station.snapshot",
            partition_key="OH",
            emitted_at=datetime(
                2026,
                8,
                12,
                1,
                0,
            ),
            payload={
                "station_id": 37097,
            },
        )
