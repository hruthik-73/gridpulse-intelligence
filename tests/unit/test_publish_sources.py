"""Tests for publishing source records to Kafka."""

from datetime import datetime

import pytest

import gridpulse_intelligence.publish_sources as publish_sources
from gridpulse_intelligence.event_factory import (
    AFDC_TOPIC,
    EIA_TOPIC,
    NWS_TOPIC,
)
from gridpulse_intelligence.models import (
    EVChargingStationRecord,
    GridRegionRecord,
    WeatherForecastRecord,
)


class FakeProducer:
    """Capture Kafka events without a real broker."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, object]] = []
        self.flush_count = 0

    def publish(
        self,
        topic: str,
        event: object,
    ) -> None:
        self.messages.append(
            (
                topic,
                event,
            )
        )

    def flush(self) -> None:
        self.flush_count += 1


def test_publish_eia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """EIA records should publish to the EIA topic."""

    record = GridRegionRecord.model_validate(
        {
            "period": "2026-08-10T05",
            "respondent": "PJM",
            "respondent-name": "PJM Interconnection",
            "type": "D",
            "type-name": "Demand",
            "value": "1000",
            "value-units": "megawatthours",
        }
    )

    class FakeEIAClient:
        def get_latest_region_data(
            self,
            length: int,
        ) -> list[GridRegionRecord]:
            assert length == 1
            return [record]

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        publish_sources,
        "EIAClient",
        FakeEIAClient,
    )

    producer = FakeProducer()

    count = publish_sources.publish_eia(
        producer=producer,  # type: ignore[arg-type]
        limit=1,
    )

    assert count == 1
    assert producer.flush_count == 1
    assert producer.messages[0][0] == EIA_TOPIC

    event = producer.messages[0][1]

    assert event.source == "eia"
    assert event.replay is False


def test_publish_nws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NWS records should publish to the weather topic."""

    record = WeatherForecastRecord(
        latitude=41.4993,
        longitude=-81.6944,
        period_start=datetime.fromisoformat("2026-08-11T14:00:00-04:00"),
        period_end=datetime.fromisoformat("2026-08-11T15:00:00-04:00"),
        temperature=80,
        temperature_unit="F",
        precipitation_probability=40,
        relative_humidity=72,
        wind_speed="8 mph",
        wind_direction="SW",
        short_forecast="Chance Thunderstorms",
    )

    class FakeNWSClient:
        def get_hourly_forecast(
            self,
            latitude: float,
            longitude: float,
            limit: int,
        ) -> list[WeatherForecastRecord]:
            assert latitude == 41.4993
            assert longitude == -81.6944
            assert limit == 1

            return [record]

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        publish_sources,
        "NWSClient",
        FakeNWSClient,
    )

    producer = FakeProducer()

    count = publish_sources.publish_nws(
        producer=producer,  # type: ignore[arg-type]
        latitude=41.4993,
        longitude=-81.6944,
        hours=1,
    )

    assert count == 1
    assert producer.flush_count == 1
    assert producer.messages[0][0] == NWS_TOPIC

    event = producer.messages[0][1]

    assert event.source == "nws"
    assert event.replay is False


def test_publish_afdc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AFDC records should publish to the EV topic."""

    record = EVChargingStationRecord(
        station_id=37097,
        station_name="Baker Electric Building",
        city="Cleveland",
        state="OH",
        zip_code="44114",
        country="US",
        latitude=41.4993,
        longitude=-81.6944,
        fuel_type_code="ELEC",
        access_code="public",
        status_code="E",
        ev_connector_types=["J1772"],
    )

    class FakeAFDCClient:
        MAX_LIMIT = 200

        def get_public_ev_stations(
            self,
            state: str,
            limit: int,
        ) -> tuple[
            list[EVChargingStationRecord],
            int,
        ]:
            assert state == "OH"
            assert limit == 1

            return [record], 1916

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        publish_sources,
        "AFDCClient",
        FakeAFDCClient,
    )

    producer = FakeProducer()

    count = publish_sources.publish_afdc(
        producer=producer,  # type: ignore[arg-type]
        state="OH",
        limit=1,
    )

    assert count == 1
    assert producer.flush_count == 1
    assert producer.messages[0][0] == AFDC_TOPIC

    event = producer.messages[0][1]

    assert event.source == "afdc"
    assert event.replay is False


def test_run_publish_all_invokes_all_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The all mode should publish every configured source."""

    calls: list[str] = []

    class FakeKafkaProducer:
        pass

    def fake_eia(
        producer: object,
        limit: int,
    ) -> int:
        del producer
        assert limit == 2
        calls.append("eia")
        return 2

    def fake_nws(
        producer: object,
        latitude: float,
        longitude: float,
        hours: int,
    ) -> int:
        del producer
        assert latitude == 41.4993
        assert longitude == -81.6944
        assert hours == 3

        calls.append("nws")
        return 3

    def fake_afdc(
        producer: object,
        state: str,
        limit: int,
    ) -> int:
        del producer
        assert state == "OH"
        assert limit == 4

        calls.append("afdc")
        return 4

    monkeypatch.setattr(
        publish_sources,
        "KafkaEventProducer",
        FakeKafkaProducer,
    )

    monkeypatch.setattr(
        publish_sources,
        "publish_eia",
        fake_eia,
    )

    monkeypatch.setattr(
        publish_sources,
        "publish_nws",
        fake_nws,
    )

    monkeypatch.setattr(
        publish_sources,
        "publish_afdc",
        fake_afdc,
    )

    counts = publish_sources.run_publish(
        source="all",
        eia_limit=2,
        latitude=41.4993,
        longitude=-81.6944,
        weather_hours=3,
        state="OH",
        ev_limit=4,
    )

    assert calls == [
        "eia",
        "nws",
        "afdc",
    ]

    assert counts == {
        "eia": 2,
        "nws": 3,
        "afdc": 4,
    }
