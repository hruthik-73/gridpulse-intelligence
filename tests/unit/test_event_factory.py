"""Tests for source-record to Kafka-event conversion."""

from datetime import datetime

from gridpulse_intelligence.event_factory import (
    AFDC_TOPIC,
    EIA_TOPIC,
    NWS_TOPIC,
    create_afdc_event,
    create_eia_event,
    create_nws_event,
)
from gridpulse_intelligence.models import (
    EVChargingStationRecord,
    GridRegionRecord,
    WeatherForecastRecord,
)


def test_topic_names_are_versioned() -> None:
    """Kafka topic names should expose explicit schema versions."""

    assert EIA_TOPIC == "gridpulse.eia.region-data.v1"
    assert NWS_TOPIC == "gridpulse.nws.forecast.v1"
    assert AFDC_TOPIC == "gridpulse.afdc.ev-stations.v1"


def test_create_eia_event() -> None:
    """EIA records should map to respondent-partitioned events."""

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

    event = create_eia_event(
        record,
        replay=True,
    )

    assert event.source == "eia"
    assert event.dataset == "eia_region_data"
    assert event.partition_key == "PJM"
    assert event.replay is True
    assert event.source_timestamp == "2026-08-10T05:00:00"
    assert event.payload["value"] == 1000.0


def test_create_nws_event() -> None:
    """Weather records should use coordinates as partition keys."""

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

    event = create_nws_event(record)

    assert event.source == "nws"
    assert event.dataset == "nws_hourly_forecast"
    assert event.partition_key == "41.4993,-81.6944"
    assert event.replay is False
    assert event.source_timestamp == "2026-08-11T14:00:00-04:00"
    assert event.payload["temperature"] == 80.0


def test_create_afdc_event() -> None:
    """EV stations should map to state-partitioned events."""

    record = EVChargingStationRecord(
        station_id=37097,
        station_name="Baker Electric Building",
        street_address="123 Main Street",
        city="Cleveland",
        state="OH",
        zip_code="44114",
        country="US",
        latitude=41.4993,
        longitude=-81.6944,
        fuel_type_code="ELEC",
        access_code="public",
        status_code="E",
        ev_network="Non-Networked",
        ev_connector_types=["J1772"],
        ev_level2_evse_num=2,
        ev_dc_fast_num=0,
        date_last_confirmed="2026-08-01",
    )

    event = create_afdc_event(record)

    assert event.source == "afdc"
    assert event.dataset == "afdc_ev_stations"
    assert event.partition_key == "OH"
    assert event.replay is False
    assert event.source_timestamp == "2026-08-01"
    assert event.payload["station_id"] == 37097


def test_afdc_updated_at_is_preferred_source_timestamp() -> None:
    """AFDC updated_at should take precedence over confirmation date."""

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
        date_last_confirmed="2026-08-01",
        updated_at="2026-08-05T12:30:00Z",
    )

    event = create_afdc_event(record)

    assert event.source_timestamp == "2026-08-05T12:30:00+00:00"
