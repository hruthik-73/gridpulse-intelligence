"""Tests for the National Weather Service API client."""

from datetime import datetime

import pytest

from gridpulse_intelligence.nws_client import NWSClient, NWSError


def make_client() -> NWSClient:
    """Create an NWS client without opening a real HTTP client."""

    return object.__new__(NWSClient)


def test_get_hourly_forecast_normalizes_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    requested_endpoints: list[str] = []

    def fake_request(endpoint: str) -> dict[str, object]:
        requested_endpoints.append(endpoint)

        if endpoint.startswith("/points/"):
            return {
                "properties": {
                    "forecastHourly": (
                        "https://api.weather.gov/gridpoints/CLE/82,67/forecast/hourly"
                    )
                }
            }

        return {
            "properties": {
                "periods": [
                    {
                        "startTime": "2026-08-11T14:00:00-04:00",
                        "endTime": "2026-08-11T15:00:00-04:00",
                        "temperature": 80,
                        "temperatureUnit": "F",
                        "probabilityOfPrecipitation": {
                            "unitCode": "wmoUnit:percent",
                            "value": 40,
                        },
                        "relativeHumidity": {
                            "unitCode": "wmoUnit:percent",
                            "value": 72,
                        },
                        "windSpeed": "8 mph",
                        "windDirection": "SW",
                        "shortForecast": ("Chance Showers And Thunderstorms"),
                    },
                    {
                        "startTime": "2026-08-11T15:00:00-04:00",
                        "endTime": "2026-08-11T16:00:00-04:00",
                        "temperature": 78,
                        "temperatureUnit": "F",
                        "probabilityOfPrecipitation": {
                            "unitCode": "wmoUnit:percent",
                            "value": 50,
                        },
                        "relativeHumidity": {
                            "unitCode": "wmoUnit:percent",
                            "value": 75,
                        },
                        "windSpeed": "9 mph",
                        "windDirection": "SW",
                        "shortForecast": ("Showers And Thunderstorms Likely"),
                    },
                ]
            }
        }

    monkeypatch.setattr(
        client,
        "_request",
        fake_request,
    )

    records = client.get_hourly_forecast(
        latitude=41.4993,
        longitude=-81.6944,
        limit=2,
    )

    assert len(records) == 2

    first = records[0]

    assert first.latitude == 41.4993
    assert first.longitude == -81.6944
    assert first.period_start == datetime.fromisoformat("2026-08-11T14:00:00-04:00")
    assert first.temperature == 80.0
    assert first.temperature_unit == "F"
    assert first.precipitation_probability == 40.0
    assert first.relative_humidity == 72.0
    assert first.wind_speed == "8 mph"
    assert first.wind_direction == "SW"

    assert requested_endpoints == [
        "/points/41.4993,-81.6944",
        ("https://api.weather.gov/gridpoints/CLE/82,67/forecast/hourly"),
    ]


def test_limit_restricts_forecast_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    def fake_request(endpoint: str) -> dict[str, object]:
        if endpoint.startswith("/points/"):
            return {"properties": {"forecastHourly": "https://example.test/hourly"}}

        periods = []

        for hour in range(3):
            periods.append(
                {
                    "startTime": (f"2026-08-11T{14 + hour:02d}:00:00-04:00"),
                    "endTime": (f"2026-08-11T{15 + hour:02d}:00:00-04:00"),
                    "temperature": 80 - hour,
                    "temperatureUnit": "F",
                    "probabilityOfPrecipitation": {
                        "value": 20,
                    },
                    "relativeHumidity": {
                        "value": 70,
                    },
                    "windSpeed": "5 mph",
                    "windDirection": "W",
                    "shortForecast": "Partly Cloudy",
                }
            )

        return {
            "properties": {
                "periods": periods,
            }
        }

    monkeypatch.setattr(
        client,
        "_request",
        fake_request,
    )

    records = client.get_hourly_forecast(
        latitude=41.4993,
        longitude=-81.6944,
        limit=1,
    )

    assert len(records) == 1


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (91.0, -81.6944),
        (-91.0, -81.6944),
        (41.4993, 181.0),
        (41.4993, -181.0),
    ],
)
def test_invalid_coordinates_fail(
    latitude: float,
    longitude: float,
) -> None:
    client = make_client()

    with pytest.raises(ValueError):
        client.get_hourly_forecast(
            latitude=latitude,
            longitude=longitude,
        )


def test_missing_forecast_periods_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    def fake_request(endpoint: str) -> dict[str, object]:
        if endpoint.startswith("/points/"):
            return {"properties": {"forecastHourly": "https://example.test/hourly"}}

        return {
            "properties": {},
        }

    monkeypatch.setattr(
        client,
        "_request",
        fake_request,
    )

    with pytest.raises(
        NWSError,
        match="forecast periods",
    ):
        client.get_hourly_forecast(
            latitude=41.4993,
            longitude=-81.6944,
        )


def test_null_weather_quantities_are_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_client()

    def fake_request(endpoint: str) -> dict[str, object]:
        if endpoint.startswith("/points/"):
            return {"properties": {"forecastHourly": "https://example.test/hourly"}}

        return {
            "properties": {
                "periods": [
                    {
                        "startTime": "2026-08-11T14:00:00-04:00",
                        "endTime": "2026-08-11T15:00:00-04:00",
                        "temperature": 80,
                        "temperatureUnit": "F",
                        "probabilityOfPrecipitation": {
                            "value": None,
                        },
                        "relativeHumidity": {
                            "value": None,
                        },
                        "windSpeed": "5 mph",
                        "windDirection": "W",
                        "shortForecast": "Mostly Sunny",
                    }
                ]
            }
        }

    monkeypatch.setattr(
        client,
        "_request",
        fake_request,
    )

    records = client.get_hourly_forecast(
        latitude=41.4993,
        longitude=-81.6944,
        limit=1,
    )

    assert records[0].precipitation_probability is None
    assert records[0].relative_humidity is None
