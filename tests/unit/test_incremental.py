from datetime import UTC, datetime

import pytest

from gridpulse_intelligence.incremental import (
    calculate_incremental_window,
    latest_safe_hour,
)


def test_latest_safe_hour_uses_safety_lag() -> None:
    now = datetime(
        2026,
        8,
        11,
        19,
        28,
        tzinfo=UTC,
    )

    result = latest_safe_hour(
        now=now,
        safety_lag_hours=2,
    )

    assert result == datetime(
        2026,
        8,
        11,
        17,
    )


def test_bootstrap_window_when_watermark_missing() -> None:
    now = datetime(
        2026,
        8,
        11,
        19,
        28,
        tzinfo=UTC,
    )

    window = calculate_incremental_window(
        watermark=None,
        bootstrap_start=datetime(
            2026,
            8,
            10,
            0,
        ),
        now=now,
        safety_lag_hours=2,
    )

    assert window is not None
    assert window.start == datetime(
        2026,
        8,
        10,
        0,
    )
    assert window.end == datetime(
        2026,
        8,
        11,
        17,
    )
    assert window.hour_count == 42


def test_existing_watermark_starts_at_next_hour() -> None:
    now = datetime(
        2026,
        8,
        11,
        19,
        28,
        tzinfo=UTC,
    )

    window = calculate_incremental_window(
        watermark=datetime(
            2026,
            8,
            11,
            12,
        ),
        bootstrap_start=datetime(
            2026,
            8,
            10,
            0,
        ),
        now=now,
        safety_lag_hours=2,
    )

    assert window is not None
    assert window.start == datetime(
        2026,
        8,
        11,
        13,
    )
    assert window.end == datetime(
        2026,
        8,
        11,
        17,
    )
    assert window.hour_count == 5


def test_no_window_when_already_current() -> None:
    now = datetime(
        2026,
        8,
        11,
        19,
        28,
        tzinfo=UTC,
    )

    window = calculate_incremental_window(
        watermark=datetime(
            2026,
            8,
            11,
            17,
        ),
        bootstrap_start=datetime(
            2026,
            8,
            10,
            0,
        ),
        now=now,
        safety_lag_hours=2,
    )

    assert window is None


def test_future_watermark_returns_no_window() -> None:
    now = datetime(
        2026,
        8,
        11,
        19,
        28,
        tzinfo=UTC,
    )

    window = calculate_incremental_window(
        watermark=datetime(
            2026,
            8,
            12,
            0,
        ),
        bootstrap_start=datetime(
            2026,
            8,
            10,
            0,
        ),
        now=now,
        safety_lag_hours=2,
    )

    assert window is None


def test_negative_safety_lag_fails() -> None:
    now = datetime(
        2026,
        8,
        11,
        19,
        28,
        tzinfo=UTC,
    )

    with pytest.raises(
        ValueError,
        match="safety_lag_hours",
    ):
        latest_safe_hour(
            now=now,
            safety_lag_hours=-1,
        )


def test_naive_current_time_fails() -> None:
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        latest_safe_hour(
            now=datetime(
                2026,
                8,
                11,
                19,
                28,
            )
        )
