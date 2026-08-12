from pathlib import Path

from gridpulse_intelligence.contracts import load_contract


def test_afdc_contract_definition() -> None:
    contract = load_contract(Path("contracts/afdc_ev_stations.yaml"))

    assert contract["dataset"]["name"] == "afdc_ev_stations"
    assert contract["dataset"]["source"] == "afdc"

    assert contract["quality"]["uniqueness"]["columns"] == [
        "station_id",
    ]

    required_metadata = set(contract["metadata"]["required"])

    assert {
        "run_id",
        "ingested_at",
        "record_count",
        "query_state",
        "total_results",
    }.issubset(required_metadata)
