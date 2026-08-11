from pathlib import Path

from gridpulse_intelligence.contracts import load_contract

CONTRACT_PATH = Path("contracts/eia_region_data.yaml")


def test_eia_contract_loads() -> None:
    contract = load_contract(CONTRACT_PATH)

    assert contract["contract_version"] == "1.0"
    assert contract["dataset"]["name"] == "eia_region_data"
    assert contract["dataset"]["source"] == "eia"


def test_eia_contract_contains_expected_fields() -> None:
    contract = load_contract(CONTRACT_PATH)

    fields = contract["schema"]["fields"]

    expected_fields = {
        "period",
        "respondent",
        "respondent-name",
        "type",
        "type-name",
        "value",
        "value-units",
    }

    assert set(fields) == expected_fields


def test_eia_contract_required_fields() -> None:
    contract = load_contract(CONTRACT_PATH)

    fields = contract["schema"]["fields"]

    for field in fields.values():
        assert field["required"] is True


def test_eia_contract_has_uniqueness_rule() -> None:
    contract = load_contract(CONTRACT_PATH)

    uniqueness_columns = contract["quality"]["uniqueness"]["columns"]

    assert uniqueness_columns == [
        "period",
        "respondent",
        "type",
    ]


def test_eia_contract_requires_bronze_metadata() -> None:
    contract = load_contract(CONTRACT_PATH)

    required_metadata = contract["metadata"]["required"]

    assert "run_id" in required_metadata
    assert "ingested_at" in required_metadata
    assert "record_count" in required_metadata
