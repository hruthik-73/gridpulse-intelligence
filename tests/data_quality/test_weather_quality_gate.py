import json
from pathlib import Path

import pytest

from gridpulse_intelligence.quality_gate import (
    QualityGateError,
    validate_or_quarantine_nws_snapshot,
)


def write_snapshot(
    path: Path,
    include_bad_field: bool = False,
) -> None:
    record: dict[str, object] = {
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

    if include_bad_field:
        record["unexpected"] = "invalid"

    payload = {
        "metadata": {
            "source": "nws",
            "dataset": "nws_hourly_forecast",
            "schema_version": "1.0",
            "run_id": "test-run",
            "ingested_at": ("2026-08-11T19:00:00+00:00"),
            "record_count": 1,
        },
        "records": [record],
    }

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_weather_quality_gate_passes(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "weather.json"
    quarantine = tmp_path / "quarantine"

    write_snapshot(snapshot)

    report = validate_or_quarantine_nws_snapshot(
        snapshot_path=snapshot,
        quarantine_root=quarantine,
    )

    assert report.record_count == 1
    assert snapshot.exists()


def test_invalid_weather_snapshot_is_quarantined(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "weather.json"
    quarantine = tmp_path / "quarantine"

    write_snapshot(
        snapshot,
        include_bad_field=True,
    )

    with pytest.raises(
        QualityGateError,
    ):
        validate_or_quarantine_nws_snapshot(
            snapshot_path=snapshot,
            quarantine_root=quarantine,
        )

    assert not snapshot.exists()
    assert len(list(quarantine.rglob("*.json"))) == 1
