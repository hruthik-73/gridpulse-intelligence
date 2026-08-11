"""Bronze storage for National Weather Service forecast data."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import structlog

from gridpulse_intelligence.models import WeatherForecastRecord

logger = structlog.get_logger(__name__)

DEFAULT_NWS_BRONZE_ROOT = Path("data/raw/nws/hourly-forecast")


def write_nws_bronze_snapshot(
    records: list[WeatherForecastRecord],
    output_root: Path = DEFAULT_NWS_BRONZE_ROOT,
) -> Path:
    """Write an immutable NWS Bronze snapshot."""

    if not records:
        raise ValueError("Cannot write an empty NWS Bronze snapshot.")

    ingested_at = datetime.now(UTC)
    run_id = str(uuid4())

    partition_path = output_root / (f"ingestion_date={ingested_at:%Y-%m-%d}")

    partition_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = partition_path / (
        f"nws_hourly_forecast_{ingested_at:%Y%m%dT%H%M%SZ}_{run_id[:8]}.json"
    )

    payload = {
        "metadata": {
            "source": "nws",
            "dataset": "nws_hourly_forecast",
            "schema_version": "1.0",
            "run_id": run_id,
            "ingested_at": ingested_at.isoformat(),
            "record_count": len(records),
        },
        "records": [
            record.model_dump(
                mode="json",
            )
            for record in records
        ],
    }

    temporary_path = destination.with_suffix(".tmp")

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(destination)

    logger.info(
        "nws_bronze_snapshot_written",
        output_path=str(destination),
        record_count=len(records),
        run_id=run_id,
    )

    return destination
