"""Tests for the GridPulse FastAPI serving layer."""

from collections.abc import Generator
from datetime import datetime

import pytest
from fastapi.testclient import (
    TestClient,
)

from gridpulse_intelligence.api import (
    app,
    get_repository,
)
from gridpulse_intelligence.api_repository import (
    GridPulseRepositoryError,
)


class FakeRepository:
    """In-memory API repository for tests."""

    def platform_status(
        self,
    ) -> dict[str, int]:
        """Return deterministic platform counts."""

        return {
            "grid_hourly_rows": 58,
            "balancing_authorities": 53,
            "ev_cities": 4,
            "weather_forecasts": 5,
        }

    def balancing_authorities(
        self,
        *,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return deterministic grid analytics."""

        rows: list[dict[str, object]] = [
            {
                "respondent": "PJM",
                "respondent_name": ("PJM Interconnection"),
                "observed_hours": 2,
                "demand_hours": 2,
                "forecast_pair_hours": 1,
                "generation_pair_hours": 1,
                "average_demand_mwh": 100.0,
                "peak_demand_mwh": 120.0,
                "mean_abs_forecast_error_mwh": 5.0,
                "mean_abs_forecast_error_pct": 4.2,
                "average_generation_demand_gap_mwh": 10.0,
                "forecast_coverage_pct": 50.0,
                "generation_coverage_pct": 50.0,
                "forecast_accuracy_rank": 1,
                "peak_demand_rank": 1,
                "contains_replay": True,
                "latest_kafka_timestamp": datetime(
                    2026,
                    8,
                    12,
                    14,
                    0,
                ),
            }
        ]

        return rows[:limit]

    def ev_cities(
        self,
        *,
        state: str | None,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return deterministic EV analytics."""

        rows: list[dict[str, object]] = [
            {
                "city_state_key": ("Cleveland|OH|US"),
                "city": "Cleveland",
                "state": "OH",
                "country": "US",
                "station_count": 2,
                "level1_ports": 0,
                "level2_ports": 5,
                "dc_fast_ports": 2,
                "total_known_ports": 7,
                "dc_fast_station_count": 1,
                "network_count": 2,
                "ports_per_station": 3.5,
                "dc_fast_station_share_pct": 50.0,
                "state_station_rank": 1,
                "national_station_rank": 1,
                "state_port_rank": 1,
                "latest_station_update": datetime(
                    2026,
                    7,
                    10,
                    10,
                    0,
                ),
            }
        ]

        if state is not None:
            rows = [row for row in rows if row["state"] == state.upper()]

        return rows[:limit]

    def weather_forecasts(
        self,
        *,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return deterministic weather analytics."""

        rows: list[dict[str, object]] = [
            {
                "weather_forecast_key": ("41.4993,-81.6944|2026-08-12 11:00:00"),
                "location_key": ("41.4993,-81.6944"),
                "latitude": 41.4993,
                "longitude": -81.6944,
                "period_start": datetime(
                    2026,
                    8,
                    12,
                    11,
                    0,
                ),
                "period_end": datetime(
                    2026,
                    8,
                    12,
                    12,
                    0,
                ),
                "forecast_hour": 11,
                "temperature_f": 74.0,
                "temperature_c": 23.333333,
                "precipitation_probability": 28.0,
                "precipitation_risk": "moderate",
                "relative_humidity": 87.0,
                "wind_speed": "2 mph",
                "wind_direction": "W",
                "short_forecast": ("Chance Showers"),
                "replay": False,
                "kafka_partition": 1,
                "kafka_offset": 5,
                "kafka_timestamp": datetime(
                    2026,
                    8,
                    12,
                    14,
                    0,
                ),
            }
        ]

        return rows[:limit]


class FailingRepository(FakeRepository):
    """Repository that simulates warehouse failure."""

    def platform_status(
        self,
    ) -> dict[str, int]:
        """Simulate an unavailable DuckDB warehouse."""

        raise GridPulseRepositoryError("Warehouse unavailable.")


@pytest.fixture
def client() -> Generator[
    TestClient,
    None,
    None,
]:
    """Create FastAPI client with repository override."""

    app.dependency_overrides[get_repository] = FakeRepository

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_health(
    client: TestClient,
) -> None:
    """Health endpoint should remain lightweight."""

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": ("gridpulse-intelligence-api"),
    }


def test_platform_status(
    client: TestClient,
) -> None:
    """Status endpoint should expose serving counts."""

    response = client.get("/api/v1/status")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "database": "duckdb",
        "grid_hourly_rows": 58,
        "balancing_authorities": 53,
        "ev_cities": 4,
        "weather_forecasts": 5,
    }


def test_grid_authorities(
    client: TestClient,
) -> None:
    """Grid endpoint should return typed analytics."""

    response = client.get(
        "/api/v1/grid/authorities",
        params={
            "limit": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["respondent"] == "PJM"

    assert body[0]["peak_demand_mwh"] == 120.0

    assert body[0]["contains_replay"] is True


def test_invalid_grid_limit_returns_422(
    client: TestClient,
) -> None:
    """FastAPI should enforce endpoint limits."""

    response = client.get(
        "/api/v1/grid/authorities",
        params={
            "limit": 0,
        },
    )

    assert response.status_code == 422


def test_ev_state_filter(
    client: TestClient,
) -> None:
    """EV endpoint should support state filtering."""

    response = client.get(
        "/api/v1/ev/cities",
        params={
            "state": "oh",
            "limit": 10,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["city"] == "Cleveland"
    assert body[0]["state"] == "OH"


def test_weather_endpoint(
    client: TestClient,
) -> None:
    """Weather endpoint should return forecast data."""

    response = client.get(
        "/api/v1/weather",
        params={
            "limit": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1

    assert body[0]["precipitation_risk"] == "moderate"

    assert body[0]["temperature_f"] == 74.0


def test_repository_failure_returns_503() -> None:
    """Warehouse failures should become HTTP 503."""

    app.dependency_overrides[get_repository] = FailingRepository

    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/v1/status")

        assert response.status_code == 503

        assert response.json()["detail"] == "Warehouse unavailable."

    finally:
        app.dependency_overrides.clear()


def test_local_frontend_cors(
    client: TestClient,
) -> None:
    """The local Next.js origin should pass CORS."""

    response = client.options(
        "/api/v1/status",
        headers={
            "Origin": ("http://localhost:3001"),
            ("Access-Control-Request-Method"): "GET",
        },
    )

    assert response.status_code == 200

    assert response.headers["access-control-allow-origin"] == "http://localhost:3001"


def test_prometheus_metrics_are_exposed(
    client: TestClient,
) -> None:
    """FastAPI metrics should be available to Prometheus."""

    health_response = client.get("/health")

    assert health_response.status_code == 200

    response = client.get("/metrics/")

    assert response.status_code == 200

    body = response.text

    assert "gridpulse_api_requests_total" in body

    assert "gridpulse_api_request_duration_seconds" in body
