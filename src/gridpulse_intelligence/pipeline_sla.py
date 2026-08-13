"""Operational SLA intelligence for GridPulse pipeline executions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import median

from gridpulse_intelligence.pipeline_runs import PipelineRun


@dataclass(frozen=True)
class PipelineSlaRule:
    """GridPulse-owned operational SLA for one pipeline stage."""

    stage: str
    display_name: str

    fallback_max_runtime_seconds: float
    max_success_age_hours: float


@dataclass(frozen=True)
class PipelineSlaSignal:
    """Current operational SLA evaluation for one pipeline stage."""

    stage: str
    display_name: str

    status: str

    latest_run_status: str | None
    latest_run_id: str | None

    current_runtime_seconds: float | None
    expected_max_runtime_seconds: float
    runtime_threshold_basis: str

    last_success_at: datetime | None
    success_age_hours: float | None
    max_success_age_hours: float

    recent_runs: int
    recent_failures: int

    detail: str


PIPELINE_SLA_RULES: tuple[
    PipelineSlaRule,
    ...,
] = (
    PipelineSlaRule(
        stage="kafka_to_bronze",
        display_name="Kafka → Bronze",
        fallback_max_runtime_seconds=300.0,
        max_success_age_hours=24.0,
    ),
    PipelineSlaRule(
        stage="bronze_to_silver",
        display_name="Bronze → Silver",
        fallback_max_runtime_seconds=600.0,
        max_success_age_hours=24.0,
    ),
    PipelineSlaRule(
        stage="build_gold",
        display_name="Gold Analytics Build",
        fallback_max_runtime_seconds=600.0,
        max_success_age_hours=24.0,
    ),
    PipelineSlaRule(
        stage="dbt_build",
        display_name="dbt Analytics Build",
        fallback_max_runtime_seconds=600.0,
        max_success_age_hours=24.0,
    ),
)


def _utc_now() -> datetime:
    """Return timezone-aware UTC now."""

    return datetime.now(UTC)


def _normalized_now(
    value: datetime | None,
) -> datetime:
    """Normalize an optional evaluation timestamp."""

    if value is None:
        return _utc_now()

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def _hours_since(
    timestamp: datetime,
    now: datetime,
) -> float:
    """Return non-negative hours since timestamp."""

    return max(
        0.0,
        (now - timestamp.astimezone(UTC)).total_seconds() / 3600.0,
    )


def _expected_runtime_seconds(
    runs: list[PipelineRun],
    rule: PipelineSlaRule,
) -> tuple[
    float,
    str,
]:
    """Estimate runtime threshold from execution history when possible."""

    successful_durations = [
        run.duration_seconds
        for run in runs
        if (
            run.status == "SUCCEEDED"
            and run.duration_seconds is not None
            and run.duration_seconds > 0
        )
    ]

    if len(successful_durations) < 3:
        return (
            rule.fallback_max_runtime_seconds,
            "configured_fallback",
        )

    observed_median = median(successful_durations)

    observed_limit = observed_median * 4.0

    bounded_limit = min(
        3600.0,
        max(
            60.0,
            observed_limit,
        ),
    )

    return (
        round(
            bounded_limit,
            3,
        ),
        "observed_median_x4",
    )


def evaluate_pipeline_sla(
    runs: Iterable[PipelineRun],
    rule: PipelineSlaRule,
    *,
    now: datetime | None = None,
) -> PipelineSlaSignal:
    """Evaluate one pipeline stage against GridPulse operational SLAs."""

    evaluation_time = _normalized_now(now)

    stage_runs = sorted(
        (run for run in runs if run.stage == rule.stage),
        key=lambda run: run.started_at,
        reverse=True,
    )

    (
        expected_runtime_seconds,
        runtime_threshold_basis,
    ) = _expected_runtime_seconds(
        stage_runs,
        rule,
    )

    successful_runs = [run for run in stage_runs if run.status == "SUCCEEDED"]

    last_success = (
        max(
            successful_runs,
            key=lambda run: run.finished_at or run.started_at,
        )
        if successful_runs
        else None
    )

    last_success_at = (
        (last_success.finished_at or last_success.started_at) if last_success else None
    )

    success_age_hours = (
        round(
            _hours_since(
                last_success_at,
                evaluation_time,
            ),
            3,
        )
        if last_success_at
        else None
    )

    recent_failures = sum(run.status == "FAILED" for run in stage_runs)

    if not stage_runs:
        return PipelineSlaSignal(
            stage=rule.stage,
            display_name=rule.display_name,
            status="NO_RUN_DATA",
            latest_run_status=None,
            latest_run_id=None,
            current_runtime_seconds=None,
            expected_max_runtime_seconds=(expected_runtime_seconds),
            runtime_threshold_basis=(runtime_threshold_basis),
            last_success_at=None,
            success_age_hours=None,
            max_success_age_hours=(rule.max_success_age_hours),
            recent_runs=0,
            recent_failures=0,
            detail=("No instrumented execution has been recorded for this stage."),
        )

    latest = stage_runs[0]

    runtime_seconds: float | None

    if latest.status == "STARTED":
        runtime_seconds = max(
            0.0,
            (evaluation_time - latest.started_at.astimezone(UTC)).total_seconds(),
        )

        runtime_seconds = round(
            runtime_seconds,
            3,
        )

        if runtime_seconds > expected_runtime_seconds:
            status = "STALLED"

            detail = "Current execution exceeds the GridPulse runtime SLA."

        else:
            status = "RUNNING"

            detail = "Current execution is within the GridPulse runtime SLA."

    elif latest.status == "FAILED":
        runtime_seconds = latest.duration_seconds

        status = "FAILED"

        detail = "Latest instrumented execution failed."

    elif latest.status == "SUCCEEDED":
        runtime_seconds = latest.duration_seconds

        if success_age_hours is not None and success_age_hours > rule.max_success_age_hours:
            status = "OVERDUE"

            detail = "Latest successful execution is older than the GridPulse success-age SLA."

        else:
            status = "SUCCEEDED"

            detail = "Latest instrumented execution completed successfully."

    else:
        runtime_seconds = latest.duration_seconds

        status = "UNKNOWN"

        detail = "Latest execution state is not recognized."

    return PipelineSlaSignal(
        stage=rule.stage,
        display_name=(rule.display_name),
        status=status,
        latest_run_status=(latest.status),
        latest_run_id=(latest.run_id),
        current_runtime_seconds=(runtime_seconds),
        expected_max_runtime_seconds=(expected_runtime_seconds),
        runtime_threshold_basis=(runtime_threshold_basis),
        last_success_at=(last_success_at),
        success_age_hours=(success_age_hours),
        max_success_age_hours=(rule.max_success_age_hours),
        recent_runs=len(stage_runs),
        recent_failures=(recent_failures),
        detail=detail,
    )


def evaluate_pipeline_slas(
    runs: Iterable[PipelineRun],
    *,
    now: datetime | None = None,
) -> list[PipelineSlaSignal]:
    """Evaluate all configured GridPulse pipeline SLAs."""

    run_list = list(runs)

    return [
        evaluate_pipeline_sla(
            run_list,
            rule,
            now=now,
        )
        for rule in PIPELINE_SLA_RULES
    ]
