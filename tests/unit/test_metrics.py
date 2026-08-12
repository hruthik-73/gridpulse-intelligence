"""Tests for GridPulse Prometheus instrumentation."""

from prometheus_client import (
    CollectorRegistry,
)

from gridpulse_intelligence.metrics import (
    GridPulseMetrics,
)


def test_successful_pipeline_run_is_recorded() -> None:
    """Successful pipeline runs should update run metrics."""

    registry = CollectorRegistry()

    metrics = GridPulseMetrics(registry=registry)

    metrics.observe_pipeline_run(
        pipeline="bronze_to_silver",
        status="success",
        duration_seconds=12.5,
        completed_at=1234.5,
    )

    assert (
        registry.get_sample_value(
            "gridpulse_pipeline_runs_total",
            {
                "pipeline": "bronze_to_silver",
                "status": "success",
            },
        )
        == 1.0
    )

    assert (
        registry.get_sample_value(
            ("gridpulse_pipeline_duration_seconds_count"),
            {
                "pipeline": "bronze_to_silver",
            },
        )
        == 1.0
    )

    assert (
        registry.get_sample_value(
            ("gridpulse_pipeline_duration_seconds_sum"),
            {
                "pipeline": "bronze_to_silver",
            },
        )
        == 12.5
    )

    assert (
        registry.get_sample_value(
            ("gridpulse_pipeline_last_success_timestamp_seconds"),
            {
                "pipeline": "bronze_to_silver",
            },
        )
        == 1234.5
    )


def test_failed_pipeline_run_records_error() -> None:
    """Failures should increment run and error counters."""

    registry = CollectorRegistry()

    metrics = GridPulseMetrics(registry=registry)

    metrics.observe_pipeline_run(
        pipeline="build_gold",
        status="failure",
        duration_seconds=4.0,
        error_type="RuntimeError",
    )

    assert (
        registry.get_sample_value(
            "gridpulse_pipeline_runs_total",
            {
                "pipeline": "build_gold",
                "status": "failure",
            },
        )
        == 1.0
    )

    assert (
        registry.get_sample_value(
            "gridpulse_pipeline_errors_total",
            {
                "pipeline": "build_gold",
                "error_type": "RuntimeError",
            },
        )
        == 1.0
    )


def test_source_record_gauge_is_updated() -> None:
    """Source record counts should be represented as gauges."""

    registry = CollectorRegistry()

    metrics = GridPulseMetrics(registry=registry)

    metrics.set_source_records(
        source="eia",
        layer="gold",
        count=58,
    )

    assert (
        registry.get_sample_value(
            "gridpulse_source_records",
            {
                "source": "eia",
                "layer": "gold",
            },
        )
        == 58.0
    )


def test_kafka_processing_outcome_is_recorded() -> None:
    """Kafka processing results should increment counters."""

    registry = CollectorRegistry()

    metrics = GridPulseMetrics(registry=registry)

    metrics.record_kafka_message(
        source="nws",
        outcome="processed",
    )

    metrics.record_kafka_message(
        source="nws",
        outcome="processed",
    )

    assert (
        registry.get_sample_value(
            "gridpulse_kafka_messages_total",
            {
                "source": "nws",
                "outcome": "processed",
            },
        )
        == 2.0
    )


def test_metrics_can_be_rendered() -> None:
    """Registry should render valid Prometheus exposition."""

    registry = CollectorRegistry()

    metrics = GridPulseMetrics(registry=registry)

    metrics.set_source_records(
        source="afdc",
        layer="silver",
        count=5,
    )

    rendered = metrics.render().decode("utf-8")

    assert "gridpulse_source_records" in rendered

    assert 'source="afdc"' in rendered
    assert 'layer="silver"' in rendered
