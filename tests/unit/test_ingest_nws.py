"""Tests for NWS ingestion orchestration."""

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

import gridpulse_intelligence.ingest_nws as ingest_nws
from gridpulse_intelligence.models import WeatherForecastRecord


def sample_weather_record() -> WeatherForecastRecord:
    """Return a valid weather record."""

    return WeatherForecastRecord.model_validate(
        {
            "latitude": 41.4993,
            "longitude": -81.6944,
            "period_start": "2026-08-11T14:00:00-04:00",
            "period_end": "2026-08-11T15:00:00-04:00",
            "temperature": 80,
            "temperature_unit": "F",
            "precipitation_probability": 40,
            "relative_humidity": 72,
            "wind_speed": "8 mph",
            "wind_direction": "SW",
            "short_forecast": "Chance Thunderstorms",
        }
    )


def test_run_ingestion_executes_complete_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful ingestion should write and validate Bronze data."""

    bronze_path = tmp_path / "weather.json"

    state: dict[str, object] = {
        "client_closed": False,
    }

    class FakeNWSClient:
        def get_hourly_forecast(
            self,
            latitude: float,
            longitude: float,
            limit: int,
        ) -> list[WeatherForecastRecord]:
            state["latitude"] = latitude
            state["longitude"] = longitude
            state["limit"] = limit

            return [
                sample_weather_record(),
            ]

        def close(self) -> None:
            state["client_closed"] = True

    def fake_write(
        records: list[WeatherForecastRecord],
    ) -> Path:
        state["written_records"] = len(records)
        return bronze_path

    def fake_quality_gate(
        snapshot_path: Path,
    ) -> SimpleNamespace:
        state["validated_path"] = snapshot_path

        return SimpleNamespace(
            record_count=1,
            unique_key_count=1,
        )

    monkeypatch.setattr(
        ingest_nws,
        "NWSClient",
        FakeNWSClient,
    )

    monkeypatch.setattr(
        ingest_nws,
        "write_nws_bronze_snapshot",
        fake_write,
    )

    monkeypatch.setattr(
        ingest_nws,
        "validate_or_quarantine_nws_snapshot",
        fake_quality_gate,
    )

    ingest_nws.run_ingestion(
        latitude=41.4993,
        longitude=-81.6944,
        hours=12,
        location_name="Cleveland, OH",
    )

    assert state["latitude"] == 41.4993
    assert state["longitude"] == -81.6944
    assert state["limit"] == 12
    assert state["written_records"] == 1
    assert state["validated_path"] == bronze_path
    assert state["client_closed"] is True


def test_empty_nws_response_fails_before_bronze_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty upstream response must not produce Bronze data."""

    state: dict[str, object] = {
        "client_closed": False,
        "writer_called": False,
    }

    class FakeNWSClient:
        def get_hourly_forecast(
            self,
            latitude: float,
            longitude: float,
            limit: int,
        ) -> list[WeatherForecastRecord]:
            del latitude, longitude, limit
            return []

        def close(self) -> None:
            state["client_closed"] = True

    def fake_write(
        records: list[WeatherForecastRecord],
    ) -> Path:
        del records
        state["writer_called"] = True
        return Path("should-not-exist.json")

    monkeypatch.setattr(
        ingest_nws,
        "NWSClient",
        FakeNWSClient,
    )

    monkeypatch.setattr(
        ingest_nws,
        "write_nws_bronze_snapshot",
        fake_write,
    )

    with pytest.raises(
        RuntimeError,
        match="no hourly forecast records",
    ):
        ingest_nws.run_ingestion(
            latitude=41.4993,
            longitude=-81.6944,
            hours=12,
        )

    assert state["writer_called"] is False
    assert state["client_closed"] is True


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", 1),
        ("12", 12),
        ("48", 48),
    ],
)
def test_positive_integer_accepts_valid_values(
    value: str,
    expected: int,
) -> None:
    """Positive CLI integers should parse successfully."""

    assert ingest_nws.positive_integer(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-1",
        "invalid",
    ],
)
def test_positive_integer_rejects_invalid_values(
    value: str,
) -> None:
    """Invalid CLI integers should be rejected."""

    with pytest.raises(
        argparse.ArgumentTypeError,
    ):
        ingest_nws.positive_integer(value)
