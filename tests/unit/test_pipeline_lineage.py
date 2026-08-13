"""Tests for GridPulse pipeline lineage intelligence."""

from gridpulse_intelligence.incident_intelligence import (
    ComponentState,
)
from gridpulse_intelligence.pipeline_lineage import (
    build_pipeline_lineage,
)
from gridpulse_intelligence.source_freshness import (
    SourceFreshnessSignal,
)


def freshness(
    source: str,
    state: str = "FRESH",
) -> SourceFreshnessSignal:
    """Create freshness fixture."""

    return SourceFreshnessSignal(
        source=source,
        display_name=source.upper(),
        dataset="test",
        state=state,
        latest_timestamp=None,
        age_hours=2.0,
        timestamp_basis="Kafka event timestamp",
        fresh_within_hours=6.0,
        stale_after_hours=24.0,
    )


def healthy_components() -> list[ComponentState]:
    """Create healthy runtime fixtures."""

    return [
        ComponentState(
            name="kafka",
            status="healthy",
            detail="Kafka reachable.",
            latency_ms=2.0,
        ),
        ComponentState(
            name="kafka_consumer",
            status="healthy",
            detail="Consumer active.",
            latency_ms=3.0,
        ),
        ComponentState(
            name="warehouse",
            status="healthy",
            detail="DuckDB reachable.",
            latency_ms=1.0,
        ),
    ]


def test_lineage_contains_expected_nodes() -> None:
    """Lineage should contain the full GridPulse path."""

    nodes, edges = build_pipeline_lineage(
        freshness=[
            freshness("eia"),
            freshness("nws"),
            freshness("afdc"),
        ],
        components=healthy_components(),
        incidents=[],
    )

    node_ids = {node.node_id for node in nodes}

    assert {
        "source-eia",
        "source-nws",
        "source-afdc",
        "kafka",
        "spark-bronze",
        "spark-silver",
        "spark-gold",
        "dbt",
        "duckdb",
        "fastapi",
        "nextjs",
    }.issubset(node_ids)

    assert len(edges) == 10


def test_stale_source_is_unhealthy() -> None:
    """A stale source should be unhealthy in the lineage."""

    nodes, _ = build_pipeline_lineage(
        freshness=[
            freshness(
                "eia",
                "STALE",
            ),
            freshness("nws"),
            freshness("afdc"),
        ],
        components=healthy_components(),
        incidents=[],
    )

    eia = next(node for node in nodes if node.node_id == "source-eia")

    assert eia.state == "UNHEALTHY"


def test_kafka_runtime_state_is_visible() -> None:
    """Kafka health should directly drive the Kafka node."""

    components = healthy_components()

    components[0] = ComponentState(
        name="kafka",
        status="degraded",
        detail="Kafka latency elevated.",
        latency_ms=500.0,
    )

    nodes, _ = build_pipeline_lineage(
        freshness=[
            freshness("eia"),
            freshness("nws"),
            freshness("afdc"),
        ],
        components=components,
        incidents=[],
    )

    kafka = next(node for node in nodes if node.node_id == "kafka")

    assert kafka.state == "DEGRADED"


def test_warehouse_drives_serving_layer() -> None:
    """Warehouse health should propagate to serving nodes."""

    components = healthy_components()

    components[2] = ComponentState(
        name="warehouse",
        status="unhealthy",
        detail="Warehouse unavailable.",
        latency_ms=2000.0,
    )

    nodes, _ = build_pipeline_lineage(
        freshness=[
            freshness("eia"),
            freshness("nws"),
            freshness("afdc"),
        ],
        components=components,
        incidents=[],
    )

    by_id = {node.node_id: node for node in nodes}

    assert by_id["duckdb"].state == "UNHEALTHY"

    assert by_id["fastapi"].state == "UNHEALTHY"

    assert by_id["nextjs"].state == "UNHEALTHY"
