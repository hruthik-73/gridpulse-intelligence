import json
from pathlib import Path

import pytest

from gridpulse_intelligence.bronze_validation import (
    BronzeValidationError,
    validate_eia_bronze_snapshot,
)


def write_snapshot(
    path: Path,
    records: list[dict[str, object]],
    record_count: int | None = None,
) -> None:
    payload = {
        "metadata": {
            "source": "eia",
            "dataset": "electricity/rto/region-data",
            "schema_version": "1.0",
            "run_id": "test-run-001",
            "ingested_at": "2026-08-11T18:00:00+00:00",
            "record_count": (len(records) if record_count is None else record_count),
        },
        "records": records,
    }

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def sample_record() -> dict[str, object]:
    return {
        "period": "2026-08-12T07:00:00",
        "respondent": "CAL",
        "respondent-name": "California",
        "type": "DF",
        "type-name": "Day-ahead demand forecast",
        "value": 37905.0,
        "value-units": "megawatthours",
    }


def test_valid_bronze_snapshot_passes(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "snapshot.json"

    write_snapshot(
        snapshot,
        [sample_record()],
    )

    report = validate_eia_bronze_snapshot(
        snapshot,
    )

    assert report.record_count == 1
    assert report.unique_key_count == 1


def test_wrong_record_count_fails(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "snapshot.json"

    write_snapshot(
        snapshot,
        [sample_record()],
        record_count=99,
    )

    with pytest.raises(
        BronzeValidationError,
        match="record_count",
    ):
        validate_eia_bronze_snapshot(
            snapshot,
        )


def test_unknown_field_fails(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "snapshot.json"

    record = sample_record()
    record["unexpected-field"] = "bad-data"

    write_snapshot(
        snapshot,
        [record],
    )

    with pytest.raises(
        BronzeValidationError,
        match="unknown fields",
    ):
        validate_eia_bronze_snapshot(
            snapshot,
        )


def test_duplicate_business_key_fails(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "snapshot.json"

    first = sample_record()
    duplicate = sample_record()

    write_snapshot(
        snapshot,
        [
            first,
            duplicate,
        ],
    )

    with pytest.raises(
        BronzeValidationError,
        match="Duplicate uniqueness key",
    ):
        validate_eia_bronze_snapshot(
            snapshot,
        )


def test_missing_required_field_fails(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "snapshot.json"

    record = sample_record()
    del record["respondent-name"]

    write_snapshot(
        snapshot,
        [record],
    )

    with pytest.raises(
        BronzeValidationError,
        match="missing fields",
    ):
        validate_eia_bronze_snapshot(
            snapshot,
        )
