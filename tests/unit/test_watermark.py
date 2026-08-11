import json
from datetime import datetime
from pathlib import Path

import pytest

from gridpulse_intelligence.watermark import (
    WatermarkError,
    read_watermark,
    write_watermark,
)


def test_read_watermark_returns_none_when_missing(
    tmp_path: Path,
) -> None:
    watermark_path = tmp_path / "watermark.json"

    result = read_watermark(watermark_path)

    assert result is None


def test_write_and_read_watermark(
    tmp_path: Path,
) -> None:
    watermark_path = tmp_path / "watermark.json"

    expected_period = datetime(
        2026,
        8,
        10,
        23,
    )

    result_path = write_watermark(
        period=expected_period,
        path=watermark_path,
    )

    assert result_path.exists()

    actual_period = read_watermark(watermark_path)

    assert actual_period == expected_period


def test_watermark_contains_metadata(
    tmp_path: Path,
) -> None:
    watermark_path = tmp_path / "watermark.json"

    write_watermark(
        period=datetime(
            2026,
            8,
            10,
            23,
        ),
        path=watermark_path,
    )

    payload = json.loads(
        watermark_path.read_text(
            encoding="utf-8",
        )
    )

    assert payload["dataset"] == "eia_region_data"
    assert payload["schema_version"] == "1.0"
    assert "updated_at" in payload


def test_invalid_watermark_json_fails(
    tmp_path: Path,
) -> None:
    watermark_path = tmp_path / "watermark.json"

    watermark_path.write_text(
        "{invalid-json",
        encoding="utf-8",
    )

    with pytest.raises(
        WatermarkError,
        match="Unable to read watermark",
    ):
        read_watermark(watermark_path)


def test_missing_period_fails(
    tmp_path: Path,
) -> None:
    watermark_path = tmp_path / "watermark.json"

    watermark_path.write_text(
        json.dumps(
            {
                "dataset": "eia_region_data",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        WatermarkError,
        match="last_successful_period",
    ):
        read_watermark(watermark_path)
