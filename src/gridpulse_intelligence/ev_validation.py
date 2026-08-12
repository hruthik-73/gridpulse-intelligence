"""Validation for AFDC EV charging station Bronze snapshots."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from gridpulse_intelligence.contracts import load_contract
from gridpulse_intelligence.models import EVChargingStationRecord

DEFAULT_EV_CONTRACT_PATH = Path("contracts/afdc_ev_stations.yaml")


class EVBronzeValidationError(Exception):
    """Raised when an EV Bronze snapshot violates its contract."""


@dataclass(frozen=True)
class EVBronzeValidationReport:
    """Summary of a successfully validated EV snapshot."""

    snapshot_path: Path
    record_count: int
    unique_key_count: int


def validate_ev_bronze_snapshot(
    snapshot_path: Path,
    contract_path: Path = DEFAULT_EV_CONTRACT_PATH,
) -> EVBronzeValidationReport:
    """Validate an AFDC EV Bronze snapshot against its contract."""

    contract = load_contract(contract_path)

    try:
        payload_object: object = json.loads(
            snapshot_path.read_text(
                encoding="utf-8",
            )
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise EVBronzeValidationError(f"Unable to read Bronze snapshot: {snapshot_path}") from exc

    if not isinstance(payload_object, dict):
        raise EVBronzeValidationError("Bronze snapshot root must be a JSON object.")

    payload: dict[str, Any] = payload_object

    metadata_object = payload.get("metadata")

    if not isinstance(metadata_object, dict):
        raise EVBronzeValidationError("Bronze snapshot is missing metadata.")

    metadata: dict[str, Any] = metadata_object

    records_object = payload.get("records")

    if not isinstance(records_object, list):
        raise EVBronzeValidationError("Bronze snapshot is missing records.")

    required_metadata = contract["metadata"]["required"]

    for key in required_metadata:
        if key not in metadata:
            raise EVBronzeValidationError(f"Bronze metadata is missing {key}.")

    metadata_record_count = metadata.get("record_count")

    if not isinstance(metadata_record_count, int):
        raise EVBronzeValidationError("Bronze metadata record_count must be an integer.")

    if metadata_record_count != len(records_object):
        raise EVBronzeValidationError("Bronze metadata record_count does not match records.")

    total_results = metadata.get("total_results")

    if not isinstance(total_results, int):
        raise EVBronzeValidationError("Bronze metadata total_results must be an integer.")

    if total_results < metadata_record_count:
        raise EVBronzeValidationError("Bronze metadata total_results is smaller than record_count.")

    query_state = metadata.get("query_state")

    if not isinstance(query_state, str) or len(query_state) != 2 or not query_state.isalpha():
        raise EVBronzeValidationError("Bronze metadata query_state is invalid.")

    expected_fields = set(contract["schema"]["fields"])

    uniqueness_columns = contract["quality"]["uniqueness"]["columns"]

    unique_keys: set[tuple[object, ...]] = set()

    for index, record_object in enumerate(records_object):
        if not isinstance(record_object, dict):
            raise EVBronzeValidationError(f"Record {index} must be a JSON object.")

        record: dict[str, Any] = record_object

        record_fields = set(record)

        missing_fields = expected_fields - record_fields

        if missing_fields:
            raise EVBronzeValidationError(
                f"Record {index} is missing fields: {sorted(missing_fields)}"
            )

        unknown_fields = record_fields - expected_fields

        if unknown_fields:
            raise EVBronzeValidationError(
                f"Record {index} contains unknown fields: {sorted(unknown_fields)}"
            )

        try:
            validated_record = EVChargingStationRecord.model_validate(record)
        except ValidationError as exc:
            raise EVBronzeValidationError(f"Record {index} failed model validation.") from exc

        if validated_record.state != query_state.upper():
            raise EVBronzeValidationError(f"Record {index} state does not match query_state.")

        key = tuple(record[column] for column in uniqueness_columns)

        if key in unique_keys:
            raise EVBronzeValidationError(f"Duplicate EV business key found: {key}")

        unique_keys.add(key)

    return EVBronzeValidationReport(
        snapshot_path=snapshot_path,
        record_count=len(records_object),
        unique_key_count=len(unique_keys),
    )
