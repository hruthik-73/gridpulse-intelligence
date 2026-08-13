"""Tests for GridPulse pipeline SLA intelligence."""

from datetime import UTC, datetime, timedelta

from gridpulse_intelligence.pipeline_runs import PipelineRun
from gridpulse_intelligence.pipeline_sla import (
    PIPELINE_SLA_RULES,
    evaluate_pipeline_sla,
)

NOW = datetime(
    2026,
    8,
    13,
    16,
    0,
    tzinfo=UTC,
)


def rule(
    stage: str = "kafka_to_bronze",
):
    """Return one configured SLA rule."""

    return next(item for item in PIPELINE_SLA_RULES if item.stage == stage)


def pipeline_run(
    *,
    status: str,
    started_at: datetime,
    duration: float | None = None,
    run_id: str = "run-1",
    stage: str = "kafka_to_bronze",
) -> PipelineRun:
    """Create pipeline telemetry fixture."""

    finished_at = (
        started_at
        + timedelta(
            seconds=duration or 0,
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
        duration_seconds=duration,
        exit_code=(0 if status == "SUCCEEDED" else (1 if status == "FAILED" else None)),
        records_processed=None,
        throughput_records_per_second=None,
        command=("test",),
    )


def test_no_run_data() -> None:
    """Uninstrumented stages should not claim health."""

    signal = evaluate_pipeline_sla(
        [],
        rule(),
        now=NOW,
    )

    assert signal.status == "NO_RUN_DATA"

    assert signal.recent_runs == 0


def test_recent_started_run_is_running() -> None:
    """A recent STARTED run should remain RUNNING."""

    signal = evaluate_pipeline_sla(
        [
            pipeline_run(
                status="STARTED",
                started_at=(
                    NOW
                    - timedelta(
                        seconds=30,
                    )
                ),
            )
        ],
        rule(),
        now=NOW,
    )

    assert signal.status == "RUNNING"


def test_old_started_run_is_stalled() -> None:
    """A STARTED run beyond runtime SLA should be STALLED."""

    signal = evaluate_pipeline_sla(
        [
            pipeline_run(
                status="STARTED",
                started_at=(
                    NOW
                    - timedelta(
                        minutes=20,
                    )
                ),
            )
        ],
        rule(),
        now=NOW,
    )

    assert signal.status == "STALLED"


def test_latest_failure_is_failed() -> None:
    """Latest failed execution should surface immediately."""

    signal = evaluate_pipeline_sla(
        [
            pipeline_run(
                status="FAILED",
                started_at=(
                    NOW
                    - timedelta(
                        minutes=5,
                    )
                ),
                duration=15.0,
            )
        ],
        rule(),
        now=NOW,
    )

    assert signal.status == "FAILED"

    assert signal.recent_failures == 1


def test_recent_success_is_succeeded() -> None:
    """Recent successful execution should satisfy SLA."""

    signal = evaluate_pipeline_sla(
        [
            pipeline_run(
                status="SUCCEEDED",
                started_at=(
                    NOW
                    - timedelta(
                        minutes=10,
                    )
                ),
                duration=20.0,
            )
        ],
        rule(),
        now=NOW,
    )

    assert signal.status == "SUCCEEDED"


def test_old_success_is_overdue() -> None:
    """Old success beyond freshness SLA should be OVERDUE."""

    signal = evaluate_pipeline_sla(
        [
            pipeline_run(
                status="SUCCEEDED",
                started_at=(
                    NOW
                    - timedelta(
                        hours=30,
                    )
                ),
                duration=20.0,
            )
        ],
        rule(),
        now=NOW,
    )

    assert signal.status == "OVERDUE"


def test_runtime_threshold_learns_from_history() -> None:
    """Enough successful history should produce an observed threshold."""

    runs = [
        pipeline_run(
            status="SUCCEEDED",
            started_at=(
                NOW
                - timedelta(
                    hours=index + 1,
                )
            ),
            duration=duration,
            run_id=(f"run-{index}"),
        )
        for index, duration in enumerate(
            [
                120.0,
                150.0,
                180.0,
            ]
        )
    ]

    signal = evaluate_pipeline_sla(
        runs,
        rule(),
        now=NOW,
    )

    assert signal.runtime_threshold_basis == "observed_median_x4"

    assert signal.expected_max_runtime_seconds == 600.0
