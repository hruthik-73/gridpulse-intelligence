import {
  getDataQuality,
} from "@/lib/api";

import type {
  DataQualityDataset,
  DataQualitySnapshot,
} from "@/lib/api";


function formatRows(
  value:
    | number
    | null,
): string {
  if (value === null) {
    return "—";
  }

  return new Intl.NumberFormat(
    "en-US",
  ).format(
    value,
  );
}


function formatPercent(
  value:
    | number
    | null,
): string {
  if (value === null) {
    return "—";
  }

  return `${value.toFixed(
    2,
  )}%`;
}


function Metric({
  label,
  value,
  note,
  emphasis = false,
}: {
  label: string;
  value: string;
  note: string;
  emphasis?: boolean;
}) {
  return (
    <div className="rounded-xl border border-white/[0.055] bg-black/20 p-4">
      <p className="text-[7px] uppercase tracking-[0.13em] text-white/20">
        {label}
      </p>

      <p
        className={`mt-3 text-2xl font-medium tracking-[-0.04em] ${
          emphasis
            ? "text-emerald-200"
            : "text-white/80"
        }`}
      >
        {value}
      </p>

      <p className="mt-2 text-[8px] leading-4 text-white/25">
        {note}
      </p>
    </div>
  );
}


function DatasetRows({
  title,
  datasets,
}: {
  title: string;
  datasets: DataQualityDataset[];
}) {
  return (
    <div className="rounded-xl border border-white/[0.055] bg-black/15 p-4">
      <p className="text-[7px] uppercase tracking-[0.14em] text-white/20">
        {title}
      </p>

      <div className="mt-4 space-y-3">
        {datasets.map(
          (item) => (
            <div
              key={
                `${item.layer}-${item.dataset}`
              }
              className="flex items-center justify-between gap-4"
            >
              <span className="text-[9px] text-white/35">
                {item.dataset}
              </span>

              <span className="font-mono text-[9px] text-white/55">
                {formatRows(
                  item.rows,
                )}
              </span>
            </div>
          ),
        )}
      </div>
    </div>
  );
}


function conservationStyle(
  state: string,
): string {
  switch (state) {
    case "BALANCED":
      return "text-emerald-200";

    case "CHECK":
      return "text-rose-300";

    case "PARTIAL":
      return "text-amber-200";

    default:
      return "text-white/30";
  }
}


export default async function DataQualityPanel() {
  let snapshot:
    DataQualitySnapshot
    | null = null;

  try {
    snapshot =
      await getDataQuality();

  } catch {
    snapshot = null;
  }

  if (!snapshot) {
    return (
      <section
        id="data-quality"
        className="mt-5 rounded-2xl border border-white/[0.07] bg-white/[0.012] p-6"
      >
        <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
          Data Quality Intelligence
        </p>

        <p className="mt-3 text-sm text-white/30">
          Data-quality intelligence is
          currently unavailable.
        </p>
      </section>
    );
  }

  return (
    <section
      id="data-quality"
      className="mt-5 overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.012]"
    >
      <div className="flex flex-col justify-between gap-4 border-b border-white/[0.06] px-5 py-5 md:flex-row md:items-center lg:px-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.7)]" />

            <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
              Data Quality Intelligence
            </p>
          </div>

          <h2 className="mt-2 text-xl font-medium tracking-[-0.035em] text-white">
            What survived transformation?
          </h2>

          <p className="mt-1 max-w-[720px] text-[10px] leading-5 text-white/30">
            Current Bronze, Silver,
            quarantine, and Gold
            materializations reconciled
            into an explainable quality
            view.
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-white/[0.06] bg-white/[0.015] px-3 py-2">
          <span className="text-[7px] uppercase tracking-[0.1em] text-white/20">
            Conservation
          </span>

          <span
            className={`text-[8px] font-semibold ${conservationStyle(
              snapshot.conservation_state,
            )}`}
          >
            {
              snapshot.conservation_state
            }
          </span>
        </div>
      </div>

      <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-4 lg:p-6">
        <Metric
          label="Bronze input"
          value={
            formatRows(
              snapshot.bronze_input_rows,
            )
          }
          note="Materialized streaming events evaluated before Silver transformation."
        />

        <Metric
          label="Silver retained"
          value={
            formatRows(
              snapshot.silver_output_rows,
            )
          }
          note="Validated and deduplicated records currently retained in Silver."
          emphasis
        />

        <Metric
          label="Removed before Silver"
          value={
            formatRows(
              snapshot.removed_before_silver,
            )
          }
          note="Difference between current Bronze input and Silver retained rows."
        />

        <Metric
          label="Retention"
          value={
            formatPercent(
              snapshot.silver_retention_pct,
            )
          }
          note="Silver rows divided by current Bronze materialized rows."
          emphasis
        />
      </div>

      <div className="grid gap-3 border-t border-white/[0.05] p-5 md:grid-cols-3 lg:p-6">
        <Metric
          label="Quality failures"
          value={
            formatRows(
              snapshot.quality_failure_rows,
            )
          }
          note="Rows currently materialized in the Silver quality quarantine."
        />

        <Metric
          label="Deduplicated"
          value={
            formatRows(
              snapshot.deduplicated_rows,
            )
          }
          note="Derived only when Bronze, Silver, and quarantine counts reconcile."
        />

        <Metric
          label="Gold analytical rows"
          value={
            formatRows(
              snapshot.gold_output_rows,
            )
          }
          note="Aggregated analytical output; not treated as data-loss conservation."
        />
      </div>

      <div className="grid gap-3 border-t border-white/[0.05] p-5 md:grid-cols-2 lg:p-6">
        <DatasetRows
          title="Silver datasets"
          datasets={
            snapshot.silver_datasets
          }
        />

        <DatasetRows
          title="Gold marts"
          datasets={
            snapshot.gold_datasets
          }
        />
      </div>

      <div className="border-t border-white/[0.05] px-5 py-4 lg:px-6">
        <p className="max-w-[900px] text-[8px] leading-4 text-white/25">
          {snapshot.detail}
        </p>

        <div className="mt-3 flex flex-wrap gap-4 text-[6px] uppercase tracking-[0.1em] text-white/15">
          <span>
            Quality failure rate{" "}
            {formatPercent(
              snapshot.quality_failure_pct,
            )}
          </span>

          <span>
            Materialized data only
          </span>

          <span>
            No inferred Gold data loss
          </span>
        </div>
      </div>
    </section>
  );
}
