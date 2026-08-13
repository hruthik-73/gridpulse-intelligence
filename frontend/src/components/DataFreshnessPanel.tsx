import {
  getSourceFreshness,
} from "@/lib/api";

import type {
  FreshnessState,
  SourceFreshness,
} from "@/lib/api";


function stateStyle(
  state: FreshnessState,
) {
  switch (state) {
    case "FRESH":
      return {
        text:
          "text-emerald-200",
        dot:
          "bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.75)]",
        border:
          "border-emerald-300/15",
      };

    case "DELAYED":
      return {
        text:
          "text-amber-200",
        dot:
          "bg-amber-300 shadow-[0_0_14px_rgba(252,211,77,0.65)]",
        border:
          "border-amber-300/15",
      };

    case "STALE":
      return {
        text:
          "text-rose-300",
        dot:
          "bg-rose-400 shadow-[0_0_14px_rgba(251,113,133,0.7)]",
        border:
          "border-rose-400/15",
      };

    case "UNKNOWN":
    default:
      return {
        text:
          "text-white/35",
        dot:
          "bg-white/30",
        border:
          "border-white/[0.07]",
      };
  }
}


function formatAge(
  ageHours:
    | number
    | null,
): string {
  if (ageHours === null) {
    return "Unknown";
  }

  if (ageHours < 1) {
    return `${Math.max(
      1,
      Math.round(
        ageHours * 60,
      ),
    )}m`;
  }

  if (ageHours < 48) {
    return `${ageHours.toFixed(
      ageHours < 10
        ? 1
        : 0,
    )}h`;
  }

  return `${(
    ageHours / 24
  ).toFixed(1)}d`;
}


function formatTimestamp(
  timestamp:
    | string
    | null,
): string {
  if (!timestamp) {
    return "No timestamp";
  }

  const date =
    new Date(
      timestamp,
    );

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return timestamp;
  }

  return date.toLocaleString(
    "en-US",
    {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    },
  );
}


function FreshnessCard({
  signal,
}: {
  signal: SourceFreshness;
}) {
  const style =
    stateStyle(
      signal.state,
    );

  const agePosition =
    signal.age_hours === null
      ? 0
      : Math.min(
          100,
          (
            signal.age_hours
            / signal.stale_after_hours
          )
          * 100,
        );

  return (
    <article
      className={`relative overflow-hidden rounded-xl border bg-black/20 p-4 ${style.border}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`h-1.5 w-1.5 rounded-full ${style.dot}`}
            />

            <p
              className={`text-[8px] font-semibold uppercase tracking-[0.15em] ${style.text}`}
            >
              {signal.state}
            </p>
          </div>

          <p className="mt-3 text-base font-medium tracking-[-0.025em] text-white">
            {signal.display_name}
          </p>

          <p className="mt-1 text-[8px] text-white/25">
            {signal.dataset}
          </p>
        </div>

        <div className="text-right">
          <p className="text-2xl font-medium tracking-[-0.045em] text-white">
            {formatAge(
              signal.age_hours,
            )}
          </p>

          <p className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            signal age
          </p>
        </div>
      </div>

      <div className="mt-5">
        <div className="relative h-[5px] overflow-hidden rounded-full bg-white/[0.05]">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-emerald-300/60 via-amber-300/60 to-rose-400/70"
            style={{
              width: `${agePosition}%`,
            }}
          />
        </div>

        <div className="mt-2 flex justify-between text-[7px] uppercase tracking-[0.1em] text-white/15">
          <span>
            Fresh
          </span>

          <span>
            {signal.fresh_within_hours}h
          </span>

          <span>
            {signal.stale_after_hours}h stale
          </span>
        </div>
      </div>

      <div className="mt-5 space-y-3 border-t border-white/[0.05] pt-4">
        <div className="flex items-center justify-between gap-4">
          <span className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Latest signal
          </span>

          <span className="text-right text-[8px] text-white/45">
            {formatTimestamp(
              signal.latest_timestamp,
            )}
          </span>
        </div>

        <div className="flex items-center justify-between gap-4">
          <span className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Freshness basis
          </span>

          <span className="text-right text-[8px] text-white/45">
            {signal.timestamp_basis}
          </span>
        </div>
      </div>
    </article>
  );
}


export default async function DataFreshnessPanel() {
  let freshness:
    SourceFreshness[] = [];

  try {
    freshness =
      await getSourceFreshness();
  } catch {
    freshness = [];
  }

  const freshCount =
    freshness.filter(
      (signal) =>
        signal.state
        === "FRESH",
    ).length;

  const staleCount =
    freshness.filter(
      (signal) =>
        signal.state
        === "STALE",
    ).length;

  const overallState =
    freshness.length === 0
      ? "UNKNOWN"
      : staleCount > 0
        ? "ATTENTION"
        : freshCount
            === freshness.length
          ? "CURRENT"
          : "DELAYED";

  return (
    <section
      id="data-freshness"
      className="mt-5 overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.012]"
    >
      <div className="flex flex-col justify-between gap-4 border-b border-white/[0.06] px-5 py-5 md:flex-row md:items-center lg:px-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.75)]" />

            <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
              Data Freshness Intelligence
            </p>
          </div>

          <h2 className="mt-2 text-xl font-medium tracking-[-0.035em] text-white">
            Is the intelligence current?
          </h2>

          <p className="mt-1 max-w-[720px] text-[10px] leading-5 text-white/30">
            GridPulse evaluates
            source recency against
            operational freshness
            thresholds so stale data
            cannot silently look
            current.
          </p>
        </div>

        <div className="flex items-center gap-3 rounded-full border border-white/[0.06] bg-black/25 px-3 py-2">
          <span className="text-[7px] uppercase tracking-[0.14em] text-white/25">
            Overall
          </span>

          <span className="text-[9px] font-semibold text-emerald-200">
            {overallState}
          </span>
        </div>
      </div>

      {freshness.length === 0 ? (
        <div className="p-6 text-sm text-white/30">
          Freshness intelligence
          is currently unavailable.
        </div>
      ) : (
        <div className="grid gap-3 p-5 md:grid-cols-3 lg:p-6">
          {freshness.map(
            (signal) => (
              <FreshnessCard
                key={
                  signal.source
                }
                signal={
                  signal
                }
              />
            ),
          )}
        </div>
      )}

      <div className="flex flex-col justify-between gap-2 border-t border-white/[0.05] px-5 py-3 text-[7px] uppercase tracking-[0.11em] text-white/20 md:flex-row lg:px-6">
        <span>
          GridPulse operational SLA
          thresholds · not upstream
          source guarantees
        </span>

        <span>
          Timestamp basis is exposed
          for every freshness signal
        </span>
      </div>
    </section>
  );
}
