"""Tests for incremental EIA ingestion safety behavior."""

from datetime import datetime
from pathlib import Path

import pytest

import gridpulse_intelligence.ingest_eia_incremental as incremental_ingestion
from gridpulse_intelligence.incremental import IncrementalWindow
from gridpulse_intelligence.models import GridRegionRecord
from gridpulse_intelligence.watermark import (
    read_watermark,
    write_watermark,
)


def make_record(period: datetime) -> GridRegionRecord:
    """Create a valid EIA record for testing."""

    return GridRegionRecord.model_validate(
        {
            "period": period.strftime("%Y-%m-%dT%H"),
            "respondent": "TEST",
            "respondent-name": "Test Balancing Authority",
            "type": "D",
            "type-name": "Demand",
            "value": "1000",
            "value-units": "megawatthours",
        }
    )


def test_expected_periods_contains_every_hour() -> None:
    window = IncrementalWindow(
        start=datetime(2026, 8, 10, 6),
        end=datetime(2026, 8, 10, 8),
    )

    result = incremental_ingestion.expected_periods(window)

    assert result == {
        datetime(2026, 8, 10, 6),
        datetime(2026, 8, 10, 7),
        datetime(2026, 8, 10, 8),
    }


def test_missing_hour_fails_coverage_validation() -> None:
    window = IncrementalWindow(
        start=datetime(2026, 8, 10, 6),
        end=datetime(2026, 8, 10, 8),
    )

    periods_received = {
        datetime(2026, 8, 10, 6),
        datetime(2026, 8, 10, 8),
    }

    with pytest.raises(
        RuntimeError,
        match="2026-08-10T07",
    ):
        incremental_ingestion.validate_period_coverage(
            window=window,
            periods_received=periods_received,
        )


def test_missing_hour_does_not_advance_watermark(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watermark_path = tmp_path / "watermark.json"

    original_watermark = datetime(
        2026,
        8,
        10,
        5,
    )

    write_watermark(
        period=original_watermark,
        path=watermark_path,
    )

    class FakeEIAClient:
        """EIA client returning an intentionally incomplete window."""

        def get_region_data(
            self,
            start: datetime,
            end: datetime,
            page_size: int = 5000,
        ) -> list[GridRegionRecord]:
            del end, page_size

            return [
                make_record(start),
            ]

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        incremental_ingestion,
        "EIAClient",
        FakeEIAClient,
    )

    monkeypatch.setattr(
        incremental_ingestion,
        "calculate_incremental_window",
        lambda **_: IncrementalWindow(
            start=datetime(2026, 8, 10, 6),
            end=datetime(2026, 8, 10, 7),
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="watermark will not advance",
    ):
        incremental_ingestion.run_incremental_ingestion(
            bootstrap_start=datetime(2026, 8, 10, 0),
            safety_lag_hours=2,
            max_window_hours=2,
            page_size=500,
            watermark_path=watermark_path,
        )

    assert read_watermark(watermark_path) == original_watermark
