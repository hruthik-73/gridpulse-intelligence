import {
  getOperationalIncidents,
} from "@/lib/api";

import type {
  OperationalIncident,
  OperationalIncidentSummary,
} from "@/lib/api";


function severityStyle(
  severity:
    OperationalIncident["severity"],
) {
  switch (severity) {
    case "CRITICAL":
      return {
        text:
          "text-rose-300",
        dot:
          "bg-rose-400 shadow-[0_0_16px_rgba(251,113,133,0.8)]",
        border:
          "border-rose-400/20",
      };

    case "HIGH":
      return {
        text:
          "text-orange-200",
        dot:
          "bg-orange-300 shadow-[0_0_14px_rgba(253,186,116,0.7)]",
        border:
          "border-orange-300/20",
      };

    case "ELEVATED":
      return {
        text:
          "text-amber-200",
        dot:
          "bg-amber-300 shadow-[0_0_14px_rgba(252,211,77,0.65)]",
        border:
          "border-amber-300/15",
      };

    case "NORMAL":
    default:
      return {
        text:
          "text-emerald-200",
        dot:
          "bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.65)]",
        border:
          "border-emerald-300/15",
      };
  }
}


function IncidentCard({
  incident,
  rank,
}: {
  incident: OperationalIncident;
  rank: number;
}) {
  const style =
    severityStyle(
      incident.severity,
    );

  return (
    <article
      className={`rounded-xl border bg-black/20 p-4 ${style.border}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <span
            className={`h-1.5 w-1.5 rounded-full ${style.dot}`}
          />

          <span
            className={`text-[8px] font-semibold uppercase tracking-[0.15em] ${style.text}`}
          >
            {incident.severity}
          </span>
        </div>

        <span className="font-mono text-[8px] text-white/20">
          {String(
            rank,
          ).padStart(
            2,
            "0",
          )}
        </span>
      </div>

      <p className="mt-4 text-base font-medium tracking-[-0.025em] text-white/85">
        {incident.title}
      </p>

      <div className="mt-2 flex flex-wrap gap-2">
        <span className="rounded-full border border-white/[0.05] bg-white/[0.025] px-2 py-1 text-[7px] uppercase tracking-[0.11em] text-white/25">
          {incident.category}
        </span>

        <span className="rounded-full border border-white/[0.05] bg-white/[0.025] px-2 py-1 text-[7px] uppercase tracking-[0.11em] text-white/25">
          {incident.current_state}
        </span>
      </div>

      <div className="mt-4 rounded-lg border border-white/[0.045] bg-black/20 p-3">
        <p className="text-[7px] uppercase tracking-[0.13em] text-white/20">
          Evidence
        </p>

        <p className="mt-2 text-[9px] leading-4 text-white/40">
          {incident.evidence}
        </p>
      </div>

      <div className="mt-3 rounded-lg border border-emerald-300/[0.07] bg-emerald-300/[0.018] p-3">
        <p className="text-[7px] uppercase tracking-[0.13em] text-emerald-200/45">
          Recommended action
        </p>

        <p className="mt-2 text-[9px] leading-4 text-white/45">
          {incident.recommended_action}
        </p>
      </div>
    </article>
  );
}


export default async function OperationalIncidentPanel() {
  let summary:
    OperationalIncidentSummary
    | null = null;

  try {
    summary =
      await getOperationalIncidents();
  } catch {
    summary = null;
  }

  const incidents =
    summary?.incidents
    ?? [];

  const highestSeverity =
    summary?.highest_severity
    ?? "NORMAL";

  const headerStyle =
    severityStyle(
      highestSeverity,
    );

  return (
    <section
      id="operational-incidents"
      className="mt-5 overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.012]"
    >
      <div className="flex flex-col justify-between gap-4 border-b border-white/[0.06] px-5 py-5 md:flex-row md:items-center lg:px-6">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`h-1.5 w-1.5 rounded-full ${headerStyle.dot}`}
            />

            <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
              Operational Incident Intelligence
            </p>
          </div>

          <h2 className="mt-2 text-xl font-medium tracking-[-0.035em] text-white">
            What needs attention?
          </h2>

          <p className="mt-1 max-w-[720px] text-[10px] leading-5 text-white/30">
            GridPulse combines
            source freshness and
            runtime dependency health
            into prioritized,
            explainable operational
            incidents.
          </p>
        </div>

        <div className="flex items-center gap-4 rounded-xl border border-white/[0.06] bg-black/25 px-4 py-3">
          <div>
            <p className="text-[7px] uppercase tracking-[0.13em] text-white/20">
              Active
            </p>

            <p className="mt-1 text-xl font-medium text-white">
              {summary?.active_incidents
                ?? "—"}
            </p>
          </div>

          <div className="h-8 w-px bg-white/[0.06]" />

          <div>
            <p className="text-[7px] uppercase tracking-[0.13em] text-white/20">
              Highest
            </p>

            <p
              className={`mt-1 text-[10px] font-semibold ${headerStyle.text}`}
            >
              {summary
                ? highestSeverity
                : "UNKNOWN"}
            </p>
          </div>
        </div>
      </div>

      {!summary ? (
        <div className="p-6 text-sm text-white/30">
          Operational incident
          intelligence is currently
          unavailable.
        </div>
      ) : incidents.length === 0 ? (
        <div className="flex min-h-[180px] items-center justify-center p-6">
          <div className="text-center">
            <span className="mx-auto block h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(110,231,183,0.8)]" />

            <p className="mt-4 text-base font-medium text-white/80">
              No active incidents
            </p>

            <p className="mt-2 text-[9px] text-white/30">
              Sources are within
              configured freshness
              thresholds and runtime
              dependencies are healthy.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-3 lg:p-6">
          {incidents.map(
            (
              incident,
              index,
            ) => (
              <IncidentCard
                key={
                  incident.incident_id
                }
                incident={
                  incident
                }
                rank={
                  index + 1
                }
              />
            ),
          )}
        </div>
      )}

      <div className="flex flex-col justify-between gap-2 border-t border-white/[0.05] px-5 py-3 text-[7px] uppercase tracking-[0.11em] text-white/20 md:flex-row lg:px-6">
        <span>
          Rule-based operational
          intelligence · evidence
          remains visible
        </span>

        <span>
          No automated remediation
          is performed
        </span>
      </div>
    </section>
  );
}
