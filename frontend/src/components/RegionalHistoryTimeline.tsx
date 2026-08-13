"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getRegionalGridHistory,
} from "@/lib/api";

import type {
  RegionalGridHistoryPoint,
  RegionalGridSignal,
} from "@/lib/api";


interface RegionalHistoryTimelineProps {
  region:
    | RegionalGridSignal
    | null;
}


function formatNumber(
  value:
    | number
    | null
    | undefined,
  digits = 0,
): string {
  if (
    value === null
    || value === undefined
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


function periodLabel(
  period: string,
): string {
  const date =
    new Date(
      period.replace(
        " ",
        "T",
      ),
    );

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return period;
  }

  return date.toLocaleString(
    "en-US",
    {
      month: "short",
      day: "numeric",
      hour: "numeric",
    },
  );
}


export default function RegionalHistoryTimeline({
  region,
}: RegionalHistoryTimelineProps) {
  const [
    history,
    setHistory,
  ] = useState<
    RegionalGridHistoryPoint[]
  >([]);

  const [
    loading,
    setLoading,
  ] = useState(
    false,
  );

  const [
    error,
    setError,
  ] = useState(
    false,
  );

  useEffect(
    () => {
      if (!region) {
        setHistory([]);
        return;
      }

      let cancelled =
        false;

      async function loadHistory() {
        setLoading(
          true,
        );

        setError(
          false,
        );

        try {
          const data =
            await getRegionalGridHistory(
              region.region,
              168,
            );

          if (!cancelled) {
            setHistory(
              data,
            );
          }
        } catch {
          if (!cancelled) {
            setHistory([]);
            setError(
              true,
            );
          }
        } finally {
          if (!cancelled) {
            setLoading(
              false,
            );
          }
        }
      }

      void loadHistory();

      return () => {
        cancelled = true;
      };
    },
    [
      region,
    ],
  );

  const summary =
    useMemo(
      () => {
        if (
          history.length === 0
        ) {
          return null;
        }

        const demands =
          history.map(
            (point) =>
              point.demand_mwh,
          );

        const total =
          demands.reduce(
            (
              current,
              value,
            ) =>
              current
              + value,
            0,
          );

        return {
          average:
            total
            / demands.length,

          peak:
            Math.max(
              ...demands,
            ),

          minimum:
            Math.min(
              ...demands,
            ),

          replayPoints:
            history.filter(
              (point) =>
                point.contains_replay,
            ).length,
        };
      },
      [
        history,
      ],
    );

  if (!region) {
    return null;
  }

  return (
    <section className="mt-3 overflow-hidden rounded-2xl border border-white/[0.07] bg-[#050b09]/90">
      <div className="flex flex-col justify-between gap-4 border-b border-white/[0.06] px-5 py-5 md:flex-row md:items-center lg:px-6">
        <div>
          <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-emerald-200">
            Historical Drill-Down
          </p>

          <h3 className="mt-2 text-xl font-medium tracking-[-0.035em] text-white">
            {region.region_name}
            {" · "}
            168-hour demand history
          </h3>

          <p className="mt-1 text-[9px] text-white/30">
            Demand, forecast, and
            historical baseline for
            the selected regional
            intelligence node.
          </p>
        </div>

        <div className="rounded-full border border-white/[0.06] bg-black/25 px-3 py-2 text-[8px] uppercase tracking-[0.14em] text-white/30">
          {history.length}
          {" "}
          observations
        </div>
      </div>

      {loading && (
        <div className="flex min-h-[360px] items-center justify-center">
          <div className="flex items-center gap-3 text-[8px] uppercase tracking-[0.16em] text-white/25">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.75)]" />

            Loading regional history
          </div>
        </div>
      )}

      {!loading
        && error && (
        <div className="flex min-h-[260px] items-center justify-center px-6 text-center text-[10px] text-white/30">
          Regional historical data
          could not be loaded.
        </div>
      )}

      {!loading
        && !error
        && history.length > 0 && (
        <>
          <div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-4 lg:p-6">
            <div className="rounded-xl border border-white/[0.055] bg-black/20 p-4">
              <p className="text-[7px] uppercase tracking-[0.14em] text-white/20">
                Current demand
              </p>

              <p className="mt-2 text-2xl font-medium tracking-[-0.04em] text-white">
                {formatNumber(
                  history[
                    history.length - 1
                  ].demand_mwh,
                )}
              </p>

              <p className="mt-1 text-[7px] text-white/20">
                MWh
              </p>
            </div>

            <div className="rounded-xl border border-white/[0.055] bg-black/20 p-4">
              <p className="text-[7px] uppercase tracking-[0.14em] text-white/20">
                168h average
              </p>

              <p className="mt-2 text-2xl font-medium tracking-[-0.04em] text-white">
                {formatNumber(
                  summary?.average,
                )}
              </p>

              <p className="mt-1 text-[7px] text-white/20">
                MWh
              </p>
            </div>

            <div className="rounded-xl border border-white/[0.055] bg-black/20 p-4">
              <p className="text-[7px] uppercase tracking-[0.14em] text-white/20">
                Peak demand
              </p>

              <p className="mt-2 text-2xl font-medium tracking-[-0.04em] text-emerald-200">
                {formatNumber(
                  summary?.peak,
                )}
              </p>

              <p className="mt-1 text-[7px] text-white/20">
                MWh
              </p>
            </div>

            <div className="rounded-xl border border-white/[0.055] bg-black/20 p-4">
              <p className="text-[7px] uppercase tracking-[0.14em] text-white/20">
                Replay coverage
              </p>

              <p className="mt-2 text-2xl font-medium tracking-[-0.04em] text-white">
                {formatNumber(
                  summary?.replayPoints,
                )}
              </p>

              <p className="mt-1 text-[7px] text-white/20">
                historical events
              </p>
            </div>
          </div>

          <div className="h-[360px] px-2 pb-5 pr-5 lg:px-4 lg:pb-6 lg:pr-6">
            <ResponsiveContainer
              width="100%"
              height="100%"
            >
              <ComposedChart
                data={history}
                margin={{
                  top: 12,
                  right: 12,
                  bottom: 12,
                  left: 4,
                }}
              >
                <defs>
                  <linearGradient
                    id="regionalDemandFill"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="0%"
                      stopColor="#6ee7b7"
                      stopOpacity={0.28}
                    />

                    <stop
                      offset="100%"
                      stopColor="#6ee7b7"
                      stopOpacity={0.01}
                    />
                  </linearGradient>
                </defs>

                <CartesianGrid
                  vertical={false}
                  stroke="rgba(255,255,255,0.05)"
                />

                <XAxis
                  dataKey="period"
                  tickFormatter={
                    periodLabel
                  }
                  minTickGap={54}
                  tick={{
                    fill:
                      "rgba(255,255,255,0.25)",
                    fontSize: 8,
                  }}
                  axisLine={false}
                  tickLine={false}
                />

                <YAxis
                  width={58}
                  tickFormatter={(
                    value,
                  ) =>
                    formatNumber(
                      Number(
                        value,
                      ),
                    )
                  }
                  tick={{
                    fill:
                      "rgba(255,255,255,0.25)",
                    fontSize: 8,
                  }}
                  axisLine={false}
                  tickLine={false}
                />

                <Tooltip
                  labelFormatter={(
                    value,
                  ) =>
                    periodLabel(
                      String(
                        value,
                      ),
                    )
                  }
                  contentStyle={{
                    background:
                      "rgba(4,10,8,0.96)",
                    border:
                      "1px solid rgba(255,255,255,0.08)",
                    borderRadius:
                      "12px",
                    fontSize:
                      "10px",
                  }}
                  labelStyle={{
                    color:
                      "rgba(255,255,255,0.5)",
                  }}
                />

                <Area
                  type="monotone"
                  dataKey="demand_mwh"
                  name="Demand"
                  stroke="#6ee7b7"
                  strokeWidth={2}
                  fill="url(#regionalDemandFill)"
                  dot={false}
                  activeDot={{
                    r: 4,
                  }}
                />

                <Line
                  type="monotone"
                  dataKey="demand_forecast_mwh"
                  name="Forecast"
                  stroke="#7dd3fc"
                  strokeWidth={1.3}
                  strokeDasharray="5 5"
                  dot={false}
                  connectNulls
                />

                <Line
                  type="monotone"
                  dataKey="demand_baseline_mwh"
                  name="Historical baseline"
                  stroke="rgba(255,255,255,0.35)"
                  strokeWidth={1}
                  dot={false}
                  connectNulls
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="flex flex-wrap gap-5 border-t border-white/[0.05] px-5 py-3 text-[7px] uppercase tracking-[0.12em] text-white/20 lg:px-6">
            <span className="flex items-center gap-2">
              <span className="h-px w-5 bg-emerald-300" />
              Demand
            </span>

            <span className="flex items-center gap-2">
              <span className="h-px w-5 bg-sky-300" />
              Forecast
            </span>

            <span className="flex items-center gap-2">
              <span className="h-px w-5 bg-white/30" />
              Historical baseline
            </span>
          </div>
        </>
      )}
    </section>
  );
}
