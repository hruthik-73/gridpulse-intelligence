"""Tests for GridPulse pipeline execution telemetry."""

from datetime import UTC, datetime
from pathlib import Path

from gridpulse_intelligence.pipeline_runs import (
    PipelineRun,
    append_pipeline_run,
    execute_pipeline_command,
    last_successful_run,
    load_pipeline_runs,
)


def test_pipeline_run_round_trip(
    tmp_path: Path,
) -> None:
    """Persisted pipeline runs should load correctly."""

    log_path = tmp_path / "runs.jsonl"

    run = PipelineRun(
        run_id="run-1",
        stage="gold",
        status="SUCCEEDED",
        started_at=datetime(
            2026,
            8,
            13,
            12,
            tzinfo=UTC,
        ),
        finished_at=datetime(
            2026,
            8,
            13,
            12,
            1,
            tzinfo=UTC,
        ),
        duration_seconds=60.0,
        exit_code=0,
        records_processed=1200,
        throughput_records_per_second=20.0,
        command=(
            "python",
            "build_gold.py",
        ),
    )

    append_pipeline_run(
        run,
        log_path,
    )

    loaded = load_pipeline_runs(log_path)

    assert loaded == [run]


def test_latest_state_wins_for_run_id(
    tmp_path: Path,
) -> None:
    """STARTED should be replaced by the run's final state."""

    log_path = tmp_path / "runs.jsonl"

    started = PipelineRun(
        run_id="run-1",
        stage="silver",
        status="STARTED",
        started_at=datetime(
            2026,
            8,
            13,
            12,
            tzinfo=UTC,
        ),
        finished_at=None,
        duration_seconds=None,
        exit_code=None,
        records_processed=None,
        throughput_records_per_second=None,
        command=(
            "python",
            "job.py",
        ),
    )

    finished = PipelineRun(
        run_id="run-1",
        stage="silver",
        status="SUCCEEDED",
        started_at=started.started_at,
        finished_at=datetime(
            2026,
            8,
            13,
            12,
            2,
            tzinfo=UTC,
        ),
        duration_seconds=120.0,
        exit_code=0,
        records_processed=None,
        throughput_records_per_second=None,
        command=started.command,
    )

    append_pipeline_run(
        started,
        log_path,
    )

    append_pipeline_run(
        finished,
        log_path,
    )

    loaded = load_pipeline_runs(log_path)

    assert len(loaded) == 1

    assert loaded[0].status == "SUCCEEDED"


def test_successful_command_is_recorded(
    tmp_path: Path,
) -> None:
    """A real successful subprocess should create run telemetry."""

    log_path = tmp_path / "runs.jsonl"

    exit_code = execute_pipeline_command(
        stage="test-stage",
        command=[
            "python",
            "-c",
            "print('ok')",
        ],
        log_path=log_path,
    )

    assert exit_code == 0

    runs = load_pipeline_runs(log_path)

    assert len(runs) == 1

    assert runs[0].status == "SUCCEEDED"

    assert runs[0].exit_code == 0

    assert runs[0].duration_seconds is not None


def test_failed_command_is_recorded(
    tmp_path: Path,
) -> None:
    """A failing subprocess should remain visible as FAILED."""

    log_path = tmp_path / "runs.jsonl"

    exit_code = execute_pipeline_command(
        stage="test-stage",
        command=[
            "python",
            "-c",
            "raise SystemExit(7)",
        ],
        log_path=log_path,
    )

    assert exit_code == 7

    run = load_pipeline_runs(log_path)[0]

    assert run.status == "FAILED"

    assert run.exit_code == 7


def test_last_successful_run() -> None:
    """Latest successful run should be selected."""

    first = PipelineRun(
        run_id="1",
        stage="gold",
        status="SUCCEEDED",
        started_at=datetime(
            2026,
            8,
            13,
            10,
            tzinfo=UTC,
        ),
        finished_at=datetime(
            2026,
            8,
            13,
            10,
            1,
            tzinfo=UTC,
        ),
        duration_seconds=60.0,
        exit_code=0,
        records_processed=None,
        throughput_records_per_second=None,
        command=("job",),
    )

    second = PipelineRun(
        run_id="2",
        stage="gold",
        status="SUCCEEDED",
        started_at=datetime(
            2026,
            8,
            13,
            11,
            tzinfo=UTC,
        ),
        finished_at=datetime(
            2026,
            8,
            13,
            11,
            1,
            tzinfo=UTC,
        ),
        duration_seconds=60.0,
        exit_code=0,
        records_processed=None,
        throughput_records_per_second=None,
        command=("job",),
    )

    assert (
        last_successful_run(
            [
                first,
                second,
            ],
            stage="gold",
        )
        == second
    )


def test_structured_record_count_creates_throughput(
    tmp_path: Path,
) -> None:
    """Structured process output should become throughput telemetry."""

    log_path = tmp_path / "runs.jsonl"

    exit_code = execute_pipeline_command(
        stage="throughput-test",
        command=[
            "python",
            "-c",
            ("print('GRIDPULSE_RECORDS_PROCESSED=1000')"),
        ],
        log_path=log_path,
    )

    assert exit_code == 0

    run = load_pipeline_runs(log_path)[0]

    assert run.records_processed == 1000

    assert run.throughput_records_per_second is not None

    assert run.throughput_records_per_second > 0
