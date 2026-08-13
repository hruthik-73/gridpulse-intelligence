"""Tests for GridPulse pipeline lineage intelligence."""

from datetime import UTC, datetime, timedelta

from gridpulse_intelligence.incident_intelligence import (
    ComponentState,
)
from gridpulse_intelligence.pipeline_lineage import (
    build_pipeline_lineage,
)
from gridpulse_intelligence.pipeline_runs import (
    PipelineRun,
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
        timestamp_basis=("Kafka event timestamp"),
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


def pipeline_run(
    *,
    stage: str,
    status: str = "SUCCEEDED",
    run_id: str = "run-1",
    hour: int = 10,
    duration: float | None = 15.0,
) -> PipelineRun:
    """Create real-run telemetry fixture."""

    started_at = datetime(
        2026,
        8,
        13,
        hour,
        tzinfo=UTC,
    )

    finished_at = (
        datetime(
            2026,
            8,
            13,
            hour,
            1,
            tzinfo=UTC,
        )
        if status != "STARTED"
        else None
    )

    return PipelineRun(
        run_id=run_id,
        stage=stage,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=(duration if status != "STARTED" else None),
        exit_code=(0 if status == "SUCCEEDED" else (1 if status == "FAILED" else None)),
        records_processed=None,
        command=("test",),
    )


def base_freshness() -> list[SourceFreshnessSignal]:
    """Create healthy source fixtures."""

    return [
        freshness("eia"),
        freshness("nws"),
        freshness("afdc"),
    ]


def test_lineage_contains_expected_nodes() -> None:
    """Lineage should contain the full GridPulse path."""

    nodes, edges = build_pipeline_lineage(
        freshness=base_freshness(),
        components=healthy_components(),
        incidents=[],
        runs=[],
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
    """A stale source should be unhealthy in lineage."""

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
        runs=[],
    )

    eia = next(node for node in nodes if node.node_id == "source-eia")

    assert eia.state == "UNHEALTHY"


def test_successful_stage_run_is_visible() -> None:
    """Actual successful execution should drive its lineage node."""

    nodes, _ = build_pipeline_lineage(
        freshness=base_freshness(),
        components=healthy_components(),
        incidents=[],
        runs=[pipeline_run(stage=("bronze_to_silver"))],
    )

    silver = next(node for node in nodes if node.node_id == "spark-silver")

    assert silver.latest_run_status == "SUCCEEDED"

    assert silver.state == "HEALTHY"

    assert silver.recent_runs == 1

    assert silver.recent_failures == 0


def test_failed_stage_run_is_unhealthy() -> None:
    """Latest failed execution should make the stage unhealthy."""

    nodes, _ = build_pipeline_lineage(
        freshness=base_freshness(),
        components=healthy_components(),
        incidents=[],
        runs=[
            pipeline_run(
                stage="build_gold",
                status="FAILED",
            )
        ],
    )

    gold = next(node for node in nodes if node.node_id == "spark-gold")

    assert gold.latest_run_status == "FAILED"

    assert gold.state == "UNHEALTHY"

    assert gold.recent_failures == 1


def test_latest_stage_execution_wins() -> None:
    """Latest execution state should represent current stage evidence."""

    nodes, _ = build_pipeline_lineage(
        freshness=base_freshness(),
        components=healthy_components(),
        incidents=[],
        runs=[
            pipeline_run(
                stage="build_gold",
                status="FAILED",
                run_id="old-failure",
                hour=9,
            ),
            pipeline_run(
                stage="build_gold",
                status="SUCCEEDED",
                run_id="new-success",
                hour=11,
            ),
        ],
    )

    gold = next(node for node in nodes if node.node_id == "spark-gold")

    assert gold.latest_run_status == "SUCCEEDED"

    assert gold.state == "HEALTHY"

    assert gold.recent_runs == 2

    assert gold.recent_failures == 1


def test_uninstrumented_stage_is_unknown() -> None:
    """A stage with no run telemetry should not claim execution health."""

    nodes, _ = build_pipeline_lineage(
        freshness=base_freshness(),
        components=healthy_components(),
        incidents=[],
        runs=[],
    )

    bronze = next(node for node in nodes if node.node_id == "spark-bronze")

    assert bronze.state == "UNKNOWN"

    assert bronze.latest_run_status is None


def test_warehouse_runtime_state_is_visible() -> None:
    """Warehouse health should remain runtime-derived."""

    components = healthy_components()

    components[2] = ComponentState(
        name="warehouse",
        status="unhealthy",
        detail=("Warehouse unavailable."),
        latency_ms=2000.0,
    )

    nodes, _ = build_pipeline_lineage(
        freshness=base_freshness(),
        components=components,
        incidents=[],
        runs=[],
    )

    by_id = {node.node_id: node for node in nodes}

    assert by_id["duckdb"].state == "UNHEALTHY"

    assert by_id["fastapi"].state == "UNHEALTHY"


def test_stalled_execution_is_unhealthy() -> None:
    """A long-running STARTED execution should become unhealthy."""

    started_at = datetime.now(UTC) - timedelta(
        hours=1,
    )

    stalled_run = PipelineRun(
        run_id="stalled-run",
        stage="kafka_to_bronze",
        status="STARTED",
        started_at=started_at,
        finished_at=None,
        duration_seconds=None,
        exit_code=None,
        records_processed=None,
        command=("test",),
    )

    nodes, _ = build_pipeline_lineage(
        freshness=base_freshness(),
        components=healthy_components(),
        incidents=[],
        runs=[stalled_run],
    )

    bronze = next(node for node in nodes if node.node_id == "spark-bronze")

    assert bronze.operational_status == "STALLED"

    assert bronze.state == "UNHEALTHY"


def test_overdue_success_is_degraded() -> None:
    """A successful stage with an old last success should be degraded."""

    started_at = datetime.now(UTC) - timedelta(
        hours=30,
    )

    old_success = PipelineRun(
        run_id="old-success",
        stage="build_gold",
        status="SUCCEEDED",
        started_at=started_at,
        finished_at=(
            started_at
            + timedelta(
                seconds=30,
            )
        ),
        duration_seconds=30.0,
        exit_code=0,
        records_processed=None,
        command=("test",),
    )

    nodes, _ = build_pipeline_lineage(
        freshness=base_freshness(),
        components=healthy_components(),
        incidents=[],
        runs=[old_success],
    )

    gold = next(node for node in nodes if node.node_id == "spark-gold")

    assert gold.operational_status == "OVERDUE"

    assert gold.state == "DEGRADED"
