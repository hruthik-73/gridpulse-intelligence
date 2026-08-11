from pathlib import Path

from gridpulse_intelligence.contracts import load_contract


def test_nws_contract_definition() -> None:
    contract = load_contract(Path("contracts/nws_hourly_forecast.yaml"))

    assert contract["dataset"]["name"] == "nws_hourly_forecast"

    assert contract["dataset"]["source"] == "nws"

    assert set(contract["schema"]["fields"]) == {
        "latitude",
        "longitude",
        "period_start",
        "period_end",
        "temperature",
        "temperature_unit",
        "precipitation_probability",
        "relative_humidity",
        "wind_speed",
        "wind_direction",
        "short_forecast",
    }

    assert contract["quality"]["uniqueness"]["columns"] == [
        "latitude",
        "longitude",
        "period_start",
    ]
