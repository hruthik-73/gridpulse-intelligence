import {
  getPipelineRuns,
} from "@/lib/api";

import type {
  PipelineRun,
  PipelineRunStatus,
  PipelineRunSummary,
} from "@/lib/api";


function statusStyle(
  status: PipelineRunStatus,
) {
  switch (status) {
    case "SUCCEEDED":
      return {
        text:
          "text-emerald-200",
        dot:
          "bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.7)]",
      };

    case "FAILED":
      return {
        text:
          "text-rose-300",
        dot:
          "bg-rose-400 shadow-[0_0_12px_rgba(251,113,133,0.75)]",
      };

    case "STARTED":
    default:
      return {
        text:
          "text-sky-200",
        dot:
          "animate-pulse bg-sky-300 shadow-[0_0_12px_rgba(125,211,252,0.7)]",
      };
  }
}


function stageTitle(
  stage: string,
): string {
  const titles:
    Record<string, string> = {
      telemetry_smoke:
        "Telemetry Health Check",

      kafka_to_bronze:
        "Kafka → Bronze Ingestion",

      bronze_to_silver:
        "Bronze → Silver Transformation",

      build_gold:
        "Gold Analytics Build",

      dbt_build:
        "dbt Analytics Build",

      eia_ingestion:
        "EIA Grid Ingestion",

      nws_ingestion:
        "NWS Weather Ingestion",

      afdc_ingestion:
        "AFDC EV Ingestion",
    };

  return (
    titles[stage]
    ?? stage
      .replaceAll(
        "_",
        " ",
      )
      .replace(
        /\b\w/g,
        (letter) =>
          letter.toUpperCase(),
      )
  );
}


function stageDescription(
  stage: string,
): string {
  const descriptions:
    Record<string, string> = {
      telemetry_smoke:
        "Execution telemetry verification",

      kafka_to_bronze:
        "Streaming events into the Bronze layer",

      bronze_to_silver:
        "Validation, normalization, and deduplication",

      build_gold:
        "Building analytics-ready Gold marts",

      dbt_build:
        "Testing and publishing analytical models",

      eia_ingestion:
        "Electricity grid source ingestion",

      nws_ingestion:
        "Weather forecast source ingestion",

      afdc_ingestion:
        "EV infrastructure source ingestion",
    };

  return (
    descriptions[stage]
    ?? "GridPulse pipeline execution"
  );
}


function formatDuration(
  seconds:
    | number
    | null,
): string {
  if (seconds === null) {
    return "Running";
  }

  if (seconds < 1) {
    return `${Math.max(
      1,
      Math.round(
        seconds * 1000,
      ),
    )} ms`;
  }

  if (seconds < 60) {
    return `${seconds.toFixed(
      1,
    )}s`;
  }

  return `${(
    seconds / 60
  ).toFixed(1)}m`;
}


function formatThroughput(
  value:
    | number
    | null,
): string {
  if (value === null) {
    return "—";
  }

  return `${new Intl.NumberFormat(
    "en-US",
    {
      maximumFractionDigits: 1,
    },
  ).format(
    value,
  )}/sec`;
}


function formatTime(
  value:
    | string
    | null,
): string {
  if (!value) {
    return "—";
  }

  const date =
    new Date(
      value,
    );

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value;
  }

  return date.toLocaleString(
    "en-US",
    {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    },
  );
}


