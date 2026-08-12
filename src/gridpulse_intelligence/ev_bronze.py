"""Bronze storage for AFDC EV charging station data."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import structlog

from gridpulse_intelligence.models import EVChargingStationRecord

logger = structlog.get_logger(__name__)

DEFAULT_EV_BRONZE_ROOT = Path("data/raw/afdc/ev-stations")


def write_ev_bronze_snapshot(
    records: list[EVChargingStationRecord],
    query_state: str,
    total_results: int,
    output_root: Path = DEFAULT_EV_BRONZE_ROOT,
) -> Path:
    """Write an immutable AFDC EV station Bronze snapshot."""

    if not records:
        raise ValueError("Cannot write an empty EV Bronze snapshot.")

    normalized_state = query_state.strip().upper()

    if len(normalized_state) != 2 or not normalized_state.isalpha():
        raise ValueError("query_state must be a two-letter state code")

    if total_results < len(records):
        raise ValueError("total_results cannot be smaller than the snapshot record count")

    ingested_at = datetime.now(UTC)
    run_id = str(uuid4())

    partition_path = output_root / f"ingestion_date={ingested_at:%Y-%m-%d}"

    partition_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = partition_path / (
        f"afdc_ev_stations_{normalized_state}_{ingested_at:%Y%m%dT%H%M%SZ}_{run_id[:8]}.json"
    )

    payload = {
        "metadata": {
            "source": "afdc",
            "dataset": "afdc_ev_stations",
            "schema_version": "1.0",
            "run_id": run_id,
            "ingested_at": ingested_at.isoformat(),
            "record_count": len(records),
            "query_state": normalized_state,
            "total_results": total_results,
        },
        "records": [record.model_dump(mode="json") for record in records],
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
        "ev_bronze_snapshot_written",
        output_path=str(destination),
        query_state=normalized_state,
        record_count=len(records),
        total_results=total_results,
        run_id=run_id,
    )

    return destination
