"""Reusable Bronze data quality gates."""

from pathlib import Path

import structlog

from gridpulse_intelligence.bronze_validation import (
    BronzeValidationError,
    BronzeValidationReport,
    validate_eia_bronze_snapshot,
)
from gridpulse_intelligence.quarantine import quarantine_snapshot
from gridpulse_intelligence.weather_validation import (
    WeatherBronzeValidationError,
    WeatherBronzeValidationReport,
    validate_nws_bronze_snapshot,
)

logger = structlog.get_logger(__name__)


class QualityGateError(Exception):
    """Raised when a Bronze snapshot fails its quality gate."""


def validate_or_quarantine_eia_snapshot(
    snapshot_path: Path,
    contract_path: Path = Path("contracts/eia_region_data.yaml"),
    quarantine_root: Path = Path("data/quarantine/eia/region-data"),
) -> BronzeValidationReport:
    """Validate an EIA snapshot or quarantine it on failure."""

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
            snapshot_path=str(snapshot_path),
            quarantine_path=str(quarantined_path),
            reason=str(exc),
        )

        raise QualityGateError(
            f"EIA quality gate failed; Bronze snapshot was quarantined at {quarantined_path}"
        ) from exc

    logger.info(
        "eia_quality_gate_passed",
        snapshot_path=str(snapshot_path),
        record_count=report.record_count,
    )

    return report


def validate_or_quarantine_nws_snapshot(
    snapshot_path: Path,
    contract_path: Path = Path("contracts/nws_hourly_forecast.yaml"),
    quarantine_root: Path = Path("data/quarantine/nws/hourly-forecast"),
) -> WeatherBronzeValidationReport:
    """Validate an NWS snapshot or quarantine it on failure."""

    try:
        report = validate_nws_bronze_snapshot(
            snapshot_path=snapshot_path,
            contract_path=contract_path,
        )

    except WeatherBronzeValidationError as exc:
        quarantined_path = quarantine_snapshot(
            snapshot_path=snapshot_path,
            reason=str(exc),
            quarantine_root=quarantine_root,
        )

        logger.error(
            "nws_quality_gate_failed",
            snapshot_path=str(snapshot_path),
            quarantine_path=str(quarantined_path),
            reason=str(exc),
        )

        raise QualityGateError(
            f"NWS quality gate failed; Bronze snapshot was quarantined at {quarantined_path}"
        ) from exc

    logger.info(
        "nws_quality_gate_passed",
        snapshot_path=str(snapshot_path),
        record_count=report.record_count,
    )

    return report
