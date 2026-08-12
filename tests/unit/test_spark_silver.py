"""Tests for GridPulse Silver transformations."""

import json
from datetime import datetime

import pytest
from pyspark.sql import SparkSession

from gridpulse_intelligence.spark_silver import (
    deduplicate_afdc,
    deduplicate_eia,
    deduplicate_nws,
    transform_afdc,
    transform_eia,
    transform_nws,
)


@pytest.fixture(scope="module")
def spark() -> SparkSession:
    """Create one local Spark session for Silver tests."""

    session = (
        SparkSession.builder.master("local[2]")
        .appName("gridpulse-silver-tests")
        .config(
            "spark.sql.shuffle.partitions",
            "2",
        )
        .getOrCreate()
    )

    session.sparkContext.setLogLevel("ERROR")

    yield session

    session.stop()


def make_bronze_dataframe(
    spark: SparkSession,
    rows: list[tuple[object, ...]],
):
    """Create a Bronze-shaped DataFrame."""

    return spark.createDataFrame(
        rows,
        schema=(
            "source string, "
            "event_id string, "
            "event_version string, "
            "event_type string, "
            "partition_key string, "
            "emitted_at string, "
            "replay boolean, "
            "source_timestamp string, "
            "topic string, "
            "partition int, "
            "offset long, "
            "kafka_timestamp timestamp, "
            "kafka_key string, "
            "payload_json string"
        ),
    )


def bronze_row(
    *,
    source: str,
    payload: dict[str, object],
    event_id: str = ("550e8400-e29b-41d4-a716-446655440000"),
    emitted_at: str = "2026-08-11T20:00:00+00:00",
    kafka_timestamp: datetime = datetime(
        2026,
        8,
        11,
        20,
        0,
    ),
    offset: int = 1,
) -> tuple[object, ...]:
    """Create one canonical Bronze row."""

    topic_by_source = {
        "eia": "gridpulse.eia.region-data.v1",
        "nws": "gridpulse.nws.forecast.v1",
        "afdc": "gridpulse.afdc.ev-stations.v1",
    }

    event_type_by_source = {
        "eia": "eia.region_data.observed",
        "nws": "nws.hourly_forecast.observed",
        "afdc": "afdc.ev_station.observed",
    }

    partition_key_by_source = {
        "eia": "PJM",
        "nws": "41.4993,-81.6944",
        "afdc": "OH",
    }

    return (
        source,
        event_id,
        "1.0",
        event_type_by_source[source],
        partition_key_by_source[source],
        emitted_at,
        False,
        "2026-08-11T19:00:00",
        topic_by_source[source],
        0,
        offset,
        kafka_timestamp,
        partition_key_by_source[source],
        json.dumps(payload),
    )


def valid_eia_payload(
    *,
    value: float | None = 3322.0,
) -> dict[str, object]:
    """Return a valid EIA payload."""

    return {
        "period": "2026-08-10T05:00:00",
        "record_type": "D",
        "respondent": "BANC",
        "respondent_name": ("Balancing Authority of Northern California"),
        "type_name": "Demand",
        "value": value,
        "value_units": "megawatthours",
    }


def valid_nws_payload(
    *,
    relative_humidity: float | None = 87.0,
    temperature: float = 74.0,
) -> dict[str, object]:
    """Return a valid NWS payload."""

    return {
        "latitude": 41.4993,
        "longitude": -81.6944,
        "period_end": "2026-08-11T22:00:00-04:00",
        "period_start": "2026-08-11T21:00:00-04:00",
        "precipitation_probability": 28.0,
        "relative_humidity": relative_humidity,
        "short_forecast": ("Chance Showers And Thunderstorms"),
        "temperature": temperature,
        "temperature_unit": "F",
        "wind_direction": "W",
        "wind_speed": "2 mph",
    }


