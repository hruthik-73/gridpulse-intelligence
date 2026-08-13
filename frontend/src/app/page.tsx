import AnalyticsExplorer from "@/components/AnalyticsExplorer";
import DataFreshnessPanel from "@/components/DataFreshnessPanel";
import GridCore from "@/components/GridCore";
import GridRiskPanel from "@/components/GridRiskPanel";
import NationalCommandCenter from "@/components/NationalCommandCenter";
import OperationalIncidentPanel from "@/components/OperationalIncidentPanel";
import PlatformHealthPanel from "@/components/PlatformHealthPanel";
import PipelineLineagePanel from "@/components/PipelineLineagePanel";
import PipelineRunsPanel from "@/components/PipelineRunsPanel";
import DataQualityPanel from "@/components/DataQualityPanel";
import RegionalGridExperience from "@/components/RegionalGridExperience";
import RegionalGridPanel from "@/components/RegionalGridPanel";

import {
  getEVCities,
  getGridAnomalies,
  getGridAuthorities,
  getPlatformHealth,
  getPlatformStatus,
  getRegionalGridSignals,
  getWeather,
} from "@/lib/api";

import type {
  EVCity,
  GridAnomaly,
  GridAuthority,
  PlatformHealth,
  PlatformStatus,
  RegionalGridSignal,
  WeatherForecast,
} from "@/lib/api";


export const dynamic =
  "force-dynamic";


interface DashboardData {
  status: PlatformStatus | null;
  health: PlatformHealth | null;

  authorities: GridAuthority[];
  anomalies: GridAnomaly[];
  regions: RegionalGridSignal[];
  evCities: EVCity[];
  weather: WeatherForecast[];

  apiAvailable: boolean;
}


