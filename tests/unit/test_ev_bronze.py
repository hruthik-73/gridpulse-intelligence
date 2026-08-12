import json
from pathlib import Path

from gridpulse_intelligence.ev_bronze import (
    write_ev_bronze_snapshot,
)
from gridpulse_intelligence.models import (
    EVChargingStationRecord,
)


def test_write_ev_bronze_snapshot(
    tmp_path: Path,
) -> None:
    record = EVChargingStationRecord(
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

    output_path = write_ev_bronze_snapshot(
        records=[record],
        query_state="OH",
        total_results=1915,
        output_root=tmp_path,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["metadata"]["source"] == "afdc"
    assert payload["metadata"]["record_count"] == 1
    assert payload["metadata"]["query_state"] == "OH"
    assert payload["metadata"]["total_results"] == 1915

    assert payload["records"][0]["station_id"] == 37097
