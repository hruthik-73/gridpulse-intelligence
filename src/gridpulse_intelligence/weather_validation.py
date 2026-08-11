"""Validation for NWS Bronze weather snapshots."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from gridpulse_intelligence.contracts import load_contract
from gridpulse_intelligence.models import WeatherForecastRecord

DEFAULT_NWS_CONTRACT_PATH = Path("contracts/nws_hourly_forecast.yaml")


class WeatherBronzeValidationError(Exception):
    """Raised when an NWS Bronze snapshot violates its contract."""


@dataclass(frozen=True)
class WeatherBronzeValidationReport:
    """Summary of a successfully validated weather snapshot."""

    snapshot_path: Path
    record_count: int
    unique_key_count: int


def validate_nws_bronze_snapshot(
    snapshot_path: Path,
    contract_path: Path = DEFAULT_NWS_CONTRACT_PATH,
) -> WeatherBronzeValidationReport:
    """Validate an NWS Bronze snapshot against its contract."""

    contract = load_contract(contract_path)

    try:
        payload_object: object = json.loads(
            snapshot_path.read_text(
                encoding="utf-8",
            )
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise WeatherBronzeValidationError(
            f"Unable to read Bronze snapshot: {snapshot_path}"
        ) from exc

    if not isinstance(payload_object, dict):
        raise WeatherBronzeValidationError("Bronze snapshot root must be a JSON object.")

    payload: dict[str, Any] = payload_object

    metadata_object = payload.get("metadata")

    if not isinstance(metadata_object, dict):
        raise WeatherBronzeValidationError("Bronze snapshot is missing metadata.")

    metadata: dict[str, Any] = metadata_object

    records_object = payload.get("records")

    if not isinstance(records_object, list):
        raise WeatherBronzeValidationError("Bronze snapshot is missing records.")

    required_metadata = contract["metadata"]["required"]

    for key in required_metadata:
        if key not in metadata:
            raise WeatherBronzeValidationError(f"Bronze metadata is missing {key}.")

    metadata_record_count = metadata.get("record_count")

    if not isinstance(
        metadata_record_count,
        int,
    ):
        raise WeatherBronzeValidationError("Bronze metadata record_count must be an integer.")

    if metadata_record_count != len(records_object):
        raise WeatherBronzeValidationError("Bronze metadata record_count does not match records.")

    expected_fields = set(contract["schema"]["fields"])

    uniqueness_columns = contract["quality"]["uniqueness"]["columns"]

    unique_keys: set[tuple[object, ...]] = set()

    for index, record_object in enumerate(records_object):
        if not isinstance(
            record_object,
            dict,
        ):
            raise WeatherBronzeValidationError(f"Record {index} must be a JSON object.")

        record: dict[str, Any] = record_object

        record_fields = set(record)

        missing_fields = expected_fields - record_fields

        if missing_fields:
            raise WeatherBronzeValidationError(
                f"Record {index} is missing fields: {sorted(missing_fields)}"
            )

        unknown_fields = record_fields - expected_fields

        if unknown_fields:
            raise WeatherBronzeValidationError(
                f"Record {index} contains unknown fields: {sorted(unknown_fields)}"
            )

        try:
            validated_record = WeatherForecastRecord.model_validate(record)
        except ValidationError as exc:
            raise WeatherBronzeValidationError(f"Record {index} failed model validation.") from exc

        if validated_record.period_end <= validated_record.period_start:
            raise WeatherBronzeValidationError(f"Record {index} has an invalid forecast interval.")

        key = tuple(record[column] for column in uniqueness_columns)

        if key in unique_keys:
            raise WeatherBronzeValidationError(f"Duplicate weather business key found: {key}")

        unique_keys.add(key)

    return WeatherBronzeValidationReport(
        snapshot_path=snapshot_path,
        record_count=len(records_object),
        unique_key_count=len(unique_keys),
    )
