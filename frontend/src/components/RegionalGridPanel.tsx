"use client";

import type {
  GridRiskSeverity,
  RegionalGridSignal,
} from "@/lib/api";


interface RegionalGridPanelProps {
  regions: RegionalGridSignal[];
}


function severityClasses(
  severity: GridRiskSeverity,
) {
  switch (severity) {
    case "CRITICAL":
      return {
        dot: "bg-rose-400 shadow-[0_0_14px_rgba(251,113,133,0.8)]",
        text: "text-rose-300",
        border: "border-rose-400/20",
        background: "bg-rose-400/[0.04]",
      };

    case "HIGH":
      return {
        dot: "bg-orange-300 shadow-[0_0_14px_rgba(253,186,116,0.7)]",
        text: "text-orange-200",
        border: "border-orange-300/20",
        background: "bg-orange-300/[0.035]",
      };

    case "ELEVATED":
      return {
        dot: "bg-amber-300 shadow-[0_0_14px_rgba(252,211,77,0.65)]",
        text: "text-amber-200",
        border: "border-amber-300/15",
        background: "bg-amber-300/[0.03]",
      };

    case "NORMAL":
    default:
      return {
        dot: "bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.65)]",
        text: "text-emerald-200",
        border: "border-emerald-300/15",
        background: "bg-emerald-300/[0.025]",
      };
  }
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


function formatSignedPercent(
  value:
    | number
    | null
    | undefined,
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  const prefix =
    value > 0
      ? "+"
      : "";

  return `${prefix}${formatNumber(
    value,
    1,
  )}%`;
}


function formatPercent(
  value:
    | number
    | null
    | undefined,
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return `${formatNumber(
    Math.abs(value),
    1,
  )}%`;
}


function PressureGauge({
  score,
  severity,
}: {
  score: number;
  severity: GridRiskSeverity;
}) {
  const classes =
    severityClasses(
      severity,
    );

  const safeScore =
    Math.min(
      100,
      Math.max(
        0,
        score,
      ),
    );

  return (
    <div className="relative flex h-[132px] w-[132px] shrink-0 items-center justify-center">
      <div className="absolute inset-0 rounded-full border border-white/[0.05]" />

      <div
        className="absolute inset-[7px] rounded-full"
        style={{
          background: `conic-gradient(
            rgba(99,245,200,0.9) 0deg,
            rgba(99,245,200,0.9) ${
              safeScore * 3.6
            }deg,
            rgba(255,255,255,0.04) ${
              safeScore * 3.6
            }deg,
            rgba(255,255,255,0.04) 360deg
          )`,
        }}
      />

      <div className="absolute inset-[12px] rounded-full bg-[#06100d]" />

      <div className="relative text-center">
        <p className="text-3xl font-medium tracking-[-0.05em] text-white">
          {formatNumber(
            safeScore,
            1,
          )}
        </p>

        <p className="mt-1 text-[8px] uppercase tracking-[0.17em] text-white/30">
          Pressure
        </p>

        <div
          className={`mt-2 flex items-center justify-center gap-1.5 text-[8px] font-semibold uppercase tracking-[0.13em] ${classes.text}`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${classes.dot}`}
          />

          {severity}
        </div>
      </div>
    </div>
  );
}


function SignalBar({
  label,
  score,
}: {
  label: string;
  score: number;
}) {
  const width =
    Math.min(
      100,
      Math.max(
        0,
        score / 4 * 100,
      ),
    );

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <span className="text-[8px] uppercase tracking-[0.12em] text-white/25">
          {label}
        </span>

        <span className="text-[9px] text-white/50">
          {formatNumber(
            score,
            2,
          )}σ
        </span>
      </div>

      <div className="h-1 overflow-hidden rounded-full bg-white/[0.05]">
        <div
          className="h-full rounded-full bg-emerald-300/70 shadow-[0_0_10px_rgba(110,231,183,0.35)]"
          style={{
            width: `${width}%`,
          }}
        />
      </div>
    </div>
  );
}


function RegionCard({
  region,
  rank,
}: {
  region: RegionalGridSignal;
  rank: number;
}) {
  const classes =
    severityClasses(
      region.severity,
    );

  return (
    <article
      className={`rounded-xl border p-4 ${classes.border} ${classes.background}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`h-1.5 w-1.5 rounded-full ${classes.dot}`}
            />

            <span className="text-[9px] text-white/25">
              {String(
                rank,
              ).padStart(
                2,
                "0",
              )}
            </span>

            <span
              className={`text-[8px] font-semibold uppercase tracking-[0.13em] ${classes.text}`}
            >
              {region.severity}
            </span>
          </div>

          <p className="mt-3 text-lg font-medium tracking-[-0.03em] text-white">
            {region.region}
          </p>

          <p className="mt-1 truncate text-[9px] text-white/30">
            {region.region_name}
          </p>
        </div>

        <div className="text-right">
          <p className="text-2xl font-medium tracking-[-0.04em] text-white">
            {formatNumber(
              region.pressure_score,
              1,
            )}
          </p>

          <p className="text-[7px] uppercase tracking-[0.13em] text-white/20">
            pressure
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2">
        <div className="rounded-lg border border-white/[0.05] bg-black/15 p-3">
          <p className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Demand
          </p>

          <p className="mt-1 text-sm text-white/70">
            {formatNumber(
              region.demand_mwh,
            )}
          </p>

          <p className="mt-1 text-[7px] text-white/20">
            MWh
          </p>
        </div>

        <div className="rounded-lg border border-white/[0.05] bg-black/15 p-3">
          <p className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            vs baseline
          </p>

          <p className="mt-1 text-sm text-white/70">
            {formatSignedPercent(
              region.demand_vs_baseline_pct,
            )}
          </p>

          <p className="mt-1 text-[7px] text-white/20">
            historical
          </p>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <SignalBar
          label="Demand pressure"
          score={
            region.demand_deviation_score
          }
        />

        <SignalBar
          label="Forecast deviation"
          score={
            region.forecast_deviation_score
          }
        />

        <SignalBar
          label="Generation imbalance"
          score={
            region.generation_deviation_score
          }
        />
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-white/[0.05] pt-3 text-[8px]">
        <span className="text-white/20">
          1h demand
        </span>

        <span className="text-white/50">
          {formatSignedPercent(
            region.demand_change_pct,
          )}
        </span>

        <span className="text-white/20">
          history
        </span>

        <span className="text-white/50">
          {
            region.history_points
          }h
        </span>
      </div>
    </article>
  );
}


export default function RegionalGridPanel({
  regions,
}: RegionalGridPanelProps) {
  if (regions.length === 0) {
    return (
      <section className="mt-5 rounded-2xl border border-white/[0.07] bg-white/[0.015] p-6">
        <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
          Regional Grid Intelligence
        </p>

        <p className="mt-3 text-sm text-white/35">
          Regional pressure
          intelligence is currently
          unavailable.
        </p>
      </section>
    );
  }

  const topRegion =
    regions[0];

  const classes =
    severityClasses(
      topRegion.severity,
    );

  const displayed =
    regions.slice(
      0,
      6,
    );

  return (
    <section className="mt-5 overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.015]">
      <div className="grid gap-6 border-b border-white/[0.06] p-5 lg:grid-cols-[1.15fr_0.85fr] lg:p-6">
        <div>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
                Regional Grid Intelligence
              </p>

              <h2 className="mt-2 text-2xl font-medium tracking-[-0.035em] text-white">
                U.S. regional load pressure
              </h2>

              <p className="mt-2 max-w-[690px] text-xs leading-5 text-white/35">
                GridPulse evaluates
                regional demand
                against each
                region&apos;s own
                historical baseline,
                then combines load,
                forecast, and
                generation deviation
                into an explainable
                pressure signal.
              </p>
            </div>

            <div className="flex items-center gap-2 rounded-full border border-emerald-300/10 bg-emerald-300/[0.03] px-3 py-2 text-[8px] uppercase tracking-[0.16em] text-emerald-200">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.7)]" />

              Regional model active
            </div>
          </div>

          <div className="mt-7 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-white/[0.06] bg-black/15 p-4">
              <p className="text-[8px] uppercase tracking-[0.14em] text-white/25">
                Current demand
              </p>

              <p className="mt-2 text-2xl font-medium tracking-[-0.03em] text-white">
                {formatNumber(
                  topRegion.demand_mwh,
                )}
              </p>

              <p className="mt-1 text-[8px] text-white/25">
                MWh
              </p>
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-black/15 p-4">
              <p className="text-[8px] uppercase tracking-[0.14em] text-white/25">
                Historical baseline
              </p>

              <p className="mt-2 text-2xl font-medium tracking-[-0.03em] text-white">
                {formatNumber(
                  topRegion.demand_baseline_mwh,
                )}
              </p>

              <p className="mt-1 text-[8px] text-white/25">
                MWh
              </p>
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-black/15 p-4">
              <p className="text-[8px] uppercase tracking-[0.14em] text-white/25">
                Demand vs baseline
              </p>

              <p
                className={`mt-2 text-2xl font-medium tracking-[-0.03em] ${classes.text}`}
              >
                {formatSignedPercent(
                  topRegion.demand_vs_baseline_pct,
                )}
              </p>

              <p className="mt-1 text-[8px] text-white/25">
                latest observation
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.05] bg-black/20 p-5">
          <div className="flex items-center gap-5">
            <PressureGauge
              score={
                topRegion.pressure_score
              }
              severity={
                topRegion.severity
              }
            />

            <div className="min-w-0">
              <p className="text-[8px] uppercase tracking-[0.15em] text-white/25">
                Highest regional pressure
              </p>

              <p className="mt-2 text-xl font-medium text-white">
                {topRegion.region}
              </p>

              <p className="mt-1 truncate text-[9px] text-white/30">
                {
                  topRegion.region_name
                }
              </p>

              <div className="mt-4 space-y-2 text-[9px]">
                <div className="flex justify-between gap-6">
                  <span className="text-white/25">
                    1h demand
                  </span>

                  <span className="text-white/60">
                    {formatSignedPercent(
                      topRegion.demand_change_pct,
                    )}
                  </span>
                </div>

                <div className="flex justify-between gap-6">
                  <span className="text-white/25">
                    Forecast error
                  </span>

                  <span className="text-white/60">
                    {formatPercent(
                      topRegion.forecast_error_pct,
                    )}
                  </span>
                </div>

                <div className="flex justify-between gap-6">
                  <span className="text-white/25">
                    Generation gap
                  </span>

                  <span className="text-white/60">
                    {formatPercent(
                      topRegion.generation_gap_pct,
                    )}
                  </span>
                </div>

                <div className="flex justify-between gap-6">
                  <span className="text-white/25">
                    History
                  </span>

                  <span className="text-white/60">
                    {
                      topRegion.history_points
                    } hours
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="p-5 lg:p-6">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <p className="text-[8px] uppercase tracking-[0.17em] text-white/25">
              Regional pressure ranking
            </p>

            <p className="mt-1 text-xs text-white/45">
              Regional aggregates
              remain separate from
              balancing-authority risk
            </p>
          </div>

          <p className="text-[8px] uppercase tracking-[0.14em] text-white/20">
            Pressure 0–100
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {displayed.map(
            (
              region,
              index,
            ) => (
              <RegionCard
                key={`${region.region}-${region.period}`}
                region={
                  region
                }
                rank={
                  index + 1
                }
              />
            ),
          )}
        </div>
      </div>

      <div className="border-t border-white/[0.05] px-5 py-3 text-[8px] leading-4 text-white/20 lg:px-6">
        Regional pressure combines
        unusually high demand,
        forecast deviation, and
        generation-demand imbalance
        relative to each region&apos;s
        own historical behavior.
        Signals are analytical
        indicators and are not
        official reliability or
        outage declarations.
      </div>
    </section>
  );
}
