"""Persistent pipeline execution telemetry for GridPulse."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

DEFAULT_RUN_LOG_PATH = Path("data/observability/pipeline_runs.jsonl")

RECORD_COUNT_PATTERN = re.compile(r"GRIDPULSE_RECORDS_PROCESSED=(\d+)")


@dataclass(frozen=True)
class PipelineRun:
    """Latest known state for one pipeline execution."""

    run_id: str
    stage: str
    status: str

    started_at: datetime
    finished_at: datetime | None

    duration_seconds: float | None
    exit_code: int | None

    records_processed: int | None
    throughput_records_per_second: float | None

    command: tuple[str, ...]


def _utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def _serialize_datetime(
    value: datetime | None,
) -> str | None:
    """Serialize an optional UTC datetime."""

    if value is None:
        return None

    return value.astimezone(UTC).isoformat()


def _parse_datetime(
    value: Any,
) -> datetime | None:
    """Parse one persisted datetime."""

    if not isinstance(
        value,
        str,
    ):
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _throughput(
    records_processed: int | None,
    duration_seconds: float | None,
) -> float | None:
    """Calculate records per second when both inputs are reliable."""

    if records_processed is None or duration_seconds is None or duration_seconds <= 0:
        return None

    return round(
        records_processed / duration_seconds,
        3,
    )


def append_pipeline_run(
    run: PipelineRun,
    log_path: Path = DEFAULT_RUN_LOG_PATH,
) -> None:
    """Append one immutable pipeline run-state event."""

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "run_id": run.run_id,
        "stage": run.stage,
        "status": run.status,
        "started_at": _serialize_datetime(run.started_at),
        "finished_at": _serialize_datetime(run.finished_at),
        "duration_seconds": run.duration_seconds,
        "exit_code": run.exit_code,
        "records_processed": run.records_processed,
        "throughput_records_per_second": run.throughput_records_per_second,
        "command": list(run.command),
    }

    with log_path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                payload,
                sort_keys=True,
            )
        )

        handle.write("\n")


def _pipeline_run_from_payload(
    payload: Any,
) -> PipelineRun | None:
    """Convert one JSONL payload into a typed run."""

    if not isinstance(
        payload,
        dict,
    ):
        return None

    run_id = payload.get("run_id")

    stage = payload.get("stage")

    status = payload.get("status")

    started_at = _parse_datetime(payload.get("started_at"))

    finished_at = _parse_datetime(payload.get("finished_at"))

    command = payload.get("command")

    if (
        not isinstance(
            run_id,
            str,
        )
        or not isinstance(
            stage,
            str,
        )
        or not isinstance(
            status,
            str,
        )
        or started_at is None
        or not isinstance(
            command,
            list,
        )
        or not all(
            isinstance(
                item,
                str,
            )
            for item in command
        )
    ):
        return None

    duration_value = payload.get("duration_seconds")

    exit_code_value = payload.get("exit_code")

    records_value = payload.get("records_processed")

    throughput_value = payload.get("throughput_records_per_second")

    duration_seconds = (
        float(duration_value)
        if isinstance(
            duration_value,
            int | float,
        )
        else None
    )

    exit_code = (
        int(exit_code_value)
        if isinstance(
            exit_code_value,
            int,
        )
        else None
    )

    records_processed = (
        int(records_value)
        if isinstance(
            records_value,
            int,
        )
        else None
    )

    throughput_records_per_second = (
        float(throughput_value)
        if isinstance(
            throughput_value,
            int | float,
        )
        else _throughput(
            records_processed,
            duration_seconds,
        )
    )

    return PipelineRun(
        run_id=run_id,
        stage=stage,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        exit_code=exit_code,
        records_processed=records_processed,
        throughput_records_per_second=(throughput_records_per_second),
        command=tuple(command),
    )


def load_pipeline_runs(
    log_path: Path = DEFAULT_RUN_LOG_PATH,
    limit: int = 50,
) -> list[PipelineRun]:
    """Return latest known state for recent pipeline runs."""

    if not log_path.exists():
        return []

    latest_by_run: dict[
        str,
        PipelineRun,
    ] = {}

    with log_path.open(
        encoding="utf-8",
    ) as handle:
        for line in handle:
            stripped = line.strip()

            if not stripped:
                continue

            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue

            run = _pipeline_run_from_payload(payload)

            if run is None:
                continue

            latest_by_run[run.run_id] = run

    runs = sorted(
        latest_by_run.values(),
        key=lambda run: run.started_at,
        reverse=True,
    )

    return runs[:limit]


def last_successful_run(
    runs: Sequence[PipelineRun],
    stage: str | None = None,
) -> PipelineRun | None:
    """Return latest successful run, optionally for one stage."""

    successful = [
        run for run in runs if (run.status == "SUCCEEDED" and (stage is None or run.stage == stage))
    ]

    if not successful:
        return None

    return max(
        successful,
        key=lambda run: run.finished_at or run.started_at,
    )


def _extract_records_processed(
    line: str,
) -> int | None:
    """Read one structured record-count marker from process output."""

    match = RECORD_COUNT_PATTERN.search(line)

    if match is None:
        return None

    return int(match.group(1))


def execute_pipeline_command(
    *,
    stage: str,
    command: Sequence[str],
    log_path: Path = DEFAULT_RUN_LOG_PATH,
) -> int:
    """Execute one command and record its real runtime state."""

    if not command:
        raise ValueError("Pipeline command cannot be empty.")

    run_id = str(uuid.uuid4())

    started_at = _utc_now()

    append_pipeline_run(
        PipelineRun(
            run_id=run_id,
            stage=stage,
            status="STARTED",
            started_at=started_at,
            finished_at=None,
            duration_seconds=None,
            exit_code=None,
            records_processed=None,
            throughput_records_per_second=None,
            command=tuple(command),
        ),
        log_path,
    )

    timer = perf_counter()

    records_processed: int | None = None

    try:
        process = subprocess.Popen(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        if process.stdout is None:
            raise RuntimeError("Pipeline process stdout unavailable.")

        for line in process.stdout:
            print(
                line,
                end="",
                flush=True,
            )

            detected_count = _extract_records_processed(line)

            if detected_count is not None:
                records_processed = detected_count

        exit_code = process.wait()

    except KeyboardInterrupt:
        exit_code = 130

    except Exception:
        exit_code = 1

    finished_at = _utc_now()

    duration_seconds = round(
        perf_counter() - timer,
        3,
    )

    status = "SUCCEEDED" if exit_code == 0 else "FAILED"

    throughput = _throughput(
        records_processed,
        duration_seconds,
    )

    append_pipeline_run(
        PipelineRun(
            run_id=run_id,
            stage=stage,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            exit_code=exit_code,
            records_processed=records_processed,
            throughput_records_per_second=(throughput),
            command=tuple(command),
        ),
        log_path,
    )

    return exit_code


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""

    parser = argparse.ArgumentParser(
        description=("Run a GridPulse pipeline command with execution telemetry.")
    )

    parser.add_argument(
        "--stage",
        required=True,
        help=("Pipeline stage identifier, for example bronze_to_silver."),
    )

    parser.add_argument(
        "--log-path",
        type=Path,
        default=DEFAULT_RUN_LOG_PATH,
    )

    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help=("Command to execute. Prefix the command with --."),
    )

    return parser


def main() -> None:
    """Run telemetry wrapper CLI."""

    parser = _build_parser()

    args = parser.parse_args()

    command: list[str] = args.command

    if command and command[0] == "--":
        command = command[1:]

    if not command:
        parser.error("A command must be supplied after --.")

    exit_code = execute_pipeline_command(
        stage=args.stage,
        command=command,
        log_path=args.log_path,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
