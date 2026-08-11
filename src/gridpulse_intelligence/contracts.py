"""Data contract utilities for GridPulse Intelligence."""

from pathlib import Path
from typing import Any

import yaml


class DataContractError(Exception):
    """Raised when a data contract is invalid."""


def load_contract(path: Path) -> dict[str, Any]:
    """Load and perform basic validation of a YAML data contract."""

    if not path.exists():
        raise DataContractError(f"Contract file does not exist: {path}")

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        contract = yaml.safe_load(file)

    if not isinstance(contract, dict):
        raise DataContractError("Contract root must be a mapping.")

    required_sections = {
        "contract_version",
        "dataset",
        "source",
        "schema",
        "quality",
        "storage",
        "metadata",
    }

    missing_sections = required_sections - contract.keys()

    if missing_sections:
        missing = ", ".join(sorted(missing_sections))

        raise DataContractError(f"Contract is missing required sections: {missing}")

    dataset = contract.get("dataset")

    if not isinstance(dataset, dict):
        raise DataContractError("dataset section must be a mapping.")

    if not dataset.get("name"):
        raise DataContractError("dataset.name is required.")

    schema = contract.get("schema")

    if not isinstance(schema, dict):
        raise DataContractError("schema section must be a mapping.")

    fields = schema.get("fields")

    if not isinstance(fields, dict) or not fields:
        raise DataContractError("schema.fields must contain at least one field.")

    return contract
