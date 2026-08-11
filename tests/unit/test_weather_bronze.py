import json
from datetime import datetime
from pathlib import Path

from gridpulse_intelligence.models import (
    WeatherForecastRecord,
)
from gridpulse_intelligence.weather_bronze import (
    write_nws_bronze_snapshot,
)


def test_write_nws_bronze_snapshot(
    tmp_path: Path,
) -> None:
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

    output_path = write_nws_bronze_snapshot(
        records=[record],
        output_root=tmp_path,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["metadata"]["source"] == "nws"

    assert payload["metadata"]["dataset"] == "nws_hourly_forecast"

    assert payload["metadata"]["record_count"] == 1

    assert payload["records"][0]["temperature"] == 80.0
