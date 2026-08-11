"""Bronze-layer storage utilities for GridPulse Intelligence."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import structlog

from gridpulse_intelligence.models import GridRegionRecord

logger = structlog.get_logger(__name__)


def write_eia_bronze_snapshot(
    records: list[GridRegionRecord],
    output_root: Path = Path("data/raw/eia/region-data"),
) -> Path:
    """Write a timestamped EIA snapshot to the local Bronze landing zone."""

    if not records:
        raise ValueError("records must not be empty")

    ingested_at = datetime.now(UTC)
    run_id = uuid4().hex

    partition_directory = output_root / f"ingestion_date={ingested_at:%Y-%m-%d}"

    partition_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = f"eia_region_data_{ingested_at:%Y%m%dT%H%M%SZ}_{run_id[:8]}.json"

    destination = partition_directory / filename
    temporary_file = destination.with_suffix(".tmp")

    payload: dict[str, object] = {
        "metadata": {
            "source": "eia",
            "dataset": "electricity/rto/region-data",
            "schema_version": "1.0",
            "run_id": run_id,
            "ingested_at": ingested_at.isoformat(),
            "record_count": len(records),
        },
        "records": [
            record.model_dump(
                by_alias=True,
                mode="json",
            )
            for record in records
        ],
    }

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            indent=2,
        )
        file.write("\n")

    temporary_file.replace(destination)

    logger.info(
        "eia_bronze_snapshot_written",
        path=str(destination),
        record_count=len(records),
        run_id=run_id,
    )

    return destination
