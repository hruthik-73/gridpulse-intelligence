"""Quality gates for GridPulse Bronze datasets."""

from pathlib import Path

import structlog

from gridpulse_intelligence.bronze_validation import (
    BronzeValidationError,
    BronzeValidationReport,
    validate_eia_bronze_snapshot,
)
from gridpulse_intelligence.quarantine import quarantine_snapshot

logger = structlog.get_logger(__name__)


class QualityGateError(Exception):
    """Raised when a dataset fails its quality gate."""


def validate_or_quarantine_eia_snapshot(
    snapshot_path: Path,
    contract_path: Path = Path("contracts/eia_region_data.yaml"),
    quarantine_root: Path = Path("data/quarantine/eia/region-data"),
) -> BronzeValidationReport:
    """Validate an EIA Bronze snapshot or quarantine it on failure."""

    try:
        report = validate_eia_bronze_snapshot(
            snapshot_path=snapshot_path,
            contract_path=contract_path,
        )

    except BronzeValidationError as exc:
        quarantined_path = quarantine_snapshot(
            snapshot_path=snapshot_path,
            reason=str(exc),
            quarantine_root=quarantine_root,
        )

        logger.error(
            "eia_quality_gate_failed",
            original_path=str(snapshot_path),
            quarantine_path=str(quarantined_path),
            reason=str(exc),
        )

        raise QualityGateError(
            f"EIA Bronze quality gate failed. Snapshot quarantined at: {quarantined_path}"
        ) from exc

    logger.info(
        "eia_quality_gate_passed",
        snapshot_path=str(snapshot_path),
        record_count=report.record_count,
        unique_key_count=report.unique_key_count,
    )

    return report
