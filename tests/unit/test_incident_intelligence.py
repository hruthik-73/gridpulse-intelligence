"""Tests for GridPulse operational incident intelligence."""

from gridpulse_intelligence.incident_intelligence import (
    ComponentState,
    build_operational_incidents,
    highest_operational_severity,
)
from gridpulse_intelligence.source_freshness import (
    SourceFreshnessSignal,
)


def freshness_signal(
    *,
    source: str = "eia",
    state: str = "FRESH",
    age_hours: float | None = 2.0,
) -> SourceFreshnessSignal:
    """Create a source freshness fixture."""

    return SourceFreshnessSignal(
        source=source,
        display_name=source.upper(),
        dataset="test dataset",
        state=state,
        latest_timestamp=None,
        age_hours=age_hours,
        timestamp_basis="Kafka event timestamp",
        fresh_within_hours=6.0,
        stale_after_hours=24.0,
    )


def test_healthy_platform_has_no_incidents() -> None:
    """Fresh sources and healthy dependencies should be incident-free."""

    incidents = build_operational_incidents(
        freshness=[freshness_signal()],
        components=[
            ComponentState(
                name="kafka",
                status="healthy",
                detail="Kafka reachable.",
                latency_ms=4.0,
            )
        ],
    )

    assert incidents == []

    assert highest_operational_severity(incidents) == "NORMAL"


def test_stale_source_creates_high_incident() -> None:
    """A stale source should become a high operational incident."""

    incidents = build_operational_incidents(
        freshness=[
            freshness_signal(
                state="STALE",
                age_hours=30.0,
            )
        ],
        components=[],
    )

    assert len(incidents) == 1

    assert incidents[0].severity == "HIGH"

    assert incidents[0].category == "DATA_FRESHNESS"


def test_delayed_source_is_elevated() -> None:
    """Delayed data should be visible without claiming outage."""

    incidents = build_operational_incidents(
        freshness=[
            freshness_signal(
                state="DELAYED",
                age_hours=10.0,
            )
        ],
        components=[],
    )

    assert incidents[0].severity == "ELEVATED"


def test_unhealthy_runtime_is_critical() -> None:
    """An unhealthy runtime dependency should be critical."""

    incidents = build_operational_incidents(
        freshness=[],
        components=[
            ComponentState(
                name="kafka_consumer",
                status="unhealthy",
                detail="Consumer metrics unavailable.",
                latency_ms=2500.0,
            )
        ],
    )

    assert incidents[0].severity == "CRITICAL"


def test_critical_incident_ranks_first() -> None:
    """Incident ordering should prioritize operational severity."""

    incidents = build_operational_incidents(
        freshness=[
            freshness_signal(
                state="STALE",
                age_hours=48.0,
            )
        ],
        components=[
            ComponentState(
                name="prometheus",
                status="unhealthy",
                detail="Prometheus unavailable.",
                latency_ms=1000.0,
            )
        ],
    )

    assert incidents[0].severity == "CRITICAL"

    assert highest_operational_severity(incidents) == "CRITICAL"
