import {
  Activity,
  Database,
  RadioTower,
  ServerCog,
} from "lucide-react";

import type {
  ComponentHealth,
  HealthState,
  PlatformHealth,
} from "@/lib/api";


interface PlatformHealthPanelProps {
  health: PlatformHealth | null;
}


interface HealthItemProps {
  title: string;

  component:
    | ComponentHealth
    | null;

  icon: React.ComponentType<{
    size?: number;
    className?: string;
  }>;
}


function statusClasses(
  status: HealthState | null,
): string {
  if (status === "healthy") {
    return "bg-emerald-300 shadow-[0_0_10px_rgba(110,231,183,0.65)]";
  }

  if (status === "degraded") {
    return "bg-amber-300 shadow-[0_0_10px_rgba(252,211,77,0.55)]";
  }

  if (status === "local_only") {
    return "bg-sky-300 shadow-[0_0_10px_rgba(125,211,252,0.45)]";
  }

  return "bg-rose-400 shadow-[0_0_10px_rgba(251,113,133,0.55)]";
}


function statusText(
  status: HealthState | null,
): string {
  if (!status) {
    return "Unavailable";
  }

  if (status === "local_only") {
    return "Local only";
  }

  return (
    status.charAt(0).toUpperCase()
    + status.slice(1)
  );
}


function HealthItem({
  title,
  component,
  icon: Icon,
}: HealthItemProps) {
  const localOnly =
    component?.status
    === "local_only";

  return (
    <article className="rounded-2xl border border-white/[0.065] bg-black/20 p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-xl border border-white/[0.07] bg-white/[0.025]">
            <Icon
              size={15}
              className="text-white/55"
            />
          </div>

          <div>
            <p className="text-xs font-medium text-white/80">
              {title}
            </p>

            <div className="mt-1.5 flex items-center gap-2">
              <span
                className={`h-1.5 w-1.5 rounded-full ${statusClasses(
                  component?.status
                    ?? null,
                )}`}
              />

              <span className="text-[9px] uppercase tracking-[0.14em] text-white/35">
                {statusText(
                  component?.status
                    ?? null,
                )}
              </span>
            </div>
          </div>
        </div>

        <div className="text-right">
          <p className="text-[9px] uppercase tracking-[0.12em] text-white/20">
            {localOnly
              ? "Runtime"
              : "Latency"}
          </p>

          <p className="mt-1 text-xs text-white/55">
            {localOnly
              ? "Local"
              : component
                ? `${component.latency_ms.toFixed(
                    1,
                  )} ms`
                : "—"}
          </p>
        </div>
      </div>

      <p className="mt-5 min-h-[40px] text-[10px] leading-5 text-white/30">
        {component?.detail
          ?? "Health information is currently unavailable."}
      </p>
    </article>
  );
}


export default function PlatformHealthPanel({
  health,
}: PlatformHealthPanelProps) {
  const overall =
    health?.status
    ?? null;

  const portfolioMode =
    health?.runtime_mode
    === "portfolio";

  return (
    <section className="mt-5 overflow-hidden rounded-[18px] border border-white/[0.08] bg-[rgba(8,13,12,0.72)] backdrop-blur-xl">
      <div className="flex flex-col gap-4 border-b border-white/[0.06] px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-emerald-200">
            {portfolioMode
              ? "PORTFOLIO SNAPSHOT"
              : "PLATFORM HEALTH"}
          </p>

          <h2 className="mt-2 text-lg font-medium text-white">
            {portfolioMode
              ? "Published analytics environment"
              : "Runtime infrastructure"}
          </h2>

          <p className="mt-1 max-w-2xl text-xs leading-5 text-white/35">
            {portfolioMode
              ? (
                  <>
                    The public experience
                    serves a read-only
                    GridPulse analytics
                    snapshot. Streaming and
                    observability runtimes
                    remain part of the
                    reproducible local
                    engineering environment.
                  </>
                )
              : (
                  <>
                    Live dependency checks
                    from the GridPulse
                    serving layer.
                  </>
                )}
          </p>
        </div>

        <div className="flex w-fit items-center gap-2 rounded-full border border-white/[0.07] bg-black/25 px-4 py-2">
          <span
            className={`h-2 w-2 rounded-full ${
              portfolioMode
                ? "bg-sky-300 shadow-[0_0_10px_rgba(125,211,252,0.45)]"
                : statusClasses(
                    overall,
                  )
            }`}
          />

          <span className="text-[9px] font-medium uppercase tracking-[0.16em] text-white/50">
            {portfolioMode
              ? "Portfolio snapshot"
              : overall
                ? `Platform ${statusText(
                    overall,
                  )}`
                : "Health unavailable"}
          </span>
        </div>
      </div>

      <div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-4">
        <HealthItem
          title={
            portfolioMode
              ? "DuckDB Analytics Snapshot"
              : "DuckDB Warehouse"
          }
          component={
            health?.warehouse
            ?? null
          }
          icon={Database}
        />

        <HealthItem
          title="Kafka Runtime"
          component={
            health?.kafka
            ?? null
          }
          icon={RadioTower}
        />

        <HealthItem
          title="Prometheus Runtime"
          component={
            health?.prometheus
            ?? null
          }
          icon={Activity}
        />

        <HealthItem
          title="Kafka Consumer"
          component={
            health?.kafka_consumer
            ?? null
          }
          icon={ServerCog}
        />
      </div>

      {portfolioMode && (
        <div className="border-t border-white/[0.055] px-6 py-4">
          <p className="text-[10px] leading-5 text-white/25">
            Public Portfolio Mode
            preserves real analytical
            output while keeping Kafka,
            Prometheus, and consumer
            runtime claims limited to the
            environment where they
            actually execute.
          </p>
        </div>
      )}
    </section>
  );
}
