"""Convert validated GridPulse records into canonical Kafka events."""

from gridpulse_intelligence.events import EventEnvelope
from gridpulse_intelligence.models import (
    EVChargingStationRecord,
    GridRegionRecord,
    WeatherForecastRecord,
)

EIA_TOPIC = "gridpulse.eia.region-data.v1"
NWS_TOPIC = "gridpulse.nws.forecast.v1"
AFDC_TOPIC = "gridpulse.afdc.ev-stations.v1"


def create_eia_event(
    record: GridRegionRecord,
    replay: bool = False,
) -> EventEnvelope:
    """Create a canonical event from an EIA electricity record."""

    return EventEnvelope(
        source="eia",
        dataset="eia_region_data",
        event_type="eia.region_data.observed",
        partition_key=record.respondent,
        replay=replay,
        source_timestamp=record.period.isoformat(),
        payload=record.model_dump(
            mode="json",
        ),
    )


def create_nws_event(
    record: WeatherForecastRecord,
    replay: bool = False,
) -> EventEnvelope:
    """Create a canonical event from an NWS forecast record."""

    location_key = f"{record.latitude:.4f},{record.longitude:.4f}"

    return EventEnvelope(
        source="nws",
        dataset="nws_hourly_forecast",
        event_type="nws.forecast.hourly",
        partition_key=location_key,
        replay=replay,
        source_timestamp=record.period_start.isoformat(),
        payload=record.model_dump(
            mode="json",
        ),
    )


def create_afdc_event(
    record: EVChargingStationRecord,
    replay: bool = False,
) -> EventEnvelope:
    """Create a canonical event from an AFDC EV station record."""

    source_timestamp: str | None = None

    if record.updated_at is not None:
        source_timestamp = record.updated_at.isoformat()
    elif record.date_last_confirmed is not None:
        source_timestamp = record.date_last_confirmed.isoformat()

    return EventEnvelope(
        source="afdc",
        dataset="afdc_ev_stations",
        event_type="afdc.ev_station.snapshot",
        partition_key=record.state,
        replay=replay,
        source_timestamp=source_timestamp,
        payload=record.model_dump(
            mode="json",
        ),
    )
