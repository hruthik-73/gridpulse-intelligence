"""Pipeline lineage intelligence for GridPulse."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from gridpulse_intelligence.incident_intelligence import (
    ComponentState,
    OperationalIncident,
)
from gridpulse_intelligence.pipeline_runs import (
    PipelineRun,
)
from gridpulse_intelligence.source_freshness import (
    SourceFreshnessSignal,
)

STATE_RANK = {
    "UNKNOWN": 0,
    "HEALTHY": 1,
    "DEGRADED": 2,
    "UNHEALTHY": 3,
}


@dataclass(frozen=True)
class PipelineStageTelemetry:
    """Execution telemetry summarized for one pipeline stage."""

    stage: str

    latest_status: str | None

    latest_started_at: datetime | None
    latest_finished_at: datetime | None

    latest_duration_seconds: float | None

    last_success_at: datetime | None

    recent_runs: int
    recent_failures: int


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

    run_stage: str | None

    latest_run_status: str | None

    latest_run_started_at: datetime | None
    latest_run_finished_at: datetime | None

    latest_run_duration_seconds: float | None

    last_success_at: datetime | None

    recent_runs: int
    recent_failures: int


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
    """Return the most severe materialized state."""

    materialized = list(states)

    if not materialized:
        return "UNKNOWN"

    return max(
        materialized,
        key=lambda state: STATE_RANK.get(
            state,
            0,
        ),
    )


def _stage_telemetry(
    runs: Iterable[PipelineRun],
    stage: str,
) -> PipelineStageTelemetry:
    """Summarize actual execution history for one pipeline stage."""

    stage_runs = sorted(
        (run for run in runs if run.stage == stage),
        key=lambda run: run.started_at,
        reverse=True,
    )

    if not stage_runs:
        return PipelineStageTelemetry(
            stage=stage,
            latest_status=None,
            latest_started_at=None,
            latest_finished_at=None,
            latest_duration_seconds=None,
            last_success_at=None,
            recent_runs=0,
            recent_failures=0,
        )

    latest = stage_runs[0]

    successful_runs = [run for run in stage_runs if run.status == "SUCCEEDED"]

    last_success = (
        max(
            successful_runs,
            key=lambda run: run.finished_at or run.started_at,
        )
        if successful_runs
        else None
    )

    return PipelineStageTelemetry(
        stage=stage,
        latest_status=latest.status,
        latest_started_at=(latest.started_at),
        latest_finished_at=(latest.finished_at),
        latest_duration_seconds=(latest.duration_seconds),
        last_success_at=(
            (last_success.finished_at or last_success.started_at) if last_success else None
        ),
        recent_runs=len(stage_runs),
        recent_failures=sum(run.status == "FAILED" for run in stage_runs),
    )


def _stage_state(
    telemetry: PipelineStageTelemetry,
    dependency_state: str,
) -> str:
    """Represent verified execution health independently of upstream state."""

    # Dependency health remains visible on its own lineage nodes
    # and through Operational Incident Intelligence.
    # A successful stage execution should therefore remain healthy.
    del dependency_state

    if telemetry.latest_status is None:
        return "UNKNOWN"

    if telemetry.latest_status == "FAILED":
        return "UNHEALTHY"

    if telemetry.latest_status in {
        "STARTED",
        "SUCCEEDED",
    }:
        return "HEALTHY"

    return "UNKNOWN"


def _incident_suffix(
    incidents_by_source: dict[
        str,
        list[OperationalIncident],
    ],
    source: str,
) -> str:
    """Return concise incident evidence for one node source."""

    incidents = incidents_by_source.get(
        source,
        [],
    )

    if not incidents:
        return ""

    top_incident = incidents[0]

    return f" Active incident: {top_incident.title}."


def build_pipeline_lineage(
    freshness: Iterable[SourceFreshnessSignal],
    components: Iterable[ComponentState],
    incidents: Iterable[OperationalIncident],
    runs: Iterable[PipelineRun] = (),
) -> tuple[
    list[PipelineLineageNode],
    list[PipelineLineageEdge],
]:
    """Build current GridPulse lineage intelligence."""

    freshness_list = list(freshness)

    run_list = list(runs)

    freshness_by_source = {signal.source: signal for signal in freshness_list}

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

    for source_incidents in incidents_by_source.values():
        source_incidents.sort(
            key=lambda incident: (
                -{
                    "CRITICAL": 4,
                    "HIGH": 3,
                    "ELEVATED": 2,
                    "NORMAL": 1,
                }.get(
                    incident.severity,
                    0,
                )
            )
        )

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

            age = f"{signal.age_hours:.1f}h old" if signal.age_hours is not None else "unknown age"

            detail = f"{signal.state} · {age} · {signal.timestamp_basis}"

        detail += _incident_suffix(
            incidents_by_source,
            source,
        )

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
            run_stage=None,
            latest_run_status=None,
            latest_run_started_at=None,
            latest_run_finished_at=None,
            latest_run_duration_seconds=None,
            last_success_at=None,
            recent_runs=0,
            recent_failures=0,
        )

    kafka_component = components_by_name.get("kafka")

    kafka_state = _runtime_state(kafka_component.status) if kafka_component else "UNKNOWN"

    kafka_detail = (
        kafka_component.detail if kafka_component else ("Kafka runtime health unavailable.")
    )

    kafka_detail += _incident_suffix(
        incidents_by_source,
        "kafka",
    )

    consumer_component = components_by_name.get("kafka_consumer")

    consumer_state = _runtime_state(consumer_component.status) if consumer_component else "UNKNOWN"

    warehouse_component = components_by_name.get("warehouse")

    warehouse_state = (
        _runtime_state(warehouse_component.status) if warehouse_component else "UNKNOWN"
    )

    warehouse_detail = (
        warehouse_component.detail if warehouse_component else ("Warehouse health unavailable.")
    )

    warehouse_detail += _incident_suffix(
        incidents_by_source,
        "warehouse",
    )

    source_states = [_freshness_state(signal.state) for signal in freshness_list]

    bronze_telemetry = _stage_telemetry(
        run_list,
        "kafka_to_bronze",
    )

    silver_telemetry = _stage_telemetry(
        run_list,
        "bronze_to_silver",
    )

    gold_telemetry = _stage_telemetry(
        run_list,
        "build_gold",
    )

    dbt_telemetry = _stage_telemetry(
        run_list,
        "dbt_build",
    )

    ingestion_dependency_state = _worst_state(
        [
            *source_states,
            kafka_state,
            consumer_state,
        ]
    )

    bronze_state = _stage_state(
        bronze_telemetry,
        ingestion_dependency_state,
    )

    silver_state = _stage_state(
        silver_telemetry,
        bronze_state,
    )

    gold_state = _stage_state(
        gold_telemetry,
        silver_state,
    )

    dbt_state = _stage_state(
        dbt_telemetry,
        _worst_state(
            [
                gold_state,
                warehouse_state,
            ]
        ),
    )

    def execution_node(
        *,
        node_id: str,
        label: str,
        layer: str,
        technology: str,
        state: str,
        detail: str,
        x: int,
        telemetry: PipelineStageTelemetry,
    ) -> PipelineLineageNode:
        return PipelineLineageNode(
            node_id=node_id,
            label=label,
            layer=layer,
            technology=technology,
            state=state,
            detail=detail,
            source=None,
            position_x=x,
            position_y=50,
            run_stage=(telemetry.stage),
            latest_run_status=(telemetry.latest_status),
            latest_run_started_at=(telemetry.latest_started_at),
            latest_run_finished_at=(telemetry.latest_finished_at),
            latest_run_duration_seconds=(telemetry.latest_duration_seconds),
            last_success_at=(telemetry.last_success_at),
            recent_runs=(telemetry.recent_runs),
            recent_failures=(telemetry.recent_failures),
        )

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
            run_stage=None,
            latest_run_status=None,
            latest_run_started_at=None,
            latest_run_finished_at=None,
            latest_run_duration_seconds=None,
            last_success_at=None,
            recent_runs=0,
            recent_failures=0,
        ),
        execution_node(
            node_id="spark-bronze",
            label="Bronze",
            layer="LAKEHOUSE",
            technology="Spark",
            state=bronze_state,
            detail=("Kafka event ingestion into replay-safe Bronze."),
            x=35,
            telemetry=bronze_telemetry,
        ),
        execution_node(
            node_id="spark-silver",
            label="Silver",
            layer="LAKEHOUSE",
            technology="Spark",
            state=silver_state,
            detail=("Validated, normalized, and deduplicated records."),
            x=48,
            telemetry=silver_telemetry,
        ),
        execution_node(
            node_id="spark-gold",
            label="Gold",
            layer="ANALYTICS",
            technology="Spark",
            state=gold_state,
            detail=("Analytics-ready energy, weather, and EV marts."),
            x=61,
            telemetry=gold_telemetry,
        ),
        execution_node(
            node_id="dbt",
            label="dbt",
            layer="MODELING",
            technology="dbt",
            state=dbt_state,
            detail=("Tested analytical models and semantic marts."),
            x=72,
            telemetry=dbt_telemetry,
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
            run_stage=None,
            latest_run_status=None,
            latest_run_started_at=None,
            latest_run_finished_at=None,
            latest_run_duration_seconds=None,
            last_success_at=None,
            recent_runs=0,
            recent_failures=0,
        ),
        PipelineLineageNode(
            node_id="fastapi",
            label="FastAPI",
            layer="SERVING",
            technology="FastAPI",
            state=warehouse_state,
            detail=("GridPulse intelligence serving layer."),
            source=None,
            position_x=91,
            position_y=35,
            run_stage=None,
            latest_run_status=None,
            latest_run_started_at=None,
            latest_run_finished_at=None,
            latest_run_duration_seconds=None,
            last_success_at=None,
            recent_runs=0,
            recent_failures=0,
        ),
        PipelineLineageNode(
            node_id="nextjs",
            label="Next.js",
            layer="EXPERIENCE",
            technology="Next.js",
            state=warehouse_state,
            detail=("Interactive operational intelligence interface."),
            source=None,
            position_x=91,
            position_y=68,
            run_stage=None,
            latest_run_status=None,
            latest_run_started_at=None,
            latest_run_finished_at=None,
            latest_run_duration_seconds=None,
            last_success_at=None,
            recent_runs=0,
            recent_failures=0,
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