def valid_afdc_payload(
    *,
    access_code: str = "public",
    updated_at: str = "2026-07-06T18:25:56Z",
    station_name: str = "Baker Electric Building",
) -> dict[str, object]:
    """Return a valid AFDC payload."""

    return {
        "access_code": access_code,
        "city": "Cleveland",
        "country": "US",
        "date_last_confirmed": "2024-12-10",
        "ev_connector_types": [
            "J1772",
        ],
        "ev_dc_fast_num": None,
        "ev_level1_evse_num": None,
        "ev_level2_evse_num": 1,
        "ev_network": "Non-Networked",
        "facility_type": "PARKING_LOT",
        "fuel_type_code": "ELEC",
        "latitude": 41.503373,
        "longitude": -81.639054,
        "state": "OH",
        "station_id": 37097,
        "station_name": station_name,
        "status_code": "E",
        "street_address": "7100 Euclid Ave",
        "updated_at": updated_at,
        "zip_code": "44103",
    }


def test_eia_valid_record_passes(
    spark: SparkSession,
) -> None:
    """Valid EIA data should produce typed Silver columns."""

    bronze = make_bronze_dataframe(
        spark,
        [
            bronze_row(
                source="eia",
                payload=valid_eia_payload(),
            )
        ],
    )

    result = transform_eia(bronze).collect()[0]

    assert result["is_valid"] is True
    assert result["quality_status"] == "PASS"
    assert result["quality_error"] is None
    assert result["respondent"] == "BANC"
    assert result["value"] == 3322.0
    assert isinstance(
        result["period"],
        datetime,
    )


def test_eia_missing_value_fails_quality(
    spark: SparkSession,
) -> None:
    """Missing EIA demand value should fail Silver quality."""

    bronze = make_bronze_dataframe(
        spark,
        [
            bronze_row(
                source="eia",
                payload=valid_eia_payload(value=None),
            )
        ],
    )

    result = transform_eia(bronze).collect()[0]

    assert result["is_valid"] is False
    assert result["quality_status"] == "FAIL"
    assert result["quality_error"] == "invalid_value"


def test_eia_deduplication_keeps_latest_event(
    spark: SparkSession,
) -> None:
    """Duplicate EIA business keys should keep the latest event."""

    older = bronze_row(
        source="eia",
        payload=valid_eia_payload(value=3000.0),
        event_id=("550e8400-e29b-41d4-a716-446655440001"),
        emitted_at="2026-08-11T19:00:00+00:00",
        kafka_timestamp=datetime(
            2026,
            8,
            11,
            19,
            0,
        ),
        offset=10,
    )

    newer = bronze_row(
        source="eia",
        payload=valid_eia_payload(value=3500.0),
        event_id=("550e8400-e29b-41d4-a716-446655440002"),
        emitted_at="2026-08-11T20:00:00+00:00",
        kafka_timestamp=datetime(
            2026,
            8,
            11,
            20,
            0,
        ),
        offset=11,
    )

    bronze = make_bronze_dataframe(
        spark,
        [
            older,
            newer,
        ],
    )

    result = deduplicate_eia(transform_eia(bronze)).collect()

    assert len(result) == 1
    assert result[0]["value"] == 3500.0
    assert result[0]["offset"] == 11


def test_nws_valid_record_passes(
    spark: SparkSession,
) -> None:
    """Valid weather data should enter NWS Silver."""

    bronze = make_bronze_dataframe(
        spark,
        [
            bronze_row(
                source="nws",
                payload=valid_nws_payload(),
            )
        ],
    )

    result = transform_nws(bronze).collect()[0]

    assert result["is_valid"] is True
    assert result["quality_status"] == "PASS"
    assert result["temperature"] == 74.0
    assert result["relative_humidity"] == 87.0
    assert isinstance(
        result["period_start"],
        datetime,
    )


