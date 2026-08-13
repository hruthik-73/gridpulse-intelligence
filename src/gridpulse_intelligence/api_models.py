"""Response models for the GridPulse Intelligence API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class APIHealth(BaseModel):
    """Basic application health response."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: str
    service: str


class PlatformStatus(BaseModel):
    """GridPulse serving-layer status."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: str
    database: str
    grid_hourly_rows: int
    balancing_authorities: int
    ev_cities: int
    weather_forecasts: int


class BalancingAuthorityPerformance(BaseModel):
    """Aggregated balancing-authority analytics."""

    model_config = ConfigDict(
        extra="forbid",
    )

    respondent: str
    respondent_name: str | None

    observed_hours: int
    demand_hours: int
    forecast_pair_hours: int
    generation_pair_hours: int

    average_demand_mwh: float | None
    peak_demand_mwh: float | None

    mean_abs_forecast_error_mwh: float | None
    mean_abs_forecast_error_pct: float | None

    average_generation_demand_gap_mwh: float | None

    forecast_coverage_pct: float | None
    generation_coverage_pct: float | None

    forecast_accuracy_rank: int
    peak_demand_rank: int

    contains_replay: bool

    latest_kafka_timestamp: datetime | None


class EVCityRanking(BaseModel):
    """City-level EV infrastructure analytics."""

    model_config = ConfigDict(
        extra="forbid",
    )

    city_state_key: str

    city: str
    state: str
    country: str

    station_count: int

    level1_ports: int
    level2_ports: int
    dc_fast_ports: int

    total_known_ports: int

    dc_fast_station_count: int
    network_count: int

    ports_per_station: float | None
    dc_fast_station_share_pct: float | None

    state_station_rank: int
    national_station_rank: int
    state_port_rank: int

    latest_station_update: datetime | None


class WeatherForecast(BaseModel):
    """Dashboard-ready weather forecast."""

    model_config = ConfigDict(
        extra="forbid",
    )

    weather_forecast_key: str
    location_key: str

    latitude: float
    longitude: float

    period_start: datetime
    period_end: datetime

    forecast_hour: int

    temperature_f: float | None
    temperature_c: float | None

    precipitation_probability: float | None
    precipitation_risk: str

    relative_humidity: float | None

    wind_speed: str | None
    wind_direction: str | None
    short_forecast: str | None

    replay: bool

    kafka_partition: int
    kafka_offset: int
    kafka_timestamp: datetime | None


class ComponentHealthResponse(BaseModel):
    """Health state for one GridPulse component."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: str
    detail: str
    latency_ms: float


class PlatformHealthResponse(BaseModel):
    """Runtime health of the GridPulse platform."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: str

    warehouse: ComponentHealthResponse
    kafka: ComponentHealthResponse
    prometheus: ComponentHealthResponse
    kafka_consumer: ComponentHealthResponse


class GridAnomalyResponse(BaseModel):
    """Explainable historical GridPulse grid-risk observation."""

    model_config = ConfigDict(
        extra="forbid",
    )

    period: str

    respondent: str
    respondent_name: str

    demand_mwh: float | None
    demand_forecast_mwh: float | None

    forecast_error_pct: float | None
    generation_gap_pct: float | None

    history_points: int

    forecast_baseline_pct: float | None
    forecast_deviation_score: float

    generation_baseline_pct: float | None
    generation_deviation_score: float

    risk_score: float
    severity: str


class RegionalGridResponse(BaseModel):
    """Explainable regional grid-pressure observation."""

    model_config = ConfigDict(
        extra="forbid",
    )

    period: str

    region: str
    region_name: str

    demand_mwh: float
    demand_forecast_mwh: float | None
    net_generation_mwh: float | None
    total_interchange_mwh: float | None

    demand_baseline_mwh: float

    demand_vs_baseline_pct: float
    demand_change_pct: float | None

    forecast_error_pct: float | None
    generation_gap_pct: float | None

    history_points: int

    demand_deviation_score: float
    forecast_deviation_score: float
    generation_deviation_score: float

    pressure_score: float
    severity: str


class RegionalGridHistoryResponse(BaseModel):
    """Historical regional grid observation."""

    model_config = ConfigDict(
        extra="forbid",
    )

    period: str

    region: str
    region_name: str

    demand_mwh: float
    demand_forecast_mwh: float | None
    net_generation_mwh: float | None
    total_interchange_mwh: float | None

    demand_baseline_mwh: float | None

    demand_vs_baseline_pct: float | None
    demand_change_pct: float | None

    forecast_error_pct: float | None
    generation_gap_pct: float | None

    contains_replay: bool


class RegionalGridTimelineResponse(BaseModel):
    """Historically scored regional pressure observation."""

    model_config = ConfigDict(
        extra="forbid",
    )

    period: str

    region: str
    region_name: str

    demand_mwh: float
    demand_forecast_mwh: float | None
    net_generation_mwh: float | None
    total_interchange_mwh: float | None

    demand_baseline_mwh: float

    demand_vs_baseline_pct: float
    demand_change_pct: float | None

    forecast_error_pct: float | None
    generation_gap_pct: float | None

    history_points: int

    demand_deviation_score: float
    forecast_deviation_score: float
    generation_deviation_score: float

    pressure_score: float
    severity: str

    contains_replay: bool


class SourceFreshnessResponse(BaseModel):
    """Operational freshness state for one GridPulse source."""

    model_config = ConfigDict(
        extra="forbid",
    )

    source: str
    display_name: str
    dataset: str

    state: str

    latest_timestamp: datetime | None
    age_hours: float | None

    timestamp_basis: str

    fresh_within_hours: float
    stale_after_hours: float


class OperationalIncidentResponse(BaseModel):
    """One actionable GridPulse operational incident."""

    model_config = ConfigDict(
        extra="forbid",
    )

    incident_id: str

    severity: str
    category: str

    title: str
    source: str

    current_state: str

    evidence: str
    recommended_action: str


class OperationalIncidentSummaryResponse(BaseModel):
    """Current GridPulse operational incident summary."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: str
    active_incidents: int
    highest_severity: str

    incidents: list[OperationalIncidentResponse]


class PipelineLineageNodeResponse(BaseModel):
    """One node in the GridPulse pipeline lineage."""

    model_config = ConfigDict(
        extra="forbid",
    )

    node_id: str

    label: str
    layer: str

    technology: str

    state: str

    detail: str

    source: str | None

    position_x: int
    position_y: int


class PipelineLineageEdgeResponse(BaseModel):
    """Directed edge between lineage nodes."""

    model_config = ConfigDict(
        extra="forbid",
    )

    edge_id: str

    source_node: str
    target_node: str

    label: str


class PipelineLineageResponse(BaseModel):
    """Current GridPulse lineage intelligence."""

    model_config = ConfigDict(
        extra="forbid",
    )

    nodes: list[PipelineLineageNodeResponse]

    edges: list[PipelineLineageEdgeResponse]