function RunCard({
  run,
}: {
  run: PipelineRun;
}) {
  const style =
    statusStyle(
      run.status,
    );

  return (
    <article className="rounded-xl border border-white/[0.055] bg-black/20 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`h-1.5 w-1.5 rounded-full ${style.dot}`}
            />

            <span
              className={`text-[8px] font-semibold uppercase tracking-[0.14em] ${style.text}`}
            >
              {run.status}
            </span>
          </div>

          <p className="mt-4 text-base font-medium tracking-[-0.025em] text-white/85">
            {stageTitle(
              run.stage,
            )}
          </p>

          <p className="mt-1 text-[8px] leading-4 text-white/25">
            {stageDescription(
              run.stage,
            )}
          </p>
        </div>

        <span className="rounded-md border border-white/[0.045] bg-white/[0.02] px-2 py-1 font-mono text-[7px] text-white/20">
          {run.run_id.slice(
            0,
            8,
          )}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2">
        <div className="rounded-lg border border-white/[0.045] bg-black/20 p-3">
          <p className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Duration
          </p>

          <p className="mt-2 text-sm font-medium text-white/60">
            {formatDuration(
              run.duration_seconds,
            )}
          </p>
        </div>

        <div className="rounded-lg border border-white/[0.045] bg-black/20 p-3">
          <p className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Exit code
          </p>

          <p
            className={`mt-2 text-sm font-medium ${
              run.exit_code === 0
                ? "text-emerald-200/70"
                : run.exit_code === null
                  ? "text-white/40"
                  : "text-rose-300/80"
            }`}
          >
            {run.exit_code
              ?? "—"}
          </p>
        </div>
      </div>

      <div className="mt-5 space-y-3 border-t border-white/[0.045] pt-4">
        <div className="flex items-center justify-between gap-4">
          <span className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Started
          </span>

          <span className="text-right text-[8px] text-white/40">
            {formatTime(
              run.started_at,
            )}
          </span>
        </div>

        <div className="flex items-center justify-between gap-4">
          <span className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Completed
          </span>

          <span className="text-right text-[8px] text-white/40">
            {run.status ===
            "STARTED"
              ? "In progress"
              : formatTime(
                  run.finished_at,
                )}
          </span>
        </div>

        {run.records_processed !==
          null && (
          <div className="flex items-center justify-between gap-4">
            <span className="text-[7px] uppercase tracking-[0.12em] text-white/20">
              Records processed
            </span>

            <span className="text-right text-[8px] text-white/40">
              {new Intl.NumberFormat(
                "en-US",
              ).format(
                run.records_processed,
              )}
            </span>
          </div>
        )}

        <div className="flex items-center justify-between gap-4">
          <span className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Run ID
          </span>

          <span className="font-mono text-[7px] text-white/25">
            {run.run_id.slice(
              0,
              12,
            )}
          </span>
        </div>
      </div>
    </article>
  );
}


export default async function PipelineRunsPanel() {
  let summary:
    PipelineRunSummary
    | null = null;

  try {
    summary =
      await getPipelineRuns(
        12,
      );
  } catch {
    summary = null;
  }

  return (
    <section
      id="pipeline-runs"
      className="mt-5 overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.012]"
    >
      <div className="flex flex-col justify-between gap-4 border-b border-white/[0.06] px-5 py-5 md:flex-row md:items-center lg:px-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-300 shadow-[0_0_14px_rgba(125,211,252,0.7)]" />

            <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
              Pipeline Execution Telemetry
            </p>
          </div>

          <h2 className="mt-2 text-xl font-medium tracking-[-0.035em] text-white">
            Pipeline run history
          </h2>

          <p className="mt-1 max-w-[720px] text-[10px] leading-5 text-white/30">
            Actual execution state,
            duration, completion
            status, and run identity
            across instrumented
            GridPulse pipelines.
          </p>
        </div>

        {summary && (
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-emerald-300/10 bg-emerald-300/[0.025] px-3 py-2 text-[8px] text-emerald-200/70">
              {
                summary.successful_runs
              } succeeded
            </span>

            <span className="rounded-full border border-sky-300/10 bg-sky-300/[0.025] px-3 py-2 text-[8px] text-sky-200/70">
              {
                summary.running_runs
              } running
            </span>

            <span className="rounded-full border border-rose-400/10 bg-rose-400/[0.025] px-3 py-2 text-[8px] text-rose-300/70">
              {
                summary.failed_runs
              } failed
            </span>
          </div>
        )}
      </div>

      {!summary ? (
        <div className="p-6 text-sm text-white/30">
          Pipeline telemetry is
          currently unavailable.
        </div>
      ) : summary.runs.length ===
        0 ? (
        <div className="flex min-h-[180px] items-center justify-center p-6 text-center">
          <div>
            <p className="text-sm text-white/50">
              No instrumented
              pipeline runs yet.
            </p>

            <p className="mt-2 text-[9px] text-white/25">
              Execution telemetry
              will appear after an
              instrumented GridPulse
              pipeline runs.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-3 lg:p-6">
          {summary.runs.map(
            (run) => (
              <RunCard
                key={
                  run.run_id
                }
                run={run}
              />
            ),
          )}
        </div>
      )}

      <div className="flex flex-col justify-between gap-2 border-t border-white/[0.05] px-5 py-3 text-[7px] uppercase tracking-[0.11em] text-white/20 md:flex-row lg:px-6">
        <span>
          Verified execution
          telemetry
        </span>

        <span>
          Run state · duration ·
          completion · identity
        </span>
      </div>
    </section>
  );
}
