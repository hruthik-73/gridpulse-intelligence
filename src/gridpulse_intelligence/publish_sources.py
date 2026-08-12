"""Publish validated GridPulse source records to Kafka."""

import argparse

import structlog

from gridpulse_intelligence.afdc_client import AFDCClient
from gridpulse_intelligence.eia_client import EIAClient
from gridpulse_intelligence.event_factory import (
    AFDC_TOPIC,
    EIA_TOPIC,
    NWS_TOPIC,
    create_afdc_event,
    create_eia_event,
    create_nws_event,
)
from gridpulse_intelligence.kafka_producer import KafkaEventProducer
from gridpulse_intelligence.nws_client import NWSClient

logger = structlog.get_logger(__name__)


def publish_eia(
    producer: KafkaEventProducer,
    limit: int,
) -> int:
    """Publish latest EIA electricity records."""

    if limit < 1:
        raise ValueError("EIA limit must be greater than zero")

    client = EIAClient()

    try:
        records = client.get_latest_region_data(
            length=limit,
        )
    finally:
        client.close()

    if not records:
        raise RuntimeError("EIA returned no records to publish.")

    for record in records:
        event = create_eia_event(
            record,
            replay=False,
        )

        producer.publish(
            EIA_TOPIC,
            event,
        )

    producer.flush()

    logger.info(
        "eia_kafka_publish_completed",
        topic=EIA_TOPIC,
        event_count=len(records),
    )

    return len(records)


def publish_nws(
    producer: KafkaEventProducer,
    latitude: float,
    longitude: float,
    hours: int,
) -> int:
    """Publish NWS hourly forecast records."""

    if hours < 1:
        raise ValueError("Weather hours must be greater than zero")

    client = NWSClient()

    try:
        records = client.get_hourly_forecast(
            latitude=latitude,
            longitude=longitude,
            limit=hours,
        )
    finally:
        client.close()

    if not records:
        raise RuntimeError("NWS returned no records to publish.")

    for record in records:
        event = create_nws_event(
            record,
            replay=False,
        )

        producer.publish(
            NWS_TOPIC,
            event,
        )

    producer.flush()

    logger.info(
        "nws_kafka_publish_completed",
        topic=NWS_TOPIC,
        event_count=len(records),
        latitude=latitude,
        longitude=longitude,
    )

    return len(records)


def publish_afdc(
    producer: KafkaEventProducer,
    state: str,
    limit: int,
) -> int:
    """Publish AFDC public EV charging station records."""

    normalized_state = state.strip().upper()

    if len(normalized_state) != 2 or not normalized_state.isalpha():
        raise ValueError("state must be a two-letter code")

    if not 1 <= limit <= AFDCClient.MAX_LIMIT:
        raise ValueError(f"AFDC limit must be between 1 and {AFDCClient.MAX_LIMIT}")

    client = AFDCClient()

    try:
        records, total_results = client.get_public_ev_stations(
            state=normalized_state,
            limit=limit,
        )
    finally:
        client.close()

    if not records:
        raise RuntimeError("AFDC returned no records to publish.")

    for record in records:
        event = create_afdc_event(
            record,
            replay=False,
        )

        producer.publish(
            AFDC_TOPIC,
            event,
        )

    producer.flush()

    logger.info(
        "afdc_kafka_publish_completed",
        topic=AFDC_TOPIC,
        event_count=len(records),
        total_results=total_results,
        state=normalized_state,
    )

    return len(records)


def run_publish(
    source: str,
    eia_limit: int,
    latitude: float,
    longitude: float,
    weather_hours: int,
    state: str,
    ev_limit: int,
) -> dict[str, int]:
    """Publish one or more GridPulse sources."""

    if source not in {
        "eia",
        "nws",
        "afdc",
        "all",
    }:
        raise ValueError("source must be eia, nws, afdc, or all")

    producer = KafkaEventProducer()

    counts: dict[str, int] = {}

    if source in {"eia", "all"}:
        counts["eia"] = publish_eia(
            producer=producer,
            limit=eia_limit,
        )

    if source in {"nws", "all"}:
        counts["nws"] = publish_nws(
            producer=producer,
            latitude=latitude,
            longitude=longitude,
            hours=weather_hours,
        )

    if source in {"afdc", "all"}:
        counts["afdc"] = publish_afdc(
            producer=producer,
            state=state,
            limit=ev_limit,
        )

    print()
    print("GridPulse Kafka source publishing completed")

    if "eia" in counts:
        print(f"EIA events: {counts['eia']}")

    if "nws" in counts:
        print(f"NWS events: {counts['nws']}")

    if "afdc" in counts:
        print(f"AFDC events: {counts['afdc']}")

    return counts


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=("Publish real GridPulse source data to Apache Kafka.")
    )

    parser.add_argument(
        "--source",
        required=True,
        choices=[
            "eia",
            "nws",
            "afdc",
            "all",
        ],
        help="Data source to publish.",
    )

    parser.add_argument(
        "--eia-limit",
        type=int,
        default=5,
        help="Number of latest EIA records.",
    )

    parser.add_argument(
        "--latitude",
        type=float,
        default=41.4993,
        help="NWS forecast latitude.",
    )

    parser.add_argument(
        "--longitude",
        type=float,
        default=-81.6944,
        help="NWS forecast longitude.",
    )

    parser.add_argument(
        "--weather-hours",
        type=int,
        default=5,
        help="Number of NWS hourly forecasts.",
    )

    parser.add_argument(
        "--state",
        default="OH",
        help="AFDC two-letter state code.",
    )

    parser.add_argument(
        "--ev-limit",
        type=int,
        default=5,
        help="Number of AFDC EV stations.",
    )

    return parser.parse_args()


def main() -> None:
    """Application entry point."""

    args = parse_args()

    run_publish(
        source=args.source,
        eia_limit=args.eia_limit,
        latitude=args.latitude,
        longitude=args.longitude,
        weather_hours=args.weather_hours,
        state=args.state,
        ev_limit=args.ev_limit,
    )


if __name__ == "__main__":
    main()
