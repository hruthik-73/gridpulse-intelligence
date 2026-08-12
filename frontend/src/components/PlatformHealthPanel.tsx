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
  component: ComponentHealth | null;
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

  return "bg-rose-400 shadow-[0_0_10px_rgba(251,113,133,0.55)]";
}

function statusText(
  status: HealthState | null,
): string {
  if (!status) {
    return "Unavailable";
  }

  return (
    status.charAt(0).toUpperCase() +
    status.slice(1)
  );
}

function HealthItem({
  title,
  component,
  icon: Icon,
}: HealthItemProps) {
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
                  component?.status ??
                    null,
                )}`}
              />

              <span className="text-[9px] uppercase tracking-[0.14em] text-white/35">
                {statusText(
                  component?.status ??
                    null,
                )}
              </span>
            </div>
          </div>
        </div>

        <div className="text-right">
          <p className="text-[9px] uppercase tracking-[0.12em] text-white/20">
            Latency
          </p>

          <p className="mt-1 text-xs text-white/55">
            {component
              ? `${component.latency_ms.toFixed(
                  1,
                )} ms`
              : "—"}
          </p>
        </div>
      </div>

      <p className="mt-5 min-h-[40px] text-[10px] leading-5 text-white/30">
        {component?.detail ??
          "Health information is currently unavailable."}
      </p>
    </article>
  );
}

export default function PlatformHealthPanel({
  health,
}: PlatformHealthPanelProps) {
  const overall =
    health?.status ?? null;

  return (
    <section className="mt-5 overflow-hidden rounded-[18px] border border-white/[0.08] bg-[rgba(8,13,12,0.72)] backdrop-blur-xl">
      <div className="flex flex-col gap-4 border-b border-white/[0.06] px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-emerald-200">
            PLATFORM HEALTH
          </p>

          <h2 className="mt-2 text-lg font-medium text-white">
            Runtime infrastructure
          </h2>

          <p className="mt-1 text-xs text-white/35">
            Live dependency checks
            from the GridPulse
            serving layer.
          </p>
        </div>

        <div className="flex w-fit items-center gap-2 rounded-full border border-white/[0.07] bg-black/25 px-4 py-2">
          <span
            className={`h-2 w-2 rounded-full ${statusClasses(
              overall,
            )}`}
          />

          <span className="text-[9px] font-medium uppercase tracking-[0.16em] text-white/50">
            {overall
              ? `Platform ${overall}`
              : "Health unavailable"}
          </span>
        </div>
      </div>

      <div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-4">
        <HealthItem
          title="DuckDB Warehouse"
          component={
            health?.warehouse ??
            null
          }
          icon={Database}
        />

        <HealthItem
          title="Kafka"
          component={
            health?.kafka ??
            null
          }
          icon={RadioTower}
        />

        <HealthItem
          title="Prometheus"
          component={
            health?.prometheus ??
            null
          }
          icon={Activity}
        />

        <HealthItem
          title="Kafka Consumer"
          component={
            health?.kafka_consumer ??
            null
          }
          icon={ServerCog}
        />
      </div>
    </section>
  );
}
