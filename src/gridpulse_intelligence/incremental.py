"""Incremental ingestion window calculation."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)


class IncrementalWindowError(Exception):
    """Raised when an incremental ingestion window cannot be created."""


@dataclass(frozen=True)
class IncrementalWindow:
    """Time range to ingest from the EIA API."""

    start: datetime
    end: datetime

    @property
    def hour_count(self) -> int:
        """Return the inclusive number of hours in the window."""

        difference = self.end - self.start
        return int(difference.total_seconds() // 3600) + 1


def latest_safe_hour(
    now: datetime | None = None,
    safety_lag_hours: int = 2,
) -> datetime:
    """Return the latest hour considered safe for ingestion."""

    if safety_lag_hours < 0:
        raise ValueError("safety_lag_hours must be zero or greater")

    current_time = now or datetime.now(UTC)

    if current_time.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    safe_time = current_time - timedelta(hours=safety_lag_hours)

    safe_hour = safe_time.replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    return safe_hour.replace(tzinfo=None)


def calculate_incremental_window(
    watermark: datetime | None,
    bootstrap_start: datetime,
    now: datetime | None = None,
    safety_lag_hours: int = 2,
) -> IncrementalWindow | None:
    """Calculate the next missing EIA ingestion window."""

    end = latest_safe_hour(
        now=now,
        safety_lag_hours=safety_lag_hours,
    )

    if watermark is None:
        start = bootstrap_start
    else:
        start = watermark + timedelta(hours=1)

    if start > end:
        logger.info(
            "incremental_window_empty",
            start=start.isoformat(),
            end=end.isoformat(),
        )
        return None

    window = IncrementalWindow(
        start=start,
        end=end,
    )

    logger.info(
        "incremental_window_calculated",
        start=window.start.isoformat(),
        end=window.end.isoformat(),
        hour_count=window.hour_count,
    )

    return window
