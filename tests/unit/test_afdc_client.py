"""Tests for the AFDC EV charging station client."""

import pytest

from gridpulse_intelligence.afdc_client import (
    AFDCClient,
    AFDCError,
)


def make_client() -> AFDCClient:
    """Create an AFDC client without opening a real HTTP client."""

    return object.__new__(AFDCClient)


def station_payload(
    station_id: int = 37097,
    station_name: str = "Baker Electric Building",
) -> dict[str, object]:
    """Return a representative AFDC EV station payload."""

    return {
        "id": station_id,
        "station_name": station_name,
        "street_address": "123 Main Street",
        "city": "Cleveland",
        "state": "OH",
        "zip": "44114",
        "country": "US",
        "latitude": 41.4993,
        "longitude": -81.6944,
        "fuel_type_code": "ELEC",
        "access_code": "public",
        "status_code": "E",
        "ev_network": "Non-Networked",
        "ev_connector_types": [
            "J1772",
        ],
        "ev_level1_evse_num": None,
        "ev_level2_evse_num": 2,
        "ev_dc_fast_num": 0,
        "facility_type": "OFFICE_BLDG",
        "date_last_confirmed": "2026-08-01",
        "updated_at": "2026-08-01T12:00:00Z",
    }


def test_normalize_station() -> None:
    """AFDC station fields should normalize into the typed model."""

    client = make_client()

    record = client._normalize_station(station_payload())

    assert record.station_id == 37097
    assert record.station_name == "Baker Electric Building"
    assert record.city == "Cleveland"
    assert record.state == "OH"
    assert record.country == "US"
    assert record.fuel_type_code == "ELEC"
    assert record.access_code == "public"
    assert record.status_code == "E"
    assert record.ev_network == "Non-Networked"
    assert record.ev_connector_types == [
        "J1772",
    ]
    assert record.ev_level2_evse_num == 2
    assert record.ev_dc_fast_num == 0


def test_get_public_ev_stations_filters_and_sorts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public EV query should use expected filters and stable ordering."""

    client = make_client()

    captured_params: dict[str, str] = {}

    def fake_request(
        params: dict[str, str],
    ) -> dict[str, object]:
        captured_params.update(params)

        return {
            "total_results": 1915,
            "fuel_stations": [
                station_payload(
                    station_id=42640,
                    station_name=("Ohio Statehouse Parking Garage"),
                ),
                station_payload(
                    station_id=37097,
                    station_name=("Baker Electric Building"),
                ),
            ],
        }

    monkeypatch.setattr(
        client,
        "_request",
        fake_request,
    )

    records, total = client.get_public_ev_stations(
        state="oh",
        limit=2,
    )

    assert total == 1915
    assert len(records) == 2

    assert [record.station_id for record in records] == [
        37097,
        42640,
    ]

    assert captured_params == {
        "fuel_type": "ELEC",
        "access": "public",
        "status": "E",
        "country": "US",
        "state": "OH",
        "limit": "2",
    }


@pytest.mark.parametrize(
    "state",
    [
        "",
        "O",
        "OHIO",
        "12",
    ],
)
def test_invalid_state_fails(
    state: str,
) -> None:
    """Invalid state codes should be rejected before an API request."""

    client = make_client()

    with pytest.raises(
        ValueError,
        match="two-letter code",
    ):
        client.get_public_ev_stations(
            state=state,
        )


@pytest.mark.parametrize(
    "limit",
    [
        0,
        201,
    ],
)
def test_invalid_limit_fails(
    limit: int,
) -> None:
    """Station request limits must remain inside AFDC bounds."""

    client = make_client()

    with pytest.raises(
        ValueError,
        match="limit must be between",
    ):
        client.get_public_ev_stations(
            state="OH",
            limit=limit,
        )


def test_missing_station_array_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed AFDC responses should fail explicitly."""

    client = make_client()

    def fake_request(
        params: dict[str, str],
    ) -> dict[str, object]:
        del params

        return {
            "total_results": 100,
        }

    monkeypatch.setattr(
        client,
        "_request",
        fake_request,
    )

    with pytest.raises(
        AFDCError,
        match="fuel_stations",
    ):
        client.get_public_ev_stations(
            state="OH",
            limit=2,
        )


def test_invalid_connector_type_fails() -> None:
    """Malformed connector values should not enter the platform."""

    client = make_client()

    station = station_payload()

    station["ev_connector_types"] = [
        "J1772",
        123,
    ]

    with pytest.raises(
        AFDCError,
        match="connector type",
    ):
        client._normalize_station(station)
