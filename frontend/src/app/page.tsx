import GridCore from "@/components/GridCore";
import {
  EVCity,
  getEVCities,
  getGridAuthorities,
  getPlatformStatus,
  getWeather,
  GridAuthority,
  PlatformStatus,
  WeatherForecast,
} from "@/lib/api";

export const dynamic = "force-dynamic";

interface DashboardData {
  status: PlatformStatus | null;
  authorities: GridAuthority[];
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
      getGridAuthorities(6),
      getEVCities("OH", 6),
      getWeather(6),
    ]);

    return {
      status,
      authorities,
      evCities,
      weather,
      apiAvailable: true,
    };
  } catch {
    return {
      status: null,
      authorities: [],
      evCities: [],
      weather: [],
      apiAvailable: false,
    };
  }
}

function formatNumber(
  value: number | null | undefined,
  digits = 0,
): string {
  if (value === null || value === undefined) {
    return "—";
  }

  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
  }).format(value);
}

function formatPercent(
  value: number | null | undefined,
): string {
  if (value === null || value === undefined) {
    return "—";
  }

  return `${formatNumber(value, 1)}%`;
}

export default async function Home() {
  const {
    status,
    authorities,
    evCities,
    weather,
    apiAvailable,
  } = await getDashboardData();

  const currentWeather = weather[0];

  const metrics = [
    {
      label: "Grid observations",
      value: status
        ? formatNumber(status.grid_hourly_rows)
        : "—",
      detail: "Gold hourly records",
    },
    {
      label: "Authorities",
      value: status
        ? formatNumber(status.balancing_authorities)
        : "—",
      detail: "Balancing regions",
    },
    {
      label: "EV markets",
      value: status
        ? formatNumber(status.ev_cities)
        : "—",
      detail: "City infrastructure marts",
    },
    {
      label: "Weather signals",
      value: status
        ? formatNumber(status.weather_forecasts)
        : "—",
      detail: "Hourly forecast windows",
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
            <span>Grid</span>
            <span>Weather</span>
            <span>EV Infrastructure</span>
            <span>Observability</span>
          </div>

          <div className="status-pill">
            <span
              className={
                apiAvailable
                  ? "status-dot"
                  : "status-dot status-dot-offline"
              }
            />

            {apiAvailable
              ? "Platform online"
              : "API unavailable"}
          </div>
        </header>

        <section className="grid min-h-[620px] items-center gap-8 py-10 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="relative z-10">
            <div className="eyebrow">
              LIVE ENERGY DATA SYSTEM
            </div>

            <h1 className="mt-6 max-w-4xl text-5xl font-semibold leading-[0.98] tracking-[-0.055em] text-white sm:text-6xl lg:text-7xl xl:text-[88px]">
              Intelligence for a
              <span className="hero-gradient block">
                changing grid.
              </span>
            </h1>

            <p className="mt-7 max-w-2xl text-base leading-8 text-white/50 md:text-lg">
              A real-time data engineering platform connecting
              electricity demand, weather signals, EV charging
              infrastructure, streaming pipelines, analytics, and
              observability.
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              <div className="tech-chip">
                Kafka
              </div>

              <div className="tech-chip">
                Spark
              </div>

              <div className="tech-chip">
                dbt
              </div>

              <div className="tech-chip">
                DuckDB
              </div>

              <div className="tech-chip">
                FastAPI
              </div>

              <div className="tech-chip">
                Prometheus
              </div>
            </div>

            <div className="mt-10 flex items-center gap-5 text-xs uppercase tracking-[0.18em] text-white/35">
              <span className="h-px w-14 bg-white/15" />
              Public energy intelligence
            </div>
          </div>

          <div className="hero-visual">
            <div className="hero-orbit hero-orbit-one" />
            <div className="hero-orbit hero-orbit-two" />
            <div className="hero-orbit hero-orbit-three" />

            <GridCore />

            <div className="floating-node floating-node-one">
              <span>STREAM</span>
              Kafka online
            </div>

            <div className="floating-node floating-node-two">
              <span>MODEL</span>
              Gold marts
            </div>

            <div className="floating-node floating-node-three">
              <span>SERVE</span>
              FastAPI
            </div>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <article
              key={metric.label}
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
          ))}
        </section>

        <section className="mt-5 grid gap-5 xl:grid-cols-[1.45fr_0.55fr]">
          <article className="glass-panel overflow-hidden">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">
                  GRID INTELLIGENCE
                </p>

                <h2 className="panel-title">
                  Balancing authority performance
                </h2>
              </div>

              <span className="live-badge">
                LIVE MART
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Authority</th>
                    <th>Peak demand</th>
                    <th>Forecast error</th>
                    <th>Coverage</th>
                    <th>Rank</th>
                  </tr>
                </thead>

                <tbody>
                  {authorities.length > 0 ? (
                    authorities.map((authority) => (
                      <tr key={authority.respondent}>
                        <td>
                          <div className="font-medium text-white">
                            {authority.respondent}
                          </div>

                          <div className="mt-1 max-w-[230px] truncate text-[11px] text-white/30">
                            {authority.respondent_name ??
                              "Balancing authority"}
                          </div>
                        </td>

                        <td>
                          {formatNumber(
                            authority.peak_demand_mwh,
                          )}{" "}
                          <span className="text-white/25">
                            MWh
                          </span>
                        </td>

                        <td>
                          {formatPercent(
                            authority.mean_abs_forecast_error_pct,
                          )}
                        </td>

                        <td>
                          {formatPercent(
                            authority.forecast_coverage_pct,
                          )}
                        </td>

                        <td>
                          <span className="rank-token">
                            #
                            {authority.peak_demand_rank}
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td
                        colSpan={5}
                        className="py-12 text-center text-white/35"
                      >
                        Start the FastAPI service to load
                        grid analytics.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <article className="weather-card">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">
                  WEATHER SIGNAL
                </p>

                <h2 className="panel-title">
                  Cleveland forecast
                </h2>
              </div>

              <span className="signal-dot" />
            </div>

            {currentWeather ? (
              <div className="px-6 pb-7">
                <div className="mt-5 flex items-end justify-between">
                  <div>
                    <p className="text-6xl font-light tracking-[-0.07em] text-white">
                      {formatNumber(
                        currentWeather.temperature_f,
                      )}
                      °
                    </p>

                    <p className="mt-3 text-sm text-white/45">
                      {currentWeather.short_forecast}
                    </p>
                  </div>

                  <div className="weather-ring">
                    <span>
                      {formatNumber(
                        currentWeather.precipitation_probability,
                      )}
                      %
                    </span>
                  </div>
                </div>

                <div className="weather-grid mt-8">
                  <div>
                    <span>Humidity</span>
                    <strong>
                      {formatPercent(
                        currentWeather.relative_humidity,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>Wind</span>
                    <strong>
                      {currentWeather.wind_speed ??
                        "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Direction</span>
                    <strong>
                      {currentWeather.wind_direction ??
                        "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Risk</span>
                    <strong className="capitalize">
                      {
                        currentWeather.precipitation_risk
                      }
                    </strong>
                  </div>
                </div>
              </div>
            ) : (
              <div className="px-6 pb-10 pt-8 text-sm text-white/35">
                Weather data unavailable.
              </div>
            )}
          </article>
        </section>

        <section className="mt-5 grid gap-5 lg:grid-cols-[0.75fr_1.25fr]">
          <article className="glass-panel">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">
                  EV INFRASTRUCTURE
                </p>

                <h2 className="panel-title">
                  Ohio charging network
                </h2>
              </div>
            </div>

            <div className="space-y-3 px-5 pb-5">
              {evCities.length > 0 ? (
                evCities.map((city) => (
                  <div
                    key={city.city_state_key}
                    className="ev-row"
                  >
                    <div>
                      <p className="text-sm font-medium text-white">
                        {city.city}
                      </p>

                      <p className="mt-1 text-[11px] text-white/30">
                        {city.station_count} stations
                      </p>
                    </div>

                    <div className="text-right">
                      <p className="text-lg text-white">
                        {formatNumber(
                          city.total_known_ports,
                        )}
                      </p>

                      <p className="text-[10px] uppercase tracking-[0.16em] text-white/25">
                        ports
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="py-10 text-center text-sm text-white/35">
                  EV infrastructure data unavailable.
                </p>
              )}
            </div>
          </article>

          <article className="architecture-panel">
            <div className="panel-header">
              <div>
                <p className="panel-kicker">
                  SYSTEM ARCHITECTURE
                </p>

                <h2 className="panel-title">
                  From public APIs to intelligence
                </h2>
              </div>

              <span className="text-[10px] uppercase tracking-[0.18em] text-white/25">
                GridPulse v0.1
              </span>
            </div>

            <div className="pipeline-track">
              {[
                ["01", "Public APIs", "EIA · NWS · AFDC"],
                ["02", "Kafka", "Event streaming"],
                ["03", "Spark", "Bronze · Silver · Gold"],
                ["04", "dbt", "Analytics marts"],
                ["05", "FastAPI", "Serving layer"],
                ["06", "Next.js", "Intelligence UI"],
              ].map(
                ([number, title, description], index) => (
                  <div
                    key={title}
                    className="pipeline-step"
                  >
                    <span className="pipeline-number">
                      {number}
                    </span>

                    <div>
                      <p className="text-sm font-medium text-white/85">
                        {title}
                      </p>

                      <p className="mt-1 text-[10px] text-white/30">
                        {description}
                      </p>
                    </div>

                    {index < 5 && (
                      <span className="pipeline-connector">
                        →
                      </span>
                    )}
                  </div>
                ),
              )}
            </div>

            <div className="architecture-footer">
              <span>
                DATA QUALITY
              </span>
              <span>
                OBSERVABILITY
              </span>
              <span>
                LINEAGE
              </span>
              <span>
                REPLAY SAFE
              </span>
            </div>
          </article>
        </section>

        <footer className="mt-6 flex flex-col justify-between gap-3 px-2 py-5 text-[10px] uppercase tracking-[0.18em] text-white/20 sm:flex-row">
          <span>
            GridPulse Intelligence
          </span>

          <span>
            Streaming · Analytics · Energy
          </span>

          <span>
            2026
          </span>
        </footer>
      </section>
    </main>
  );
}
