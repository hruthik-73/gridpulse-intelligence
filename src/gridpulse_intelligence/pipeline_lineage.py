"""Pipeline lineage intelligence for GridPulse."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from gridpulse_intelligence.incident_intelligence import (
    ComponentState,
    OperationalIncident,
)
from gridpulse_intelligence.source_freshness import (
    SourceFreshnessSignal,
)


@dataclass(frozen=True)
class PipelineLineageNode:
    """One GridPulse pipeline node."""

    node_id: str

    label: str
    layer: str

    technology: str

    state: str

    detail: str

    source: str | None

    position_x: int
    position_y: int


@dataclass(frozen=True)
class PipelineLineageEdge:
    """Directed relationship between two pipeline nodes."""

    edge_id: str

    source_node: str
    target_node: str

    label: str


def _freshness_state(
    freshness_state: str,
) -> str:
    """Convert source freshness into lineage health."""

    if freshness_state == "FRESH":
        return "HEALTHY"

    if freshness_state == "DELAYED":
        return "DEGRADED"

    if freshness_state == "STALE":
        return "UNHEALTHY"

    return "UNKNOWN"


def _runtime_state(
    component_status: str,
) -> str:
    """Normalize platform component state."""

    normalized = component_status.strip().lower()

    if normalized == "healthy":
        return "HEALTHY"

    if normalized == "degraded":
        return "DEGRADED"

    if normalized == "unhealthy":
        return "UNHEALTHY"

    return "UNKNOWN"


def _worst_state(
    states: Iterable[str],
) -> str:
    """Return the most severe state."""

    rank = {
        "UNKNOWN": 0,
        "HEALTHY": 1,
        "DEGRADED": 2,
        "UNHEALTHY": 3,
    }

    materialized = list(states)

    if not materialized:
        return "UNKNOWN"

    return max(
        materialized,
        key=lambda state: rank.get(
            state,
            0,
        ),
    )


def build_pipeline_lineage(
    freshness: Iterable[SourceFreshnessSignal],
    components: Iterable[ComponentState],
    incidents: Iterable[OperationalIncident],
) -> tuple[
    list[PipelineLineageNode],
    list[PipelineLineageEdge],
]:
    """Build current GridPulse lineage intelligence."""

    freshness_by_source = {signal.source: signal for signal in freshness}

    components_by_name = {component.name: component for component in components}

    incidents_by_source: dict[
        str,
        list[OperationalIncident],
    ] = {}

    for incident in incidents:
        incidents_by_source.setdefault(
            incident.source,
            [],
        ).append(incident)

    def source_node(
        *,
        node_id: str,
        label: str,
        source: str,
        y: int,
    ) -> PipelineLineageNode:
        signal = freshness_by_source.get(source)

        if signal is None:
            state = "UNKNOWN"
            detail = "Freshness signal unavailable."

        else:
            state = _freshness_state(signal.state)

            if signal.age_hours is None:
                age = "unknown age"

            else:
                age = f"{signal.age_hours:.1f}h old"

            detail = f"{signal.state} · {age} · {signal.timestamp_basis}"

        return PipelineLineageNode(
            node_id=node_id,
            label=label,
            layer="SOURCE",
            technology="Public API",
            state=state,
            detail=detail,
            source=source,
            position_x=5,
            position_y=y,
        )

    kafka_component = components_by_name.get("kafka")

    kafka_state = _runtime_state(kafka_component.status) if kafka_component else "UNKNOWN"

    kafka_detail = (
        kafka_component.detail if kafka_component else "Kafka runtime health unavailable."
    )

    consumer_component = components_by_name.get("kafka_consumer")

    consumer_state = _runtime_state(consumer_component.status) if consumer_component else "UNKNOWN"

    warehouse_component = components_by_name.get("warehouse")

    warehouse_state = (
        _runtime_state(warehouse_component.status) if warehouse_component else "UNKNOWN"
    )

    warehouse_detail = (
        warehouse_component.detail if warehouse_component else "Warehouse health unavailable."
    )

    source_states = [_freshness_state(signal.state) for signal in freshness_by_source.values()]

    ingestion_state = _worst_state(
        source_states
        + [
            kafka_state,
        ]
    )

    transformation_state = _worst_state(
        [
            ingestion_state,
            consumer_state,
            warehouse_state,
        ]
    )

    serving_state = warehouse_state

    nodes = [
        source_node(
            node_id="source-eia",
            label="EIA",
            source="eia",
            y=18,
        ),
        source_node(
            node_id="source-nws",
            label="NWS",
            source="nws",
            y=50,
        ),
        source_node(
            node_id="source-afdc",
            label="AFDC",
            source="afdc",
            y=82,
        ),
        PipelineLineageNode(
            node_id="kafka",
            label="Kafka",
            layer="STREAMING",
            technology="Apache Kafka",
            state=kafka_state,
            detail=kafka_detail,
            source="kafka",
            position_x=20,
            position_y=50,
        ),
        PipelineLineageNode(
            node_id="spark-bronze",
            label="Bronze",
            layer="LAKEHOUSE",
            technology="Spark",
            state=transformation_state,
            detail=("Raw event normalization and replay-safe Bronze writes."),
            source=None,
            position_x=35,
            position_y=50,
        ),
        PipelineLineageNode(
            node_id="spark-silver",
            label="Silver",
            layer="LAKEHOUSE",
            technology="Spark",
            state=transformation_state,
            detail=("Validated and deduplicated domain records."),
            source=None,
            position_x=48,
            position_y=50,
        ),
        PipelineLineageNode(
            node_id="spark-gold",
            label="Gold",
            layer="ANALYTICS",
            technology="Spark",
            state=transformation_state,
            detail=("Analytics-ready energy, weather, and EV marts."),
            source=None,
            position_x=61,
            position_y=50,
        ),
        PipelineLineageNode(
            node_id="dbt",
            label="dbt",
            layer="MODELING",
            technology="dbt",
            state=warehouse_state,
            detail=("Tested analytical models and semantic marts."),
            source=None,
            position_x=72,
            position_y=50,
        ),
        PipelineLineageNode(
            node_id="duckdb",
            label="DuckDB",
            layer="WAREHOUSE",
            technology="DuckDB",
            state=warehouse_state,
            detail=warehouse_detail,
            source="warehouse",
            position_x=82,
            position_y=50,
        ),
        PipelineLineageNode(
            node_id="fastapi",
            label="FastAPI",
            layer="SERVING",
            technology="FastAPI",
            state=serving_state,
            detail=("GridPulse intelligence serving layer."),
            source=None,
            position_x=91,
            position_y=35,
        ),
        PipelineLineageNode(
            node_id="nextjs",
            label="Next.js",
            layer="EXPERIENCE",
            technology="Next.js",
            state=serving_state,
            detail=("Interactive operational intelligence interface."),
            source=None,
            position_x=91,
            position_y=68,
        ),
    ]

    edges = [
        PipelineLineageEdge(
            edge_id="eia-kafka",
            source_node="source-eia",
            target_node="kafka",
            label="grid events",
        ),
        PipelineLineageEdge(
            edge_id="nws-kafka",
            source_node="source-nws",
            target_node="kafka",
            label="forecast events",
        ),
        PipelineLineageEdge(
            edge_id="afdc-kafka",
            source_node="source-afdc",
            target_node="kafka",
            label="station events",
        ),
        PipelineLineageEdge(
            edge_id="kafka-bronze",
            source_node="kafka",
            target_node="spark-bronze",
            label="stream",
        ),
        PipelineLineageEdge(
            edge_id="bronze-silver",
            source_node="spark-bronze",
            target_node="spark-silver",
            label="transform",
        ),
        PipelineLineageEdge(
            edge_id="silver-gold",
            source_node="spark-silver",
            target_node="spark-gold",
            label="aggregate",
        ),
        PipelineLineageEdge(
            edge_id="gold-dbt",
            source_node="spark-gold",
            target_node="dbt",
            label="model",
        ),
        PipelineLineageEdge(
            edge_id="dbt-duckdb",
            source_node="dbt",
            target_node="duckdb",
            label="serve",
        ),
        PipelineLineageEdge(
            edge_id="duckdb-api",
            source_node="duckdb",
            target_node="fastapi",
            label="query",
        ),
        PipelineLineageEdge(
            edge_id="api-ui",
            source_node="fastapi",
            target_node="nextjs",
            label="JSON API",
        ),
    ]

    return (
        nodes,
        edges,
    )