def test_nws_invalid_humidity_fails_quality(
    spark: SparkSession,
) -> None:
    """Humidity above 100 percent should fail."""

    bronze = make_bronze_dataframe(
        spark,
        [
            bronze_row(
                source="nws",
                payload=valid_nws_payload(relative_humidity=120.0),
            )
        ],
    )

    result = transform_nws(bronze).collect()[0]

    assert result["is_valid"] is False
    assert result["quality_error"] == "invalid_relative_humidity"


def test_nws_deduplication_keeps_latest_event(
    spark: SparkSession,
) -> None:
    """Duplicate forecast hours should keep the latest event."""

    older = bronze_row(
        source="nws",
        payload=valid_nws_payload(temperature=72.0),
        event_id=("550e8400-e29b-41d4-a716-446655440003"),
        emitted_at="2026-08-11T19:00:00+00:00",
        kafka_timestamp=datetime(
            2026,
            8,
            11,
            19,
            0,
        ),
        offset=20,
    )

    newer = bronze_row(
        source="nws",
        payload=valid_nws_payload(temperature=75.0),
        event_id=("550e8400-e29b-41d4-a716-446655440004"),
        emitted_at="2026-08-11T20:00:00+00:00",
        kafka_timestamp=datetime(
            2026,
            8,
            11,
            20,
            0,
        ),
        offset=21,
    )

    bronze = make_bronze_dataframe(
        spark,
        [
            older,
            newer,
        ],
    )

    result = deduplicate_nws(transform_nws(bronze)).collect()

    assert len(result) == 1
    assert result[0]["temperature"] == 75.0
    assert result[0]["offset"] == 21


def test_afdc_valid_record_passes(
    spark: SparkSession,
) -> None:
    """Valid charging station data should enter AFDC Silver."""

    bronze = make_bronze_dataframe(
        spark,
        [
            bronze_row(
                source="afdc",
                payload=valid_afdc_payload(),
            )
        ],
    )

    result = transform_afdc(bronze).collect()[0]

    assert result["is_valid"] is True
    assert result["quality_status"] == "PASS"
    assert result["station_id"] == 37097
    assert result["state"] == "OH"
    assert result["ev_connector_types"] == ["J1772"]


def test_afdc_non_public_station_fails_quality(
    spark: SparkSession,
) -> None:
    """Non-public charging stations should fail Silver rules."""

    bronze = make_bronze_dataframe(
        spark,
        [
            bronze_row(
                source="afdc",
                payload=valid_afdc_payload(access_code="private"),
            )
        ],
    )

    result = transform_afdc(bronze).collect()[0]

    assert result["is_valid"] is False
    assert result["quality_error"] == "invalid_access_code"


def test_afdc_deduplication_prefers_latest_update(
    spark: SparkSession,
) -> None:
    """AFDC should keep the latest station snapshot."""

    older = bronze_row(
        source="afdc",
        payload=valid_afdc_payload(
            updated_at=("2026-07-01T10:00:00Z"),
            station_name="Old Station Name",
        ),
        event_id=("550e8400-e29b-41d4-a716-446655440005"),
        emitted_at="2026-08-11T21:00:00+00:00",
        kafka_timestamp=datetime(
            2026,
            8,
            11,
            21,
            0,
        ),
        offset=30,
    )

    newer = bronze_row(
        source="afdc",
        payload=valid_afdc_payload(
            updated_at=("2026-07-10T10:00:00Z"),
            station_name="Updated Station Name",
        ),
        event_id=("550e8400-e29b-41d4-a716-446655440006"),
        emitted_at="2026-08-11T20:00:00+00:00",
        kafka_timestamp=datetime(
            2026,
            8,
            11,
            20,
            0,
        ),
        offset=31,
    )

    bronze = make_bronze_dataframe(
        spark,
        [
            older,
            newer,
        ],
    )

    result = deduplicate_afdc(transform_afdc(bronze)).collect()

    assert len(result) == 1

    assert result[0]["station_name"] == "Updated Station Name"

    assert result[0]["offset"] == 31
