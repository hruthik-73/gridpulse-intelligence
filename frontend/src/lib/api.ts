const API_URL =
  process.env.NEXT_PUBLIC_GRIDPULSE_API_URL ??
  "http://127.0.0.1:8080";


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

  average_generation_demand_gap_mwh:
    | number
    | null;

  forecast_coverage_pct: number | null;
  generation_coverage_pct: number | null;

  forecast_accuracy_rank: number;
  peak_demand_rank: number;

  contains_replay: boolean;

  latest_kafka_timestamp:
    | string
    | null;
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
  dc_fast_station_share_pct:
    | number
    | null;

  state_station_rank: number;
  national_station_rank: number;
  state_port_rank: number;

  latest_station_update:
    | string
    | null;
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

  precipitation_probability:
    | number
    | null;

  precipitation_risk: string;

  relative_humidity:
    | number
    | null;

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


export type GridRiskSeverity =
  | "NORMAL"
  | "ELEVATED"
  | "HIGH"
  | "CRITICAL";


export interface GridAnomaly {
  period: string;

  respondent: string;
  respondent_name: string;

  demand_mwh: number | null;
  demand_forecast_mwh: number | null;

  forecast_error_pct: number | null;
  generation_gap_pct: number | null;

  history_points: number;

  forecast_baseline_pct:
    | number
    | null;

  forecast_deviation_score: number;

  generation_baseline_pct:
    | number
    | null;

  generation_deviation_score: number;

  risk_score: number;
  severity: GridRiskSeverity;
}


export interface RegionalGridSignal {
  period: string;

  region: string;
  region_name: string;

  demand_mwh: number;

  demand_forecast_mwh:
    | number
    | null;

  net_generation_mwh:
    | number
    | null;

  total_interchange_mwh:
    | number
    | null;

  demand_baseline_mwh: number;

  demand_vs_baseline_pct: number;

  demand_change_pct:
    | number
    | null;

  forecast_error_pct:
    | number
    | null;

  generation_gap_pct:
    | number
    | null;

  history_points: number;

  demand_deviation_score: number;
  forecast_deviation_score: number;
  generation_deviation_score: number;

  pressure_score: number;

  severity: GridRiskSeverity;
}


export interface RegionalGridHistoryPoint {
  period: string;

  region: string;
  region_name: string;

  demand_mwh: number;

  demand_forecast_mwh:
    | number
    | null;

  net_generation_mwh:
    | number
    | null;

  total_interchange_mwh:
    | number
    | null;

  demand_baseline_mwh:
    | number
    | null;

  demand_vs_baseline_pct:
    | number
    | null;

  demand_change_pct:
    | number
    | null;

  forecast_error_pct:
    | number
    | null;

  generation_gap_pct:
    | number
    | null;

  contains_replay: boolean;
}




export interface RegionalGridTimelinePoint {
  period: string;

  region: string;
  region_name: string;

  demand_mwh: number;

  demand_forecast_mwh:
    | number
    | null;

  net_generation_mwh:
    | number
    | null;

  total_interchange_mwh:
    | number
    | null;

  demand_baseline_mwh: number;

  demand_vs_baseline_pct: number;

  demand_change_pct:
    | number
    | null;

  forecast_error_pct:
    | number
    | null;

  generation_gap_pct:
    | number
    | null;

  history_points: number;

  demand_deviation_score: number;
  forecast_deviation_score: number;
  generation_deviation_score: number;

  pressure_score: number;

  severity: GridRiskSeverity;

  contains_replay: boolean;
}



export type FreshnessState =
  | "FRESH"
  | "DELAYED"
  | "STALE"
  | "UNKNOWN";


export interface SourceFreshness {
  source: string;
  display_name: string;
  dataset: string;

  state: FreshnessState;

  latest_timestamp:
    | string
    | null;

  age_hours:
    | number
    | null;

  timestamp_basis: string;

  fresh_within_hours: number;
  stale_after_hours: number;
}


async function fetchJSON<T>(
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
      `GridPulse API request failed: ${response.status} ${response.statusText}`,
    );
  }

  return response.json() as Promise<T>;
}


export async function getPlatformStatus(): Promise<PlatformStatus> {
  return fetchJSON<PlatformStatus>(
    "/api/v1/status",
  );
}


export async function getGridAuthorities(
  limit = 20,
): Promise<GridAuthority[]> {
  return fetchJSON<GridAuthority[]>(
    `/api/v1/grid/authorities?limit=${limit}`,
  );
}


export async function getGridAnomalies(
  limit = 20,
): Promise<GridAnomaly[]> {
  return fetchJSON<GridAnomaly[]>(
    `/api/v1/grid/anomalies?limit=${limit}`,
  );
}


export async function getRegionalGridSignals(
  limit = 20,
): Promise<RegionalGridSignal[]> {
  return fetchJSON<RegionalGridSignal[]>(
    `/api/v1/grid/regions?limit=${limit}`,
  );
}


export async function getRegionalGridHistory(
  region: string,
  hours = 168,
): Promise<RegionalGridHistoryPoint[]> {
  return fetchJSON<RegionalGridHistoryPoint[]>(
    `/api/v1/grid/regions/${encodeURIComponent(
      region,
    )}/history?hours=${hours}`,
  );
}




export async function getRegionalGridTimeline(
  hours = 168,
): Promise<RegionalGridTimelinePoint[]> {
  return fetchJSON<RegionalGridTimelinePoint[]>(
    `/api/v1/grid/regions/timeline?hours=${hours}`,
  );
}


export async function getEVCities(
  state?: string,
  limit = 25,
): Promise<EVCity[]> {
  const searchParams =
    new URLSearchParams();

  if (state) {
    searchParams.set(
      "state",
      state,
    );
  }

  searchParams.set(
    "limit",
    String(limit),
  );

  return fetchJSON<EVCity[]>(
    `/api/v1/ev/cities?${searchParams.toString()}`,
  );
}


export async function getWeather(
  limit = 24,
): Promise<WeatherForecast[]> {
  return fetchJSON<WeatherForecast[]>(
    `/api/v1/weather?limit=${limit}`,
  );
}



export async function getSourceFreshness(): Promise<SourceFreshness[]> {
  return fetchJSON<SourceFreshness[]>(
    "/api/v1/platform/freshness",
  );
}


export async function getPlatformHealth(): Promise<PlatformHealth> {
  return fetchJSON<PlatformHealth>(
    "/api/v1/platform/health",
  );
}
