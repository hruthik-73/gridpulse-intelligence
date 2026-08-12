export interface PlatformStatus {
  status: string;
  database: string;
  grid_hourly_rows: number;
  balancing_authorities: number;
  ev_cities: number;
  weather_forecasts: number;
}

export interface GridAuthority {
  respondent: string;
  respondent_name: string | null;
  observed_hours: number;
  demand_hours: number;
  forecast_pair_hours: number;
  generation_pair_hours: number;
  average_demand_mwh: number | null;
  peak_demand_mwh: number | null;
  mean_abs_forecast_error_mwh: number | null;
  mean_abs_forecast_error_pct: number | null;
  average_generation_demand_gap_mwh: number | null;
  forecast_coverage_pct: number | null;
  generation_coverage_pct: number | null;
  forecast_accuracy_rank: number;
  peak_demand_rank: number;
  contains_replay: boolean;
  latest_kafka_timestamp: string | null;
}

export interface EVCity {
  city_state_key: string;
  city: string;
  state: string;
  country: string;
  station_count: number;
  level1_ports: number;
  level2_ports: number;
  dc_fast_ports: number;
  total_known_ports: number;
  dc_fast_station_count: number;
  network_count: number;
  ports_per_station: number | null;
  dc_fast_station_share_pct: number | null;
  state_station_rank: number;
  national_station_rank: number;
  state_port_rank: number;
  latest_station_update: string | null;
}

export interface WeatherForecast {
  weather_forecast_key: string;
  location_key: string;
  latitude: number;
  longitude: number;
  period_start: string;
  period_end: string;
  forecast_hour: number;
  temperature_f: number | null;
  temperature_c: number | null;
  precipitation_probability: number | null;
  precipitation_risk: string;
  relative_humidity: number | null;
  wind_speed: string | null;
  wind_direction: string | null;
  short_forecast: string | null;
  replay: boolean;
  kafka_partition: number;
  kafka_offset: number;
  kafka_timestamp: string | null;
}

export type HealthState =
  | "healthy"
  | "degraded"
  | "unhealthy";

export interface ComponentHealth {
  status: HealthState;
  detail: string;
  latency_ms: number;
}

export interface PlatformHealth {
  status: HealthState;
  warehouse: ComponentHealth;
  kafka: ComponentHealth;
  prometheus: ComponentHealth;
  kafka_consumer: ComponentHealth;
}

const API_URL =
  process.env.NEXT_PUBLIC_GRIDPULSE_API_URL ??
  "http://127.0.0.1:8080";

async function fetchJson<T>(
  path: string,
): Promise<T> {
  const response = await fetch(
    `${API_URL}${path}`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      `GridPulse API request failed: ${response.status}`,
    );
  }

  return response.json() as Promise<T>;
}

export function getPlatformStatus() {
  return fetchJson<PlatformStatus>(
    "/api/v1/status",
  );
}

export function getPlatformHealth() {
  return fetchJson<PlatformHealth>(
    "/api/v1/platform/health",
  );
}

export function getGridAuthorities(
  limit = 10,
) {
  return fetchJson<GridAuthority[]>(
    `/api/v1/grid/authorities?limit=${limit}`,
  );
}

export function getEVCities(
  state = "OH",
  limit = 10,
) {
  return fetchJson<EVCity[]>(
    `/api/v1/ev/cities?state=${state}&limit=${limit}`,
  );
}

export function getWeather(
  limit = 5,
) {
  return fetchJson<WeatherForecast[]>(
    `/api/v1/weather?limit=${limit}`,
  );
}
