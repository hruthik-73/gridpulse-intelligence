"""Runtime health checks for GridPulse platform components."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import httpx
from confluent_kafka.admin import AdminClient

from gridpulse_intelligence.api_repository import (
    GridPulseRepository,
)
from gridpulse_intelligence.config import (
    get_settings,
)

REQUIRED_TOPICS = {
    "gridpulse.eia.region-data.v1",
    "gridpulse.nws.forecast.v1",
    "gridpulse.afdc.ev-stations.v1",
    "gridpulse.dead-letter.v1",
}

DEFAULT_PROMETHEUS_URL = "http://127.0.0.1:9090"


@dataclass(frozen=True)
class ComponentHealth:
    """Health result for one platform component."""

    status: str
    detail: str
    latency_ms: float


class PlatformHealthService:
    """Check GridPulse infrastructure dependencies."""

    def __init__(
        self,
        repository: GridPulseRepository,
        prometheus_url: str = DEFAULT_PROMETHEUS_URL,
    ) -> None:
        self.repository = repository
        self.prometheus_url = prometheus_url.rstrip("/")

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> float:
        return round(
            (perf_counter() - started_at) * 1000,
            2,
        )

    def check_duckdb(
        self,
    ) -> ComponentHealth:
        """Verify the analytics warehouse is queryable."""

        started_at = perf_counter()

        try:
            counts = self.repository.platform_status()

            return ComponentHealth(
                status="healthy",
                detail=(
                    f"Warehouse query succeeded; {counts['grid_hourly_rows']} grid rows available."
                ),
                latency_ms=self._elapsed_ms(started_at),
            )

        except Exception as exc:
            return ComponentHealth(
                status="unhealthy",
                detail=(f"Warehouse query failed: {type(exc).__name__}"),
                latency_ms=self._elapsed_ms(started_at),
            )

    def check_kafka(
        self,
    ) -> ComponentHealth:
        """Verify Kafka and required topics are available."""

        started_at = perf_counter()

        try:
            settings = get_settings()

            admin = AdminClient({"bootstrap.servers": (settings.kafka_bootstrap_servers)})

            metadata = admin.list_topics(timeout=2.0)

            available_topics = set(metadata.topics)

            missing_topics = REQUIRED_TOPICS - available_topics

            if missing_topics:
                return ComponentHealth(
                    status="degraded",
                    detail=("Kafka reachable but missing: " + ", ".join(sorted(missing_topics))),
                    latency_ms=self._elapsed_ms(started_at),
                )

            return ComponentHealth(
                status="healthy",
                detail=("Kafka reachable; all required GridPulse topics exist."),
                latency_ms=self._elapsed_ms(started_at),
            )

        except Exception as exc:
            return ComponentHealth(
                status="unhealthy",
                detail=(f"Kafka unavailable: {type(exc).__name__}"),
                latency_ms=self._elapsed_ms(started_at),
            )

    def check_prometheus(
        self,
    ) -> ComponentHealth:
        """Verify the Prometheus server is ready."""

        started_at = perf_counter()

        try:
            response = httpx.get(
                (f"{self.prometheus_url}/-/ready"),
                timeout=2.0,
            )

            if response.status_code != 200:
                return ComponentHealth(
                    status="unhealthy",
                    detail=(f"Prometheus readiness returned HTTP {response.status_code}."),
                    latency_ms=self._elapsed_ms(started_at),
                )

            return ComponentHealth(
                status="healthy",
                detail="Prometheus is ready.",
                latency_ms=self._elapsed_ms(started_at),
            )

        except httpx.HTTPError as exc:
            return ComponentHealth(
                status="unhealthy",
                detail=(f"Prometheus unavailable: {type(exc).__name__}"),
                latency_ms=self._elapsed_ms(started_at),
            )

    def check_kafka_consumer(
        self,
    ) -> ComponentHealth:
        """Check whether Prometheus can scrape the consumer."""

        started_at = perf_counter()

        try:
            response = httpx.get(
                (f"{self.prometheus_url}/api/v1/query"),
                params={"query": ('up{job="gridpulse-kafka-consumer"}')},
                timeout=2.0,
            )

            response.raise_for_status()

            payload: dict[
                str,
                Any,
            ] = response.json()

            results = payload.get(
                "data",
                {},
            ).get(
                "result",
                [],
            )

            if not results:
                return ComponentHealth(
                    status="degraded",
                    detail=("No Kafka consumer scrape target is currently reporting."),
                    latency_ms=self._elapsed_ms(started_at),
                )

            values = [float(result["value"][1]) for result in results]

            if any(value == 1.0 for value in values):
                return ComponentHealth(
                    status="healthy",
                    detail=("Kafka consumer metrics target is being scraped."),
                    latency_ms=self._elapsed_ms(started_at),
                )

            return ComponentHealth(
                status="degraded",
                detail=("Kafka consumer target exists but is currently down."),
                latency_ms=self._elapsed_ms(started_at),
            )

        except (
            httpx.HTTPError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            return ComponentHealth(
                status="unhealthy",
                detail=(f"Unable to determine consumer health: {type(exc).__name__}"),
                latency_ms=self._elapsed_ms(started_at),
            )

    def snapshot(
        self,
    ) -> dict[
        str,
        ComponentHealth,
    ]:
        """Return health for all platform components."""

        return {
            "warehouse": (self.check_duckdb()),
            "kafka": (self.check_kafka()),
            "prometheus": (self.check_prometheus()),
            "kafka_consumer": (self.check_kafka_consumer()),
        }
