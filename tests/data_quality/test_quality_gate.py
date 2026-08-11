import json
from pathlib import Path

import pytest

from gridpulse_intelligence.quality_gate import (
    QualityGateError,
    validate_or_quarantine_eia_snapshot,
)


def valid_record() -> dict[str, object]:
    return {
        "period": "2026-08-12T07:00:00",
        "respondent": "CAL",
        "respondent-name": "California",
        "type": "DF",
        "type-name": "Day-ahead demand forecast",
        "value": 37905.0,
        "value-units": "megawatthours",
    }


def write_snapshot(
    path: Path,
    records: list[dict[str, object]],
) -> None:
    payload = {
        "metadata": {
            "source": "eia",
            "dataset": "electricity/rto/region-data",
            "schema_version": "1.0",
            "run_id": "quality-gate-test",
            "ingested_at": "2026-08-11T19:00:00+00:00",
            "record_count": len(records),
        },
        "records": records,
    }

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_quality_gate_keeps_valid_snapshot(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "valid.json"

    write_snapshot(
        snapshot,
        [valid_record()],
    )

    report = validate_or_quarantine_eia_snapshot(
        snapshot_path=snapshot,
        quarantine_root=tmp_path / "quarantine",
    )

    assert snapshot.exists()
    assert report.record_count == 1
    assert report.unique_key_count == 1


def test_quality_gate_quarantines_invalid_snapshot(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "invalid.json"

    record = valid_record()
    record["unexpected-field"] = "bad-data"

    write_snapshot(
        snapshot,
        [record],
    )

    quarantine_root = tmp_path / "quarantine"

    with pytest.raises(
        QualityGateError,
        match="quality gate failed",
    ):
        validate_or_quarantine_eia_snapshot(
            snapshot_path=snapshot,
            quarantine_root=quarantine_root,
        )

    assert not snapshot.exists()

    quarantined_files = list(quarantine_root.rglob("*.json"))

    reason_files = list(quarantine_root.rglob("*.reason.txt"))

    assert len(quarantined_files) == 1
    assert len(reason_files) == 1

    reason = reason_files[0].read_text(
        encoding="utf-8",
    )

    assert "unknown fields" in reason


def test_quality_gate_quarantines_duplicate_records(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "duplicates.json"

    record = valid_record()

    write_snapshot(
        snapshot,
        [
            record,
            record.copy(),
        ],
    )

    quarantine_root = tmp_path / "quarantine"

    with pytest.raises(QualityGateError):
        validate_or_quarantine_eia_snapshot(
            snapshot_path=snapshot,
            quarantine_root=quarantine_root,
        )

    assert not snapshot.exists()

    quarantined_files = list(quarantine_root.rglob("*.json"))

    assert len(quarantined_files) == 1
