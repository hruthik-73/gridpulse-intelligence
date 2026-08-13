"use client";

import type {
  GridAnomaly,
  GridRiskSeverity,
} from "@/lib/api";


interface GridRiskPanelProps {
  anomalies: GridAnomaly[];
}


function severityClasses(
  severity: GridRiskSeverity,
) {
  switch (severity) {
    case "CRITICAL":
      return {
        dot: "bg-rose-400 shadow-[0_0_16px_rgba(251,113,133,0.8)]",
        text: "text-rose-300",
        border:
          "border-rose-400/20",
        background:
          "bg-rose-400/[0.045]",
      };

    case "HIGH":
      return {
        dot: "bg-orange-300 shadow-[0_0_16px_rgba(253,186,116,0.7)]",
        text: "text-orange-200",
        border:
          "border-orange-300/20",
        background:
          "bg-orange-300/[0.04]",
      };

    case "ELEVATED":
      return {
        dot: "bg-amber-300 shadow-[0_0_14px_rgba(252,211,77,0.65)]",
        text: "text-amber-200",
        border:
          "border-amber-300/15",
        background:
          "bg-amber-300/[0.035]",
      };

    case "NORMAL":
    default:
      return {
        dot: "bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.65)]",
        text: "text-emerald-200",
        border:
          "border-emerald-300/15",
        background:
          "bg-emerald-300/[0.025]",
      };
  }
}


function formatNumber(
  value: number | null,
  digits = 1,
): string {
  if (value === null) {
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
  value: number | null,
): string {
  if (value === null) {
    return "—";
  }

  return `${formatNumber(
    Math.abs(value),
    1,
  )}%`;
}


function severityCount(
  anomalies: GridAnomaly[],
  severity: GridRiskSeverity,
): number {
  return anomalies.filter(
    (anomaly) =>
      anomaly.severity === severity,
  ).length;
}


function BaselineMetric({
  label,
  current,
  baseline,
  deviation,
}: {
  label: string;
  current: number | null;
  baseline: number | null;
  deviation: number;
}) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-black/20 p-3">
      <p className="text-[8px] uppercase tracking-[0.14em] text-white/25">
        {label}
      </p>

      <div className="mt-3 grid grid-cols-3 gap-3">
        <div>
          <p className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Current
          </p>

          <p className="mt-1 text-xs text-white/70">
            {formatPercent(
              current,
            )}
          </p>
        </div>

        <div>
          <p className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Baseline
          </p>

          <p className="mt-1 text-xs text-white/50">
            {formatPercent(
              baseline,
            )}
          </p>
        </div>

        <div>
          <p className="text-[7px] uppercase tracking-[0.12em] text-white/20">
            Robust z
          </p>

          <p className="mt-1 text-xs text-emerald-200">
            {formatNumber(
              deviation,
              2,
            )}
          </p>
        </div>
      </div>
    </div>
  );
}


