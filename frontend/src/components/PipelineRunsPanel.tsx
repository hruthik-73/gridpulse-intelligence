import {
  getPipelineRuns,
} from "@/lib/api";

import type {
  PipelineRun,
  PipelineRunStatus,
  PipelineRunSummary,
} from "@/lib/api";


const PIPELINE_STAGES = [
  "kafka_to_bronze",
  "bronze_to_silver",
  "build_gold",
  "dbt_build",
] as const;


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
      kafka_to_bronze:
        "Kafka → Bronze Ingestion",

      bronze_to_silver:
        "Bronze → Silver Transformation",

      build_gold:
        "Gold Analytics Build",

      dbt_build:
        "dbt Analytics Build",
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
      kafka_to_bronze:
        "Kafka events into replay-safe Bronze storage",

      bronze_to_silver:
        "Validation, normalization, and deduplication",

      build_gold:
        "Analytics-ready Gold mart generation",

      dbt_build:
        "Analytical modeling, testing, and publishing",
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


function formatRecords(
  value:
    | number
    | null,
): string {
  if (value === null) {
    return "—";
  }

  if (value === 0) {
    return "No new records";
  }

  return new Intl.NumberFormat(
    "en-US",
  ).format(
    value,
  );
}


function formatThroughput(
  value:
    | number
    | null,
): string {
  if (value === null) {
    return "—";
  }

  if (value === 0) {
    return "No new data";
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


function latestRunForStage(
  runs: PipelineRun[],
  stage: string,
): PipelineRun | null {
  const matching = runs
    .filter(
      (run) =>
        run.stage === stage,
    )
    .sort(
      (
        first,
        second,
      ) =>
        new Date(
          second.started_at,
        ).getTime()
        - new Date(
          first.started_at,
        ).getTime(),
    );

  return matching[0]
    ?? null;
}


function stageHistory(
  runs: PipelineRun[],
  stage: string,
): PipelineRun[] {
  return runs.filter(
    (run) =>
      run.stage === stage,
  );
}


function EmptyStageCard({
  stage,
}: {
  stage: string;
}) {
  return (
    <article className="rounded-xl border border-white/[0.055] bg-black/20 p-4">
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-white/20" />

        <span className="text-[8px] font-semibold uppercase tracking-[0.14em] text-white/25">
          No run data
        </span>
      </div>

      <p className="mt-4 text-base font-medium tracking-[-0.025em] text-white/70">
        {stageTitle(
          stage,
        )}
      </p>

      <p className="mt-1 text-[8px] leading-4 text-white/25">
        {stageDescription(
          stage,
        )}
      </p>

      <div className="mt-5 flex min-h-[105px] items-center justify-center rounded-lg border border-dashed border-white/[0.055] bg-black/15">
        <p className="text-center text-[8px] leading-4 text-white/20">
          No instrumented execution
          <br />
          recorded yet
        </p>
      </div>
    </article>
  );
}


function RunCard({
  run,
  history,
}: {
  run: PipelineRun;
  history: PipelineRun[];
}) {
  const style =
    statusStyle(
      run.status,
    );

  const failures =
    history.filter(
      (item) =>
        item.status
        === "FAILED",
    ).length;

  const successes =
    history.filter(
      (item) =>
        item.status
        === "SUCCEEDED",
    ).length;

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
            Records
          </p>

          <p
            className={`mt-2 text-sm font-medium ${
              run.records_processed
                && run.records_processed
                > 0
                ? "text-emerald-200/70"
                : "text-white/45"
            }`}
          >
            {formatRecords(
              run.records_processed,
            )}
          </p>
        </div>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-2">
        <div className="rounded-lg border border-white/[0.045] bg-black/20 p-3">
          <p className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Throughput
          </p>

          <p className="mt-2 text-xs font-medium text-white/55">
            {formatThroughput(
              run.throughput_records_per_second,
            )}
          </p>
        </div>

        <div className="rounded-lg border border-white/[0.045] bg-black/20 p-3">
          <p className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Exit code
          </p>

          <p
            className={`mt-2 text-xs font-medium ${
              run.exit_code === 0
                ? "text-emerald-200/65"
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
            Latest execution
          </span>

          <span className="text-right text-[8px] text-white/40">
            {formatTime(
              run.started_at,
            )}
          </span>
        </div>

        <div className="flex items-center justify-between gap-4">
          <span className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Retained history
          </span>

          <span className="text-right text-[8px] text-white/40">
            {history.length}
            {" "}
            runs
          </span>
        </div>

        <div className="flex items-center justify-between gap-4">
          <span className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Successful
          </span>

          <span className="text-right text-[8px] text-emerald-200/50">
            {successes}
          </span>
        </div>

        <div className="flex items-center justify-between gap-4">
          <span className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Failed
          </span>

          <span
            className={`text-right text-[8px] ${
              failures > 0
                ? "text-rose-300/70"
                : "text-white/40"
            }`}
          >
            {failures}
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
        100,
      );
  } catch {
    summary = null;
  }

  const operationalRuns =
    summary?.runs.filter(
      (run) =>
        PIPELINE_STAGES.some(
          (stage) =>
            stage === run.stage,
        ),
    )
    ?? [];

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
            Latest execution by stage
          </h2>

          <p className="mt-1 max-w-[720px] text-[10px] leading-5 text-white/30">
            One operational card per
            pipeline stage. Historical
            executions remain retained
            for SLA, failure, and
            recovery intelligence.
          </p>
        </div>

        {summary && (
          <div className="rounded-full border border-white/[0.06] bg-white/[0.015] px-3 py-2 text-[8px] text-white/30">
            {
              operationalRuns.length
            }
            {" "}
            operational runs retained
          </div>
        )}
      </div>

      {!summary ? (
        <div className="p-6 text-sm text-white/30">
          Pipeline telemetry is
          currently unavailable.
        </div>
      ) : (
        <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-4 lg:p-6">
          {PIPELINE_STAGES.map(
            (stage) => {
              const latest =
                latestRunForStage(
                  operationalRuns,
                  stage,
                );

              const history =
                stageHistory(
                  operationalRuns,
                  stage,
                );

              if (!latest) {
                return (
                  <EmptyStageCard
                    key={stage}
                    stage={stage}
                  />
                );
              }

              return (
                <RunCard
                  key={stage}
                  run={latest}
                  history={history}
                />
              );
            },
          )}
        </div>
      )}

      <div className="flex flex-col justify-between gap-2 border-t border-white/[0.05] px-5 py-3 text-[7px] uppercase tracking-[0.11em] text-white/20 md:flex-row lg:px-6">
        <span>
          Latest execution shown ·
          full history retained
        </span>

        <span>
          Smoke-test runs hidden from
          operational view
        </span>
      </div>
    </section>
  );
}
