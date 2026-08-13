"use client";

import type {
  EVCity,
  GridAnomaly,
  PlatformHealth,
  RegionalGridSignal,
  WeatherForecast,
} from "@/lib/api";


interface NationalCommandCenterProps {
  topRisk: GridAnomaly | null;
  topRegion: RegionalGridSignal | null;
  weather: WeatherForecast | null;
  topEvCity: EVCity | null;
  health: PlatformHealth | null;
}


function formatNumber(
  value:
    | number
    | null
    | undefined,
  digits = 0,
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "en-US",
    {
      maximumFractionDigits:
        digits,
    },
  ).format(value);
}


function formatPercent(
  value:
    | number
    | null
    | undefined,
  signed = false,
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  const prefix =
    signed && value > 0
      ? "+"
      : "";

  return `${prefix}${formatNumber(
    value,
    1,
  )}%`;
}


function severityText(
  severity:
    | string
    | undefined,
): string {
  switch (severity) {
    case "CRITICAL":
      return "text-rose-300";

    case "HIGH":
      return "text-orange-200";

    case "ELEVATED":
      return "text-amber-200";

    default:
      return "text-emerald-200";
  }
}


function severityDot(
  severity:
    | string
    | undefined,
): string {
  switch (severity) {
    case "CRITICAL":
      return "bg-rose-400 shadow-[0_0_14px_rgba(251,113,133,0.8)]";

    case "HIGH":
      return "bg-orange-300 shadow-[0_0_14px_rgba(253,186,116,0.7)]";

    case "ELEVATED":
      return "bg-amber-300 shadow-[0_0_14px_rgba(252,211,77,0.7)]";

    default:
      return "bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.7)]";
  }
}


function scrollToSection(
  targetId: string,
): void {
  const element =
    document.getElementById(
      targetId,
    );

  if (!element) {
    return;
  }

  element.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}


function IntelligenceCard({
  index,
  kicker,
  title,
  value,
  valueClass = "text-white",
  detail,
  footer,
  dotClass,
  targetId,
}: {
  index: string;
  kicker: string;
  title: string;
  value: string;
  valueClass?: string;
  detail: string;
  footer: string;
  dotClass?: string;
  targetId: string;
}) {
  return (
    <button
      type="button"
      onClick={() =>
        scrollToSection(
          targetId,
        )
      }
      className="group relative w-full overflow-hidden rounded-xl border border-white/[0.065] bg-black/20 p-4 text-left transition-all duration-300 hover:-translate-y-0.5 hover:border-emerald-300/20 hover:bg-emerald-300/[0.025] focus:outline-none focus-visible:ring-1 focus-visible:ring-emerald-300/50"
    >
      <div className="absolute left-0 top-0 h-full w-px bg-gradient-to-b from-emerald-300/35 via-emerald-300/5 to-transparent" />

      <div className="absolute right-3 top-3 text-[12px] text-white/10 transition-all duration-300 group-hover:translate-x-0.5 group-hover:text-emerald-200/50">
        ↘
      </div>

      <div className="flex items-center justify-between pr-5">
        <p className="text-[7px] font-medium uppercase tracking-[0.18em] text-white/25">
          {index}
        </p>

        {dotClass && (
          <span
            className={`h-1.5 w-1.5 rounded-full ${dotClass}`}
          />
        )}
      </div>

      <p className="mt-4 text-[8px] font-semibold uppercase tracking-[0.16em] text-emerald-200/70">
        {kicker}
      </p>

      <p className="mt-2 truncate text-sm font-medium text-white/80">
        {title}
      </p>

      <p
        className={`mt-4 text-3xl font-medium tracking-[-0.045em] ${valueClass}`}
      >
        {value}
      </p>

      <p className="mt-2 min-h-[32px] text-[9px] leading-4 text-white/30">
        {detail}
      </p>

      <div className="mt-4 flex items-center justify-between border-t border-white/[0.05] pt-3">
        <p className="text-[7px] uppercase tracking-[0.13em] text-white/20">
          {footer}
        </p>

        <p className="text-[7px] uppercase tracking-[0.13em] text-white/15 transition-colors group-hover:text-emerald-200/50">
          Explore
        </p>
      </div>
    </button>
  );
}


