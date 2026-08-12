"use client";

import {
  Activity,
  CloudSun,
  PlugZap,
} from "lucide-react";
import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type {
  EVCity,
  GridAuthority,
  WeatherForecast,
} from "@/lib/api";

type AnalyticsTab =
  | "grid"
  | "weather"
  | "ev";

interface AnalyticsExplorerProps {
  authorities: GridAuthority[];
  weather: WeatherForecast[];
  evCities: EVCity[];
}

function formatNumber(
  value: number,
): string {
  return new Intl.NumberFormat(
    "en-US",
    {
      maximumFractionDigits: 1,
    },
  ).format(value);
}

function weatherLabel(
  periodStart: string,
): string {
  return new Date(
    periodStart,
  ).toLocaleTimeString(
    "en-US",
    {
      hour: "numeric",
      minute: "2-digit",
    },
  );
}

const tooltipStyle = {
  backgroundColor:
    "rgba(5, 10, 9, 0.96)",
  border:
    "1px solid rgba(255,255,255,0.10)",
  borderRadius: "12px",
  fontSize: "11px",
};

export default function AnalyticsExplorer({
  authorities,
  weather,
  evCities,
}: AnalyticsExplorerProps) {
  const [
    activeTab,
    setActiveTab,
  ] = useState<AnalyticsTab>("grid");

  const gridData = authorities.map(
    (authority) => ({
      authority:
        authority.respondent,
      peakDemand:
        authority.peak_demand_mwh ??
        0,
      forecastError:
        authority.mean_abs_forecast_error_pct ??
        0,
    }),
  );

  const weatherData = weather.map(
    (forecast) => ({
      time: weatherLabel(
        forecast.period_start,
      ),
      temperature:
        forecast.temperature_f ??
        0,
      precipitation:
        forecast.precipitation_probability ??
        0,
    }),
  );

  const evData = evCities.map(
    (city) => ({
      city: city.city,
      ports:
        city.total_known_ports,
      stations:
        city.station_count,
    }),
  );

  const tabs = [
    {
      key: "grid" as const,
      label: "Grid",
      icon: Activity,
    },
    {
      key: "weather" as const,
      label: "Weather",
      icon: CloudSun,
    },
    {
      key: "ev" as const,
      label: "EV Network",
      icon: PlugZap,
    },
  ];

  return (
    <section className="mt-5 overflow-hidden rounded-[18px] border border-white/[0.08] bg-[rgba(8,13,12,0.72)] backdrop-blur-xl">
      <div className="flex flex-col gap-5 border-b border-white/[0.06] px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-emerald-200">
            LIVE ANALYTICS
          </p>

          <h2 className="mt-2 text-lg font-medium text-white">
            GridPulse intelligence explorer
          </h2>

          <p className="mt-1 text-xs text-white/35">
            Explore the analytical marts
            produced by the GridPulse
            pipeline.
          </p>
        </div>

        <div className="flex w-fit rounded-xl border border-white/[0.07] bg-black/25 p-1">
          {tabs.map(
            ({
              key,
              label,
              icon: Icon,
            }) => (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setActiveTab(
                    key,
                  );
                }}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-[10px] font-medium uppercase tracking-[0.12em] transition ${
                  activeTab === key
                    ? "bg-emerald-300/[0.10] text-emerald-200"
                    : "text-white/35 hover:text-white/70"
                }`}
              >
                <Icon
                  size={13}
                />

                {label}
              </button>
            ),
          )}
        </div>
      </div>

      <div className="grid gap-5 p-5 xl:grid-cols-[1fr_260px]">
        <div className="min-h-[380px] rounded-2xl border border-white/[0.06] bg-black/20 p-4">
          {activeTab ===
            "grid" && (
            <>
              <div className="mb-5">
                <p className="text-xs font-medium text-white/80">
                  Peak demand vs.
                  forecast error
                </p>

                <p className="mt-1 text-[10px] text-white/30">
                  Balancing authority
                  comparison
                </p>
              </div>

              <div className="h-[310px]">
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <ComposedChart
                    data={
                      gridData
                    }
                    margin={{
                      top: 10,
                      right: 10,
                      left: 0,
                      bottom: 0,
                    }}
                  >
                    <CartesianGrid
                      stroke="rgba(255,255,255,0.05)"
                      vertical={
                        false
                      }
                    />

                    <XAxis
                      dataKey="authority"
                      tick={{
                        fill:
                          "rgba(255,255,255,0.35)",
                        fontSize: 10,
                      }}
                      axisLine={
                        false
                      }
                      tickLine={
                        false
                      }
                    />

                    <YAxis
                      yAxisId="left"
                      tick={{
                        fill:
                          "rgba(255,255,255,0.3)",
                        fontSize: 9,
                      }}
                      axisLine={
                        false
                      }
                      tickLine={
                        false
                      }
                      width={48}
                    />

                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{
                        fill:
                          "rgba(255,255,255,0.3)",
                        fontSize: 9,
                      }}
                      axisLine={
                        false
                      }
                      tickLine={
                        false
                      }
                      unit="%"
                      width={40}
                    />

                    <Tooltip
                      contentStyle={
                        tooltipStyle
                      }
                      labelStyle={{
                        color:
                          "#ffffff",
                      }}
                      itemStyle={{
                        color:
                          "#b8fbe7",
                      }}
                    />

                    <Bar
                      yAxisId="left"
                      dataKey="peakDemand"
                      name="Peak demand MWh"
                      fill="#63f5c8"
                      fillOpacity={
                        0.55
                      }
                      radius={[
                        5,
                        5,
                        0,
                        0,
                      ]}
                    />

                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="forecastError"
                      name="Forecast error %"
                      stroke="#8bdcff"
                      strokeWidth={2}
                      dot={{
                        fill:
                          "#8bdcff",
                        r: 3,
                      }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {activeTab ===
            "weather" && (
            <>
              <div className="mb-5">
                <p className="text-xs font-medium text-white/80">
                  Temperature and
                  precipitation
                </p>

                <p className="mt-1 text-[10px] text-white/30">
                  Hourly NWS forecast
                  signal
                </p>
              </div>

              <div className="h-[310px]">
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <AreaChart
                    data={
                      weatherData
                    }
                    margin={{
                      top: 10,
                      right: 10,
                      left: 0,
                      bottom: 0,
                    }}
                  >
                    <defs>
                      <linearGradient
                        id="temperatureFill"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor="#8bdcff"
                          stopOpacity={
                            0.32
                          }
                        />

                        <stop
                          offset="100%"
                          stopColor="#8bdcff"
                          stopOpacity={
                            0
                          }
                        />
                      </linearGradient>
                    </defs>

                    <CartesianGrid
                      stroke="rgba(255,255,255,0.05)"
                      vertical={
                        false
                      }
                    />

                    <XAxis
                      dataKey="time"
                      tick={{
                        fill:
                          "rgba(255,255,255,0.35)",
                        fontSize: 9,
                      }}
                      axisLine={
                        false
                      }
                      tickLine={
                        false
                      }
                    />

                    <YAxis
                      yAxisId="temperature"
                      tick={{
                        fill:
                          "rgba(255,255,255,0.3)",
                        fontSize: 9,
                      }}
                      axisLine={
                        false
                      }
                      tickLine={
                        false
                      }
                      unit="°"
                      width={38}
                    />

                    <YAxis
                      yAxisId="precipitation"
                      orientation="right"
                      domain={[
                        0,
                        100,
                      ]}
                      tick={{
                        fill:
                          "rgba(255,255,255,0.3)",
                        fontSize: 9,
                      }}
                      axisLine={
                        false
                      }
                      tickLine={
                        false
                      }
                      unit="%"
                      width={38}
                    />

                    <Tooltip
                      contentStyle={
                        tooltipStyle
                      }
                      labelStyle={{
                        color:
                          "#ffffff",
                      }}
                    />

                    <Area
                      yAxisId="temperature"
                      type="monotone"
                      dataKey="temperature"
                      name="Temperature °F"
                      stroke="#8bdcff"
                      strokeWidth={2}
                      fill="url(#temperatureFill)"
                    />

                    <Line
                      yAxisId="precipitation"
                      type="monotone"
                      dataKey="precipitation"
                      name="Precipitation %"
                      stroke="#63f5c8"
                      strokeWidth={2}
                      dot={{
                        r: 3,
                        fill:
                          "#63f5c8",
                      }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {activeTab ===
            "ev" && (
            <>
              <div className="mb-5">
                <p className="text-xs font-medium text-white/80">
                  Charging capacity by
                  city
                </p>

                <p className="mt-1 text-[10px] text-white/30">
                  AFDC city-level
                  infrastructure
                </p>
              </div>

              <div className="h-[310px]">
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <BarChart
                    data={evData}
                    margin={{
                      top: 10,
                      right: 10,
                      left: 0,
                      bottom: 0,
                    }}
                  >
                    <CartesianGrid
                      stroke="rgba(255,255,255,0.05)"
                      vertical={
                        false
                      }
                    />

                    <XAxis
                      dataKey="city"
                      tick={{
                        fill:
                          "rgba(255,255,255,0.35)",
                        fontSize: 9,
                      }}
                      axisLine={
                        false
                      }
                      tickLine={
                        false
                      }
                    />

                    <YAxis
                      tick={{
                        fill:
                          "rgba(255,255,255,0.3)",
                        fontSize: 9,
                      }}
                      axisLine={
                        false
                      }
                      tickLine={
                        false
                      }
                      width={35}
                    />

                    <Tooltip
                      contentStyle={
                        tooltipStyle
                      }
                      labelStyle={{
                        color:
                          "#ffffff",
                      }}
                    />

                    <Bar
                      dataKey="ports"
                      name="Charging ports"
                      fill="#d5f77d"
                      fillOpacity={
                        0.65
                      }
                      radius={[
                        5,
                        5,
                        0,
                        0,
                      ]}
                    />

                    <Bar
                      dataKey="stations"
                      name="Stations"
                      fill="#63f5c8"
                      fillOpacity={
                        0.45
                      }
                      radius={[
                        5,
                        5,
                        0,
                        0,
                      ]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>

        <aside className="rounded-2xl border border-white/[0.06] bg-white/[0.018] p-5">
          <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-white/30">
            DATA LAYER
          </p>

          <p className="mt-3 text-xl font-medium text-white">
            {activeTab ===
              "grid" &&
              "EIA"}

            {activeTab ===
              "weather" &&
              "NWS"}

            {activeTab ===
              "ev" &&
              "AFDC"}
          </p>

          <div className="mt-7 space-y-3">
            <div className="rounded-xl border border-white/[0.06] bg-black/20 p-4">
              <p className="text-[8px] uppercase tracking-[0.14em] text-white/25">
                Records
              </p>

              <p className="mt-2 text-2xl font-light text-white">
                {activeTab ===
                  "grid" &&
                  authorities.length}

                {activeTab ===
                  "weather" &&
                  weather.length}

                {activeTab ===
                  "ev" &&
                  evCities.length}
              </p>
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-black/20 p-4">
              <p className="text-[8px] uppercase tracking-[0.14em] text-white/25">
                Pipeline
              </p>

              <p className="mt-2 text-xs leading-5 text-white/55">
                Bronze
                <span className="mx-2 text-emerald-200">
                  →
                </span>
                Silver
                <span className="mx-2 text-emerald-200">
                  →
                </span>
                Gold
              </p>
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-black/20 p-4">
              <p className="text-[8px] uppercase tracking-[0.14em] text-white/25">
                Serving
              </p>

              <p className="mt-2 text-xs text-white/55">
                dbt → DuckDB →
                FastAPI
              </p>
            </div>
          </div>

          <div className="mt-7 border-t border-white/[0.06] pt-5">
            <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.14em] text-emerald-200">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-200 shadow-[0_0_10px_rgba(99,245,200,0.8)]" />
              Live warehouse
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
