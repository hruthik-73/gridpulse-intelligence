"""Validation utilities for Bronze-layer snapshots."""

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from gridpulse_intelligence.contracts import load_contract
from gridpulse_intelligence.models import GridRegionRecord


class BronzeValidationError(Exception):
    """Raised when a Bronze snapshot violates its data contract."""


@dataclass(frozen=True)
class BronzeValidationReport:
    """Summary produced after successful Bronze validation."""

    snapshot_path: Path
    record_count: int
    unique_key_count: int


def validate_eia_bronze_snapshot(
    snapshot_path: Path,
    contract_path: Path = Path("contracts/eia_region_data.yaml"),
) -> BronzeValidationReport:
    """Validate an EIA Bronze snapshot against its data contract."""

    if not snapshot_path.exists():
        raise BronzeValidationError(f"Snapshot does not exist: {snapshot_path}")

    contract = load_contract(contract_path)

    with snapshot_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload: object = json.load(file)

    if not isinstance(payload, dict):
        raise BronzeValidationError("Bronze snapshot root must be a JSON object.")

    metadata = payload.get("metadata")
    records = payload.get("records")

    if not isinstance(metadata, dict):
        raise BronzeValidationError("Bronze snapshot is missing valid metadata.")

    if not isinstance(records, list):
        raise BronzeValidationError("Bronze snapshot is missing a records list.")

    required_metadata = contract["metadata"]["required"]

    if not isinstance(required_metadata, list):
        raise BronzeValidationError("Contract metadata.required must be a list.")

    missing_metadata = [
        field for field in required_metadata if isinstance(field, str) and field not in metadata
    ]

    if missing_metadata:
        raise BronzeValidationError(
            "Missing required metadata: " + ", ".join(sorted(missing_metadata))
        )

    declared_record_count = metadata.get("record_count")

    if not isinstance(declared_record_count, int):
        raise BronzeValidationError("metadata.record_count must be an integer.")

    if declared_record_count != len(records):
        raise BronzeValidationError("metadata.record_count does not match the number of records.")

    schema = contract["schema"]

    if not isinstance(schema, dict):
        raise BronzeValidationError("Contract schema must be a mapping.")

    contract_fields = schema.get("fields")

    if not isinstance(contract_fields, dict):
        raise BronzeValidationError("Contract schema.fields must be a mapping.")

    expected_fields = set(contract_fields)

    quality = contract["quality"]

    if not isinstance(quality, dict):
        raise BronzeValidationError("Contract quality section must be a mapping.")

    uniqueness = quality.get("uniqueness")

    if not isinstance(uniqueness, dict):
        raise BronzeValidationError("Contract uniqueness rule must be a mapping.")

    uniqueness_columns = uniqueness.get("columns")

    if not isinstance(uniqueness_columns, list):
        raise BronzeValidationError("Contract uniqueness columns must be a list.")

    uniqueness_fields = [column for column in uniqueness_columns if isinstance(column, str)]

    seen_keys: set[tuple[str, ...]] = set()

    for index, raw_record in enumerate(records):
        if not isinstance(raw_record, dict):
            raise BronzeValidationError(f"Record {index} must be a JSON object.")

        normalized_record = {str(key): value for key, value in raw_record.items()}

        actual_fields = set(normalized_record)

        missing_fields = expected_fields - actual_fields
        unknown_fields = actual_fields - expected_fields

        if missing_fields:
            raise BronzeValidationError(
                f"Record {index} is missing fields: " + ", ".join(sorted(missing_fields))
            )

        if unknown_fields:
            raise BronzeValidationError(
                f"Record {index} contains unknown fields: " + ", ".join(sorted(unknown_fields))
            )

        try:
            GridRegionRecord.model_validate(normalized_record)
        except ValidationError as exc:
            raise BronzeValidationError(f"Record {index} failed schema validation.") from exc

        uniqueness_key = tuple(str(normalized_record.get(column)) for column in uniqueness_fields)

        if uniqueness_key in seen_keys:
            raise BronzeValidationError(
                f"Duplicate uniqueness key found in record {index}: {uniqueness_key}"
            )

        seen_keys.add(uniqueness_key)

    return BronzeValidationReport(
        snapshot_path=snapshot_path,
        record_count=len(records),
        unique_key_count=len(seen_keys),
    )
