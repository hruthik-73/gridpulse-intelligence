"""Incremental ingestion watermark management."""

import json
from datetime import UTC, datetime
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

DEFAULT_WATERMARK_PATH = Path("data/checkpoints/eia_region_data_watermark.json")


class WatermarkError(Exception):
    """Raised when watermark state cannot be read or written."""


def read_watermark(
    path: Path = DEFAULT_WATERMARK_PATH,
) -> datetime | None:
    """Return the last successfully ingested EIA period."""

    if not path.exists():
        logger.info(
            "watermark_not_found",
            path=str(path),
        )
        return None

    try:
        payload: object = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise WatermarkError(f"Unable to read watermark: {path}") from exc

    if not isinstance(payload, dict):
        raise WatermarkError("Watermark root must be a JSON object.")

    raw_period = payload.get("last_successful_period")

    if not isinstance(raw_period, str):
        raise WatermarkError("Watermark is missing last_successful_period.")

    try:
        period = datetime.fromisoformat(raw_period)
    except ValueError as exc:
        raise WatermarkError("Watermark contains an invalid period.") from exc

    logger.info(
        "watermark_loaded",
        path=str(path),
        last_successful_period=period.isoformat(),
    )

    return period


def write_watermark(
    period: datetime,
    path: Path = DEFAULT_WATERMARK_PATH,
) -> Path:
    """Atomically persist the last successfully ingested EIA period."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    updated_at = datetime.now(UTC)

    payload = {
        "dataset": "eia_region_data",
        "schema_version": "1.0",
        "last_successful_period": period.isoformat(),
        "updated_at": updated_at.isoformat(),
    }

    temporary_path = path.with_suffix(".tmp")

    try:
        temporary_path.write_text(
            json.dumps(
                payload,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(path)

    except OSError as exc:
        raise WatermarkError(f"Unable to write watermark: {path}") from exc

    logger.info(
        "watermark_updated",
        path=str(path),
        last_successful_period=period.isoformat(),
    )

    return path
