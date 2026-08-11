"""Quarantine utilities for invalid GridPulse snapshots."""

from datetime import UTC, datetime
from pathlib import Path
from shutil import move
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


def quarantine_snapshot(
    snapshot_path: Path,
    reason: str,
    quarantine_root: Path = Path("data/quarantine/eia/region-data"),
) -> Path:
    """Move an invalid snapshot into the quarantine area."""

    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot does not exist: {snapshot_path}")

    quarantined_at = datetime.now(UTC)

    partition_directory = quarantine_root / f"quarantine_date={quarantined_at:%Y-%m-%d}"

    partition_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    quarantine_id = uuid4().hex[:8]

    destination = (
        partition_directory
        / f"{snapshot_path.stem}_quarantine_{quarantine_id}{snapshot_path.suffix}"
    )

    move(
        str(snapshot_path),
        str(destination),
    )

    reason_file = destination.with_suffix(destination.suffix + ".reason.txt")

    reason_file.write_text(
        reason + "\n",
        encoding="utf-8",
    )

    logger.warning(
        "snapshot_quarantined",
        source_path=str(snapshot_path),
        quarantine_path=str(destination),
        reason=reason,
    )

    return destination
