import json
from pathlib import Path

import pytest

from gridpulse_intelligence.weather_validation import (
    WeatherBronzeValidationError,
    validate_nws_bronze_snapshot,
)


def sample_record() -> dict[str, object]:
    return {
        "latitude": 41.4993,
        "longitude": -81.6944,
        "period_start": "2026-08-11T14:00:00-04:00",
        "period_end": "2026-08-11T15:00:00-04:00",
        "temperature": 80.0,
        "temperature_unit": "F",
        "precipitation_probability": 40.0,
        "relative_humidity": 72.0,
        "wind_speed": "8 mph",
        "wind_direction": "SW",
        "short_forecast": "Chance Thunderstorms",
    }


def write_snapshot(
    path: Path,
    records: list[dict[str, object]],
) -> None:
    payload = {
        "metadata": {
            "source": "nws",
            "dataset": "nws_hourly_forecast",
            "schema_version": "1.0",
            "run_id": "test-run",
            "ingested_at": ("2026-08-11T19:00:00+00:00"),
            "record_count": len(records),
        },
        "records": records,
    }

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_valid_weather_snapshot(
    tmp_path: Path,
) -> None:
    path = tmp_path / "weather.json"

    write_snapshot(
        path,
        [sample_record()],
    )

    report = validate_nws_bronze_snapshot(path)

    assert report.record_count == 1
    assert report.unique_key_count == 1


def test_duplicate_weather_key_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "weather.json"
    record = sample_record()

    write_snapshot(
        path,
        [
            record,
            record.copy(),
        ],
    )

    with pytest.raises(
        WeatherBronzeValidationError,
        match="Duplicate",
    ):
        validate_nws_bronze_snapshot(path)


def test_unknown_weather_field_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "weather.json"

    record = sample_record()
    record["unexpected"] = "bad"

    write_snapshot(
        path,
        [record],
    )

    with pytest.raises(
        WeatherBronzeValidationError,
        match="unknown fields",
    ):
        validate_nws_bronze_snapshot(path)


def test_missing_weather_field_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "weather.json"

    record = sample_record()
    del record["temperature"]

    write_snapshot(
        path,
        [record],
    )

    with pytest.raises(
        WeatherBronzeValidationError,
        match="missing fields",
    ):
        validate_nws_bronze_snapshot(path)
