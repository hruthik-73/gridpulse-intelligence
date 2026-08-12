"""Prometheus metrics for GridPulse Intelligence."""

from time import time
from typing import Literal

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

PipelineStatus = Literal[
    "success",
    "failure",
]

_DEFAULT_METRICS: "GridPulseMetrics | None" = None


def _required_label(
    value: str,
    name: str,
) -> str:
    """Validate and normalize a Prometheus label value."""

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{name} must not be empty")

    return normalized


class GridPulseMetrics:
    """GridPulse Prometheus instrumentation."""

    def __init__(
        self,
        registry: CollectorRegistry | None = None,
    ) -> None:
        self.registry = registry if registry is not None else CollectorRegistry()

        self.pipeline_runs = Counter(
            "gridpulse_pipeline_runs",
            ("Total GridPulse pipeline runs by pipeline and status."),
            (
                "pipeline",
                "status",
            ),
            registry=self.registry,
        )

        self.pipeline_errors = Counter(
            "gridpulse_pipeline_errors",
            ("Total GridPulse pipeline errors by pipeline and error type."),
            (
                "pipeline",
                "error_type",
            ),
            registry=self.registry,
        )

        self.pipeline_duration = Histogram(
            "gridpulse_pipeline_duration_seconds",
            ("GridPulse pipeline execution duration in seconds."),
            ("pipeline",),
            registry=self.registry,
        )

        self.last_success_timestamp = Gauge(
            "gridpulse_pipeline_last_success_timestamp_seconds",
            ("Unix timestamp of the most recent successful pipeline run."),
            ("pipeline",),
            registry=self.registry,
        )

        self.source_records = Gauge(
            "gridpulse_source_records",
            ("Current observed record count by source and data layer."),
            (
                "source",
                "layer",
            ),
            registry=self.registry,
        )

        self.kafka_messages = Counter(
            "gridpulse_kafka_messages",
            ("Total Kafka messages handled by source and outcome."),
            (
                "source",
                "outcome",
            ),
            registry=self.registry,
        )

        self.api_requests = Counter(
            "gridpulse_api_requests",
            ("Total HTTP requests handled by method, route, and status."),
            (
                "method",
                "route",
                "status",
            ),
            registry=self.registry,
        )

        self.api_request_duration = Histogram(
            "gridpulse_api_request_duration_seconds",
            ("GridPulse API request duration in seconds."),
            (
                "method",
                "route",
            ),
            registry=self.registry,
        )

    def observe_pipeline_run(
        self,
        *,
        pipeline: str,
        status: PipelineStatus,
        duration_seconds: float,
        error_type: str | None = None,
        completed_at: float | None = None,
    ) -> None:
        """Record one completed pipeline execution."""

        normalized_pipeline = _required_label(
            pipeline,
            "pipeline",
        )

        if duration_seconds < 0:
            raise ValueError("duration_seconds must not be negative")

        self.pipeline_runs.labels(
            pipeline=normalized_pipeline,
            status=status,
        ).inc()

        self.pipeline_duration.labels(
            pipeline=normalized_pipeline,
        ).observe(duration_seconds)

        if status == "success":
            success_time = completed_at if completed_at is not None else time()

            self.last_success_timestamp.labels(
                pipeline=normalized_pipeline,
            ).set(success_time)

            return

        normalized_error = _required_label(
            error_type or "unknown",
            "error_type",
        )

        self.pipeline_errors.labels(
            pipeline=normalized_pipeline,
            error_type=normalized_error,
        ).inc()

    def set_source_records(
        self,
        *,
        source: str,
        layer: str,
        count: int,
    ) -> None:
        """Set the current record count for one data layer."""

        if count < 0:
            raise ValueError("count must not be negative")

        normalized_source = _required_label(
            source,
            "source",
        )

        normalized_layer = _required_label(
            layer,
            "layer",
        )

        self.source_records.labels(
            source=normalized_source,
            layer=normalized_layer,
        ).set(count)

    def record_kafka_message(
        self,
        *,
        source: str,
        outcome: str,
    ) -> None:
        """Record one Kafka processing outcome."""

        normalized_source = _required_label(
            source,
            "source",
        )

        normalized_outcome = _required_label(
            outcome,
            "outcome",
        )

        self.kafka_messages.labels(
            source=normalized_source,
            outcome=normalized_outcome,
        ).inc()

    def record_api_request(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record one completed API request."""

        if duration_seconds < 0:
            raise ValueError("duration_seconds must not be negative")

        if status_code < 100 or status_code > 599:
            raise ValueError("status_code must be between 100 and 599")

        normalized_method = _required_label(
            method,
            "method",
        ).upper()

        normalized_route = _required_label(
            route,
            "route",
        )

        status = str(status_code)

        self.api_requests.labels(
            method=normalized_method,
            route=normalized_route,
            status=status,
        ).inc()

        self.api_request_duration.labels(
            method=normalized_method,
            route=normalized_route,
        ).observe(duration_seconds)

    def render(self) -> bytes:
        """Render this registry in Prometheus exposition format."""

        return generate_latest(self.registry)


def get_metrics() -> GridPulseMetrics:
    """Return process-wide GridPulse metrics."""

    global _DEFAULT_METRICS

    if _DEFAULT_METRICS is None:
        _DEFAULT_METRICS = GridPulseMetrics(registry=REGISTRY)

    return _DEFAULT_METRICS
