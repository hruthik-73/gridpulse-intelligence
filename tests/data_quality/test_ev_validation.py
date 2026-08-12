import json
from pathlib import Path

import pytest

from gridpulse_intelligence.ev_validation import (
    EVBronzeValidationError,
    validate_ev_bronze_snapshot,
)


def sample_record() -> dict[str, object]:
    return {
        "station_id": 37097,
        "station_name": "Baker Electric Building",
        "street_address": "123 Main Street",
        "city": "Cleveland",
        "state": "OH",
        "zip_code": "44114",
        "country": "US",
        "latitude": 41.4993,
        "longitude": -81.6944,
        "fuel_type_code": "ELEC",
        "access_code": "public",
        "status_code": "E",
        "ev_network": "Non-Networked",
        "ev_connector_types": ["J1772"],
        "ev_level1_evse_num": None,
        "ev_level2_evse_num": 2,
        "ev_dc_fast_num": 0,
        "facility_type": None,
        "date_last_confirmed": None,
        "updated_at": None,
    }


def write_snapshot(
    path: Path,
    records: list[dict[str, object]],
    query_state: str = "OH",
    total_results: int = 1915,
) -> None:
    payload = {
        "metadata": {
            "source": "afdc",
            "dataset": "afdc_ev_stations",
            "schema_version": "1.0",
            "run_id": "test-run",
            "ingested_at": "2026-08-11T20:00:00+00:00",
            "record_count": len(records),
            "query_state": query_state,
            "total_results": total_results,
        },
        "records": records,
    }

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_valid_ev_snapshot(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ev.json"

    write_snapshot(
        path,
        [sample_record()],
    )

    report = validate_ev_bronze_snapshot(path)

    assert report.record_count == 1
    assert report.unique_key_count == 1


def test_duplicate_station_id_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ev.json"
    record = sample_record()

    write_snapshot(
        path,
        [
            record,
            record.copy(),
        ],
    )

    with pytest.raises(
        EVBronzeValidationError,
        match="Duplicate",
    ):
        validate_ev_bronze_snapshot(path)


def test_station_state_must_match_query_state(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ev.json"

    record = sample_record()
    record["state"] = "PA"

    write_snapshot(
        path,
        [record],
        query_state="OH",
    )

    with pytest.raises(
        EVBronzeValidationError,
        match="query_state",
    ):
        validate_ev_bronze_snapshot(path)


def test_unknown_ev_field_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ev.json"

    record = sample_record()
    record["unexpected"] = "bad"

    write_snapshot(
        path,
        [record],
    )

    with pytest.raises(
        EVBronzeValidationError,
        match="unknown fields",
    ):
        validate_ev_bronze_snapshot(path)
