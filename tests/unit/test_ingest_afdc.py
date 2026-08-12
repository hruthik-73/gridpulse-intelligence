"""Tests for AFDC ingestion orchestration."""

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

import gridpulse_intelligence.ingest_afdc as ingest_afdc
from gridpulse_intelligence.models import EVChargingStationRecord


def sample_ev_record() -> EVChargingStationRecord:
    """Return a valid EV charging station record."""

    return EVChargingStationRecord(
        station_id=37097,
        station_name="Baker Electric Building",
        street_address="123 Main Street",
        city="Cleveland",
        state="OH",
        zip_code="44114",
        country="US",
        latitude=41.4993,
        longitude=-81.6944,
        fuel_type_code="ELEC",
        access_code="public",
        status_code="E",
        ev_network="Non-Networked",
        ev_connector_types=["J1772"],
        ev_level2_evse_num=2,
        ev_dc_fast_num=0,
    )


def test_run_ingestion_executes_complete_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful AFDC ingestion should write and validate Bronze data."""

    bronze_path = tmp_path / "ev.json"

    state: dict[str, object] = {
        "client_closed": False,
    }

    class FakeAFDCClient:
        MAX_LIMIT = 200

        def get_public_ev_stations(
            self,
            state: str,
            limit: int,
        ) -> tuple[list[EVChargingStationRecord], int]:
            globals_state = {
                "state": state,
                "limit": limit,
            }

            state_store.update(globals_state)

            return [
                sample_ev_record(),
            ], 1916

        def close(self) -> None:
            state_store["client_closed"] = True

    state_store = state

    def fake_write(
        records: list[EVChargingStationRecord],
        query_state: str,
        total_results: int,
    ) -> Path:
        state_store["written_records"] = len(records)
        state_store["query_state"] = query_state
        state_store["total_results"] = total_results

        return bronze_path

    def fake_quality_gate(
        snapshot_path: Path,
    ) -> SimpleNamespace:
        state_store["validated_path"] = snapshot_path

        return SimpleNamespace(
            record_count=1,
            unique_key_count=1,
        )

    monkeypatch.setattr(
        ingest_afdc,
        "AFDCClient",
        FakeAFDCClient,
    )

    monkeypatch.setattr(
        ingest_afdc,
        "write_ev_bronze_snapshot",
        fake_write,
    )

    monkeypatch.setattr(
        ingest_afdc,
        "validate_or_quarantine_ev_snapshot",
        fake_quality_gate,
    )

    ingest_afdc.run_ingestion(
        state="OH",
        limit=25,
    )

    assert state_store["state"] == "OH"
    assert state_store["limit"] == 25
    assert state_store["written_records"] == 1
    assert state_store["query_state"] == "OH"
    assert state_store["total_results"] == 1916
    assert state_store["validated_path"] == bronze_path
    assert state_store["client_closed"] is True


def test_empty_afdc_response_fails_before_bronze_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty upstream response must not create Bronze data."""

    state: dict[str, object] = {
        "client_closed": False,
        "writer_called": False,
    }

    class FakeAFDCClient:
        MAX_LIMIT = 200

        def get_public_ev_stations(
            self,
            state: str,
            limit: int,
        ) -> tuple[list[EVChargingStationRecord], int]:
            del state, limit
            return [], 0

        def close(self) -> None:
            state_store["client_closed"] = True

    state_store = state

    def fake_write(
        records: list[EVChargingStationRecord],
        query_state: str,
        total_results: int,
    ) -> Path:
        del records, query_state, total_results

        state_store["writer_called"] = True

        return Path("should-not-exist.json")

    monkeypatch.setattr(
        ingest_afdc,
        "AFDCClient",
        FakeAFDCClient,
    )

    monkeypatch.setattr(
        ingest_afdc,
        "write_ev_bronze_snapshot",
        fake_write,
    )

    with pytest.raises(
        RuntimeError,
        match="no public EV charging stations",
    ):
        ingest_afdc.run_ingestion(
            state="OH",
            limit=25,
        )

    assert state_store["writer_called"] is False
    assert state_store["client_closed"] is True


def test_state_code_normalizes_valid_value() -> None:
    """State codes should normalize to uppercase."""

    assert ingest_afdc.state_code(" oh ") == "OH"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "O",
        "OHIO",
        "12",
    ],
)
def test_state_code_rejects_invalid_values(
    value: str,
) -> None:
    """Malformed state codes should be rejected."""

    with pytest.raises(
        argparse.ArgumentTypeError,
    ):
        ingest_afdc.state_code(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", 1),
        ("25", 25),
        ("200", 200),
    ],
)
def test_station_limit_accepts_valid_values(
    value: str,
    expected: int,
) -> None:
    """Valid station limits should parse successfully."""

    assert ingest_afdc.station_limit(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "201",
        "invalid",
    ],
)
def test_station_limit_rejects_invalid_values(
    value: str,
) -> None:
    """Invalid station limits should be rejected."""

    with pytest.raises(
        argparse.ArgumentTypeError,
    ):
        ingest_afdc.station_limit(value)
