import json
from pathlib import Path

import pytest

from gridpulse_intelligence.quality_gate import (
    QualityGateError,
    validate_or_quarantine_ev_snapshot,
)


def write_snapshot(
    path: Path,
    invalid: bool = False,
) -> None:
    record: dict[str, object] = {
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

    if invalid:
        record["unexpected"] = "invalid"

    payload = {
        "metadata": {
            "source": "afdc",
            "dataset": "afdc_ev_stations",
            "schema_version": "1.0",
            "run_id": "test-run",
            "ingested_at": "2026-08-11T20:00:00+00:00",
            "record_count": 1,
            "query_state": "OH",
            "total_results": 1915,
        },
        "records": [record],
    }

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_ev_quality_gate_passes(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "ev.json"
    quarantine = tmp_path / "quarantine"

    write_snapshot(snapshot)

    report = validate_or_quarantine_ev_snapshot(
        snapshot_path=snapshot,
        quarantine_root=quarantine,
    )

    assert report.record_count == 1
    assert snapshot.exists()


def test_invalid_ev_snapshot_is_quarantined(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "ev.json"
    quarantine = tmp_path / "quarantine"

    write_snapshot(
        snapshot,
        invalid=True,
    )

    with pytest.raises(QualityGateError):
        validate_or_quarantine_ev_snapshot(
            snapshot_path=snapshot,
            quarantine_root=quarantine,
        )

    assert not snapshot.exists()

    assert len(list(quarantine.rglob("*.json"))) == 1