export default function NationalCommandCenter({
  topRisk,
  topRegion,
  weather,
  topEvCity,
  health,
}: NationalCommandCenterProps) {
  const healthComponents =
    health
      ? [
          health.warehouse,
          health.kafka,
          health.prometheus,
          health.kafka_consumer,
        ]
      : [];

  const healthyComponents =
    healthComponents.filter(
      (component) =>
        component.status ===
        "healthy",
    ).length;

  const healthLabel =
    health
      ? health.status.toUpperCase()
      : "UNKNOWN";

  const healthValueClass =
    health?.status ===
    "healthy"
      ? "text-emerald-200"
      : health?.status ===
          "degraded"
        ? "text-amber-200"
        : "text-rose-300";

  const healthDotClass =
    health?.status ===
    "healthy"
      ? "bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.7)]"
      : health?.status ===
          "degraded"
        ? "bg-amber-300 shadow-[0_0_14px_rgba(252,211,77,0.7)]"
        : "bg-rose-400 shadow-[0_0_14px_rgba(251,113,133,0.7)]";

  return (
    <section className="mt-5 overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.012]">
      <div className="flex flex-col justify-between gap-4 border-b border-white/[0.06] px-5 py-5 md:flex-row md:items-center lg:px-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.8)]" />

            <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
              National Command Center
            </p>
          </div>

          <h2 className="mt-2 text-xl font-medium tracking-[-0.035em] text-white">
            GridPulse intelligence snapshot
          </h2>

          <p className="mt-1 text-[10px] text-white/30">
            Select an intelligence
            signal to explore its
            detailed operational view.
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-white/[0.06] bg-black/20 px-3 py-2">
          <span className="text-[7px] uppercase tracking-[0.15em] text-white/25">
            Intelligence layers
          </span>

          <span className="text-[9px] font-medium text-emerald-200">
            05
          </span>
        </div>
      </div>

      <div className="grid gap-3 p-5 md:grid-cols-2 lg:p-6 xl:grid-cols-5">
        <IntelligenceCard
          index="01"
          kicker="Balancing authority risk"
          title={
            topRisk
              ? `${topRisk.respondent} · ${topRisk.respondent_name}`
              : "No active signal"
          }
          value={
            topRisk
              ? formatNumber(
                  topRisk.risk_score,
                  1,
                )
              : "—"
          }
          valueClass={
            severityText(
              topRisk?.severity,
            )
          }
          detail={
            topRisk
              ? `Forecast error ${formatPercent(
                  topRisk.forecast_error_pct,
                )} · ${topRisk.history_points} historical observations`
              : "Historical authority intelligence unavailable."
          }
          footer={
            topRisk
              ? `${topRisk.severity} · historical anomaly`
              : "Awaiting authority data"
          }
          dotClass={
            severityDot(
              topRisk?.severity,
            )
          }
          targetId="grid-risk"
        />

        <IntelligenceCard
          index="02"
          kicker="Regional load pressure"
          title={
            topRegion
              ? `${topRegion.region} · ${topRegion.region_name}`
              : "No regional signal"
          }
          value={
            topRegion
              ? formatNumber(
                  topRegion.pressure_score,
                  1,
                )
              : "—"
          }
          valueClass={
            severityText(
              topRegion?.severity,
            )
          }
          detail={
            topRegion
              ? `Demand ${formatPercent(
                  topRegion.demand_vs_baseline_pct,
                  true,
                )} vs historical baseline`
              : "Regional pressure intelligence unavailable."
          }
          footer={
            topRegion
              ? `${topRegion.severity} · regional pressure`
              : "Awaiting regional data"
          }
          dotClass={
            severityDot(
              topRegion?.severity,
            )
          }
          targetId="regional-grid"
        />

        <IntelligenceCard
          index="03"
          kicker="Weather signal"
          title={
            weather
              ?.short_forecast ??
            "Weather unavailable"
          }
          value={
            weather
              ?.temperature_f !==
                null &&
            weather
              ?.temperature_f !==
                undefined
              ? `${formatNumber(
                  weather.temperature_f,
                )}°F`
              : "—"
          }
          detail={
            weather
              ? `Precipitation ${formatPercent(
                  weather.precipitation_probability,
                )} · humidity ${formatPercent(
                  weather.relative_humidity,
                )}`
              : "Current NWS forecast signal unavailable."
          }
          footer={
            weather
              ? `${weather.precipitation_risk} precipitation risk`
              : "Awaiting weather data"
          }
          dotClass="bg-sky-300 shadow-[0_0_14px_rgba(125,211,252,0.7)]"
          targetId="analytics-explorer"
        />

        <IntelligenceCard
          index="04"
          kicker="EV infrastructure"
          title={
            topEvCity
              ? `${topEvCity.city}, ${topEvCity.state}`
              : "Infrastructure unavailable"
          }
          value={
            topEvCity
              ? formatNumber(
                  topEvCity.station_count,
                )
              : "—"
          }
          detail={
            topEvCity
              ? `${formatNumber(
                  topEvCity.total_known_ports,
                )} known charging ports · ${formatNumber(
                  topEvCity.dc_fast_ports,
                )} DC fast`
              : "EV infrastructure intelligence unavailable."
          }
          footer="Charging stations"
          dotClass="bg-violet-300 shadow-[0_0_14px_rgba(196,181,253,0.7)]"
          targetId="analytics-explorer"
        />

        <IntelligenceCard
          index="05"
          kicker="Platform operations"
          title="GridPulse runtime"
          value={
            healthLabel
          }
          valueClass={
            healthValueClass
          }
          detail={
            health
              ? `${healthyComponents}/${healthComponents.length} runtime dependencies healthy`
              : "Platform health snapshot unavailable."
          }
          footer="Warehouse · Kafka · Metrics · Consumer"
          dotClass={
            healthDotClass
          }
          targetId="platform-health"
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-white/[0.05] px-5 py-3 text-[7px] uppercase tracking-[0.14em] text-white/20 lg:px-6">
        <span>
          CLICK TO EXPLORE
        </span>

        <span>
          HISTORICAL BASELINES
        </span>

        <span>
          REGIONAL PRESSURE
        </span>

        <span>
          WEATHER SIGNALS
        </span>

        <span>
          EV INFRASTRUCTURE
        </span>

        <span>
          RUNTIME HEALTH
        </span>
      </div>
    </section>
  );
}