function RiskGauge({
  score,
  severity,
}: {
  score: number;
  severity: GridRiskSeverity;
}) {
  const classes =
    severityClasses(severity);

  const safeScore = Math.min(
    100,
    Math.max(
      0,
      score,
    ),
  );

  return (
    <div className="relative flex h-[128px] w-[128px] items-center justify-center">
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
        <div className="text-3xl font-medium tracking-[-0.05em] text-white">
          {formatNumber(
            safeScore,
            1,
          )}
        </div>

        <div className="mt-1 text-[8px] uppercase tracking-[0.18em] text-white/30">
          Risk score
        </div>

        <div
          className={`mt-2 flex items-center justify-center gap-1.5 text-[8px] font-semibold uppercase tracking-[0.14em] ${classes.text}`}
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


function RiskRow({
  anomaly,
  rank,
}: {
  anomaly: GridAnomaly;
  rank: number;
}) {
  const classes =
    severityClasses(
      anomaly.severity,
    );

  return (
    <div
      className={`grid gap-4 rounded-xl border px-4 py-3 md:grid-cols-[38px_1.35fr_0.55fr_0.8fr_0.8fr_0.55fr] md:items-center ${classes.border} ${classes.background}`}
    >
      <div className="text-[10px] font-medium text-white/25">
        {String(
          rank,
        ).padStart(
          2,
          "0",
        )}
      </div>

      <div>
        <div className="flex items-center gap-2">
          <span
            className={`h-1.5 w-1.5 rounded-full ${classes.dot}`}
          />

          <p className="text-xs font-medium text-white/80">
            {anomaly.respondent}
          </p>

          <span
            className={`text-[8px] font-semibold uppercase tracking-[0.13em] ${classes.text}`}
          >
            {anomaly.severity}
          </span>
        </div>

        <p className="mt-1 truncate text-[9px] text-white/30">
          {anomaly.respondent_name}
        </p>
      </div>

      <div>
        <p className="text-[8px] uppercase tracking-[0.13em] text-white/25">
          Risk
        </p>

        <p className="mt-1 text-sm font-medium text-white">
          {formatNumber(
            anomaly.risk_score,
            1,
          )}
        </p>
      </div>

      <div>
        <p className="text-[8px] uppercase tracking-[0.13em] text-white/25">
          Forecast
        </p>

        <p className="mt-1 text-xs text-white/65">
          {formatPercent(
            anomaly.forecast_error_pct,
          )}
        </p>

        <p className="mt-1 text-[7px] text-white/25">
          baseline{" "}
          {formatPercent(
            anomaly.forecast_baseline_pct,
          )}
        </p>
      </div>

      <div>
        <p className="text-[8px] uppercase tracking-[0.13em] text-white/25">
          Generation
        </p>

        <p className="mt-1 text-xs text-white/65">
          {formatPercent(
            anomaly.generation_gap_pct,
          )}
        </p>

        <p className="mt-1 text-[7px] text-white/25">
          baseline{" "}
          {formatPercent(
            anomaly.generation_baseline_pct,
          )}
        </p>
      </div>

      <div>
        <p className="text-[8px] uppercase tracking-[0.13em] text-white/25">
          History
        </p>

        <p className="mt-1 text-xs text-white/60">
          {anomaly.history_points}
        </p>
      </div>
    </div>
  );
}


export default function GridRiskPanel({
  anomalies,
}: GridRiskPanelProps) {
  if (anomalies.length === 0) {
    return (
      <section className="mt-5 rounded-2xl border border-white/[0.07] bg-white/[0.015] p-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-200">
          Historical Grid Risk
        </p>

        <p className="mt-3 text-sm text-white/35">
          Historical anomaly
          intelligence is currently
          unavailable.
        </p>
      </section>
    );
  }

  const topRisk =
    anomalies[0];

  const critical =
    severityCount(
      anomalies,
      "CRITICAL",
    );

  const high =
    severityCount(
      anomalies,
      "HIGH",
    );

  const elevated =
    severityCount(
      anomalies,
      "ELEVATED",
    );

  const normal =
    severityCount(
      anomalies,
      "NORMAL",
    );

  const displayed =
    anomalies.slice(
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
                Explainable Grid Risk
              </p>

              <h2 className="mt-2 text-2xl font-medium tracking-[-0.035em] text-white">
                Historical anomaly
                intelligence
              </h2>

              <p className="mt-2 max-w-[680px] text-xs leading-5 text-white/35">
                GridPulse compares
                each authority&apos;s
                latest observation
                with its own
                historical baseline,
                then exposes the
                signals responsible
                for the resulting risk
                score.
              </p>
            </div>

            <div className="flex items-center gap-2 rounded-full border border-emerald-300/10 bg-emerald-300/[0.03] px-3 py-2 text-[8px] uppercase tracking-[0.16em] text-emerald-200">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.7)]" />

              Explainability active
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-4">
            {[
              [
                "Critical",
                critical,
                "text-rose-200",
              ],
              [
                "High",
                high,
                "text-orange-200",
              ],
              [
                "Elevated",
                elevated,
                "text-amber-200",
              ],
              [
                "Normal",
                normal,
                "text-emerald-200",
              ],
            ].map(
              ([
                label,
                value,
                valueClass,
              ]) => (
                <div
                  key={label}
                  className="rounded-xl border border-white/[0.06] bg-black/15 px-4 py-3"
                >
                  <p className="text-[8px] uppercase tracking-[0.14em] text-white/25">
                    {label}
                  </p>

                  <p
                    className={`mt-2 text-2xl font-medium ${valueClass}`}
                  >
                    {value}
                  </p>
                </div>
              ),
            )}
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.05] bg-black/20 p-5">
          <div className="flex items-center gap-5">
            <RiskGauge
              score={
                topRisk.risk_score
              }
              severity={
                topRisk.severity
              }
            />

            <div className="min-w-0">
              <p className="text-[8px] uppercase tracking-[0.15em] text-white/25">
                Strongest deviation
              </p>

              <p className="mt-2 text-lg font-medium text-white">
                {topRisk.respondent}
              </p>

              <p className="mt-1 truncate text-[9px] text-white/30">
                {
                  topRisk.respondent_name
                }
              </p>

              <p className="mt-3 text-[8px] uppercase tracking-[0.12em] text-white/25">
                {
                  topRisk.history_points
                }{" "}
                historical observations
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-2">
            <BaselineMetric
              label="Forecast error"
              current={
                topRisk.forecast_error_pct
              }
              baseline={
                topRisk.forecast_baseline_pct
              }
              deviation={
                topRisk.forecast_deviation_score
              }
            />

            <BaselineMetric
              label="Generation-demand gap"
              current={
                topRisk.generation_gap_pct
              }
              baseline={
                topRisk.generation_baseline_pct
              }
              deviation={
                topRisk.generation_deviation_score
              }
            />
          </div>
        </div>
      </div>

      <div className="p-5 lg:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-[8px] uppercase tracking-[0.17em] text-white/25">
              Explainable ranking
            </p>

            <p className="mt-1 text-xs text-white/45">
              Current signal versus
              historical baseline
            </p>
          </div>

          <p className="text-[8px] uppercase tracking-[0.14em] text-white/20">
            Risk 0–100
          </p>
        </div>

        <div className="space-y-2">
          {displayed.map(
            (
              anomaly,
              index,
            ) => (
              <RiskRow
                key={`${anomaly.respondent}-${anomaly.period}`}
                anomaly={
                  anomaly
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
        GridPulse uses each
        authority&apos;s historical
        median and robust deviation
        behavior to explain the latest
        anomaly score. Risk signals are
        analytical indicators and are
        not official reliability or
        outage declarations.
      </div>
    </section>
  );
}