async function getDashboardData(): Promise<DashboardData> {
  try {
    const [
      status,
      authorities,
      evCities,
      weather,
    ] = await Promise.all([
      getPlatformStatus(),
      getGridAuthorities(10),
      getEVCities("OH", 10),
      getWeather(12),
    ]);

    let health:
      | PlatformHealth
      | null = null;

    let anomalies:
      GridAnomaly[] = [];

    let regions:
      RegionalGridSignal[] = [];

    try {
      health =
        await getPlatformHealth();
    } catch {
      health = null;
    }

    try {
      anomalies =
        await getGridAnomalies(
          20,
        );
    } catch {
      anomalies = [];
    }

    try {
      regions =
        await getRegionalGridSignals(
          20,
        );
    } catch {
      regions = [];
    }

    return {
      status,
      health,
      authorities,
      anomalies,
      regions,
      evCities,
      weather,
      apiAvailable: true,
    };
  } catch {
    return {
      status: null,
      health: null,
      authorities: [],
      anomalies: [],
      regions: [],
      evCities: [],
      weather: [],
      apiAvailable: false,
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


export default async function Home() {
  const {
    status,
    health,
    authorities,
    anomalies,
    regions,
    evCities,
    weather,
    apiAvailable,
  } = await getDashboardData();

  const currentWeather =
    weather[0];

  const topAuthority =
    authorities[0];

  const topEvCity =
    evCities[0];

  const topRisk =
    anomalies[0] ?? null;

  const topRegion =
    regions[0] ?? null;

  const platformLabel =
    !apiAvailable
      ? "API unavailable"
      : health
        ? `Platform ${health.status}`
        : "API online";

  const platformDotClass =
    !apiAvailable ||
    health?.status ===
      "unhealthy"
      ? "status-dot status-dot-offline"
      : health?.status ===
          "degraded"
        ? "h-[6px] w-[6px] rounded-full bg-amber-300 shadow-[0_0_12px_rgba(252,211,77,0.7)]"
        : "status-dot";

  const metrics = [
    {
      label:
        "Grid observations",
      value: status
        ? formatNumber(
            status.grid_hourly_rows,
          )
        : "—",
      detail:
        "Gold hourly records",
    },
    {
      label:
        "Authorities",
      value: status
        ? formatNumber(
            status.balancing_authorities,
          )
        : "—",
      detail:
        "Balancing authorities",
    },
    {
      label:
        "EV markets",
      value: status
        ? formatNumber(
            status.ev_cities,
          )
        : "—",
      detail:
        "City infrastructure marts",
    },
    {
      label:
        "Weather signals",
      value: status
        ? formatNumber(
            status.weather_forecasts,
          )
        : "—",
      detail:
        "Hourly forecast windows",
    },
  ];

  return (
    <main className="min-h-screen overflow-hidden">
      <div className="grid-shell" />

      <section className="relative mx-auto max-w-[1500px] px-5 pb-20 pt-6 md:px-10">
        <header className="glass-panel flex items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="brand-mark">
              <span />
            </div>

            <div>
              <p className="text-sm font-semibold tracking-[0.18em] text-white">
                GRIDPULSE
              </p>

              <p className="text-[10px] uppercase tracking-[0.28em] text-white/35">
                Intelligence Platform
              </p>
            </div>
          </div>

          <div className="hidden items-center gap-7 text-xs text-white/45 md:flex">
            <span>
              <a
                href="#grid-map"
                className="transition-colors duration-200 hover:text-emerald-200"
              >
                Grid
              </a>
            </span>

            <span>
              <a
                href="#analytics-explorer"
                className="transition-colors duration-200 hover:text-emerald-200"

            data-analytics-tab="weather">
                Weather
              </a>
            </span>

            <span>
              <a
                href="#analytics-explorer"
                className="transition-colors duration-200 hover:text-emerald-200"

            data-analytics-tab="ev">
                EV Infrastructure
              </a>
            </span>

            <span>
              <a
                href="#platform-health"
                className="transition-colors duration-200 hover:text-emerald-200"
              >
                Observability
              </a>
            </span>
          </div>

          <div className="status-pill">
            <span
              className={
                platformDotClass
              }
            />

            {platformLabel}
          </div>
        </header>

        <section className="grid min-h-[620px] items-center gap-8 py-8 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="relative z-10">
            <div className="eyebrow">
              LIVE ENERGY DATA SYSTEM
            </div>

            <h1 className="mt-6 max-w-[760px] font-semibold leading-[0.98] tracking-[-0.055em] text-white">
              <span className="block text-5xl sm:text-6xl lg:text-[64px] xl:text-[76px]">
                Intelligence for a
              </span>

              <span className="hero-gradient mt-1 block text-5xl sm:text-6xl lg:text-[64px] xl:text-[76px]">
                changing grid.
              </span>
            </h1>

            <p className="mt-7 max-w-[620px] text-base leading-8 text-white/50 md:text-lg">
              A real-time data
              engineering platform
              connecting electricity
              demand, weather signals,
              EV charging
              infrastructure,
              streaming pipelines,
              analytics, and
              observability.
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              {[
                "Kafka",
                "Spark",
                "dbt",
                "DuckDB",
                "FastAPI",
                "Prometheus",
              ].map(
                (technology) => (
                  <div
                    key={
                      technology
                    }
                    className="tech-chip"
                  >
                    {technology}
                  </div>
                ),
              )}
            </div>

            <div className="mt-10 flex items-center gap-5 text-xs uppercase tracking-[0.18em] text-white/35">
              <span className="h-px w-14 bg-white/15" />

              Public energy
              intelligence
            </div>
          </div>

          <div className="relative flex min-h-[560px] items-center justify-center">
            <GridCore
              gridObservations={
                status?.grid_hourly_rows ??
                0
              }
              balancingAuthorities={
                status?.balancing_authorities ??
                0
              }
              evMarkets={
                status?.ev_cities ??
                0
              }
              weatherSignals={
                status?.weather_forecasts ??
                0
              }
              topAuthority={
                topAuthority
                  ?.respondent_name ??
                topAuthority
                  ?.respondent ??
                null
              }
              topAuthorityPeakDemand={
                topAuthority
                  ?.peak_demand_mwh ??
                null
              }
              currentTemperatureF={
                currentWeather
                  ?.temperature_f ??
                null
              }
              precipitationProbability={
                currentWeather
                  ?.precipitation_probability ??
                null
              }
              currentForecast={
                currentWeather
                  ?.short_forecast ??
                null
              }
              topEvCity={
                topEvCity?.city ??
                null
              }
              topEvStationCount={
                topEvCity
                  ?.station_count ??
                null
              }
              topEvPortCount={
                topEvCity
                  ?.total_known_ports ??
                null
              }
            />
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map(
            (metric) => (
              <article
                key={
                  metric.label
                }
                className="metric-card"
              >
                <div className="metric-line" />

                <p className="text-xs uppercase tracking-[0.18em] text-white/35">
                  {metric.label}
                </p>

                <p className="mt-5 text-4xl font-medium tracking-[-0.04em] text-white">
                  {metric.value}
                </p>

                <p className="mt-2 text-xs text-white/35">
                  {metric.detail}
                </p>
              </article>
            ),
          )}
        </section>

        <NationalCommandCenter
          topRisk={topRisk}
          topRegion={topRegion}
          weather={
            currentWeather ??
            null
          }
          topEvCity={
            topEvCity ??
            null
          }
          health={health}
        />


        <div
          id="grid-map"
          className="scroll-mt-6"
        >
          <RegionalGridExperience
            regions={regions}
          />
        </div>


        <div
          id="grid-risk"
          className="scroll-mt-6"
        >
          <GridRiskPanel
            anomalies={
              anomalies
            }
          />
        </div>


        <div
          id="regional-grid"
          className="scroll-mt-6"
        >
          <RegionalGridPanel
            regions={
              regions
            }
          />
        </div>


        <div
          id="analytics-explorer"
          className="scroll-mt-6"
        >
          <AnalyticsExplorer
            authorities={
              authorities
            }
            weather={
              weather
            }
            evCities={
              evCities
            }
          />
        </div>


        {health?.runtime_mode ===
          "portfolio" && (
          <section className="mt-5 rounded-[18px] border border-sky-300/[0.10] bg-sky-300/[0.025] px-6 py-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-sky-200/80">
              PUBLIC PORTFOLIO MODE
            </p>

            <p className="mt-2 max-w-4xl text-xs leading-5 text-white/35">
              Operational intelligence below
              uses retained, sanitized evidence
              captured from the validated local
              GridPulse pipeline. Kafka, Spark,
              Prometheus, and the consumer are
              not presented as continuously
              running public cloud services.
            </p>
          </section>
        )}


        <div
          id="platform-health"
          className="scroll-mt-6"
        >
          <PlatformHealthPanel
            health={health}
          />
        </div>


        <DataFreshnessPanel />


        <OperationalIncidentPanel />


        <PipelineLineagePanel />


        <PipelineRunsPanel />


        <DataQualityPanel />


        <footer className="mt-6 flex flex-col justify-between gap-3 px-2 py-5 text-[10px] uppercase tracking-[0.18em] text-white/20 sm:flex-row">
          <span>
            GridPulse Intelligence
          </span>

          <span>
            Streaming · Analytics ·
            Energy
          </span>

          <span>
            2026
          </span>
        </footer>
      </section>

</main>
  );
}
