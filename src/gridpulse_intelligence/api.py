"""FastAPI serving layer for GridPulse Intelligence."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.responses import Response

from gridpulse_intelligence.api_models import (
    APIHealth,
    BalancingAuthorityPerformance,
    ComponentHealthResponse,
    EVCityRanking,
    GridAnomalyResponse,
    OperationalIncidentResponse,
    OperationalIncidentSummaryResponse,
    PlatformHealthResponse,
    PlatformStatus,
    RegionalGridHistoryResponse,
    RegionalGridResponse,
    RegionalGridTimelineResponse,
    SourceFreshnessResponse,
    WeatherForecast,
)
from gridpulse_intelligence.api_repository import (
    GridPulseRepository,
    GridPulseRepositoryError,
)
from gridpulse_intelligence.grid_anomaly import load_grid_anomalies
from gridpulse_intelligence.incident_intelligence import (
    ComponentState,
    build_operational_incidents,
    highest_operational_severity,
)
from gridpulse_intelligence.platform_health import PlatformHealthService
from gridpulse_intelligence.regional_grid import load_regional_grid_signals
from gridpulse_intelligence.regional_history import load_regional_history
from gridpulse_intelligence.regional_timeline import load_regional_timeline
from gridpulse_intelligence.source_freshness import load_source_freshness

DEFAULT_DATABASE_PATH = "data/warehouse/gridpulse.duckdb"


API_REQUESTS = Counter(
    "gridpulse_api_requests_total",
    "Total GridPulse API HTTP requests.",
    (
        "method",
        "route",
        "status_code",
    ),
)

API_REQUEST_DURATION = Histogram(
    "gridpulse_api_request_duration_seconds",
    "GridPulse API request duration in seconds.",
    (
        "method",
        "route",
    ),
)


app = FastAPI(
    title="GridPulse Intelligence API",
    version="0.1.0",
    description=(
        "Serving layer for GridPulse electricity, weather, "
        "EV infrastructure, platform health, historical "
        "grid-risk intelligence, and regional grid-pressure "
        "intelligence."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=[
        "*",
    ],
    allow_headers=[
        "*",
    ],
)


metrics_app = make_asgi_app()

app.mount(
    "/metrics",
    metrics_app,
)


def _route_label(
    request: Request,
) -> str:
    """Return a low-cardinality route label for API metrics."""

    route = request.scope.get(
        "route",
    )

    path = getattr(
        route,
        "path",
        None,
    )

    if isinstance(
        path,
        str,
    ):
        return path

    return request.url.path


@app.middleware(
    "http",
)
async def observe_api_request(
    request: Request,
    call_next: Callable[
        [Request],
        Awaitable[Response],
    ],
) -> Response:
    """Record API request count and request duration."""

    started = time.perf_counter()

    try:
        response = await call_next(
            request,
        )

    except Exception:
        duration = time.perf_counter() - started

        API_REQUESTS.labels(
            method=request.method,
            route=_route_label(
                request,
            ),
            status_code="500",
        ).inc()

        API_REQUEST_DURATION.labels(
            method=request.method,
            route=_route_label(
                request,
            ),
        ).observe(
            duration,
        )

        raise

    duration = time.perf_counter() - started

    API_REQUESTS.labels(
        method=request.method,
        route=_route_label(
            request,
        ),
        status_code=str(
            response.status_code,
        ),
    ).inc()

    API_REQUEST_DURATION.labels(
        method=request.method,
        route=_route_label(
            request,
        ),
    ).observe(
        duration,
    )

    return response


@lru_cache
def get_repository() -> GridPulseRepository:
    """Return the process-wide API repository."""

    return GridPulseRepository(
        database_path=Path(
            DEFAULT_DATABASE_PATH,
        )
    )


RepositoryDependency = Annotated[
    GridPulseRepository,
    Depends(
        get_repository,
    ),
]


@lru_cache
def get_platform_health_service() -> PlatformHealthService:
    """Return the process-wide platform health service."""

    return PlatformHealthService(
        repository=get_repository(),
    )


HealthServiceDependency = Annotated[
    PlatformHealthService,
    Depends(
        get_platform_health_service,
    ),
]


@app.get(
    "/health",
    response_model=APIHealth,
    tags=[
        "platform",
    ],
)
def health() -> APIHealth:
    """Return basic process health."""

    return APIHealth(
        status="ok",
        service="gridpulse-intelligence-api",
    )


@app.get(
    "/api/v1/status",
    response_model=PlatformStatus,
    tags=[
        "platform",
    ],
)
def platform_status(
    repository: RepositoryDependency,
) -> PlatformStatus:
    """Return analytics serving-layer status."""

    try:
        status = repository.platform_status()

    except GridPulseRepositoryError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(
                exc,
            ),
        ) from exc

    return PlatformStatus(
        status="ok",
        database="duckdb",
        **status,
    )


@app.get(
    "/api/v1/platform/health",
    response_model=PlatformHealthResponse,
    tags=[
        "platform",
    ],
)
def platform_health(
    health_service: HealthServiceDependency,
) -> PlatformHealthResponse:
    """Return runtime dependency health."""

    components = health_service.snapshot()

    statuses = {component.status for component in components.values()}

    if "unhealthy" in statuses:
        overall_status = "unhealthy"

    elif "degraded" in statuses:
        overall_status = "degraded"

    else:
        overall_status = "healthy"

    def response_component(
        name: str,
    ) -> ComponentHealthResponse:
        component = components[name]

        return ComponentHealthResponse(
            status=component.status,
            detail=component.detail,
            latency_ms=component.latency_ms,
        )

    return PlatformHealthResponse(
        status=overall_status,
        warehouse=response_component(
            "warehouse",
        ),
        kafka=response_component(
            "kafka",
        ),
        prometheus=response_component(
            "prometheus",
        ),
        kafka_consumer=response_component(
            "kafka_consumer",
        ),
    )


@app.get(
    "/api/v1/platform/incidents",
    response_model=OperationalIncidentSummaryResponse,
    tags=[
        "platform",
    ],
)
def operational_incidents(
    health_service: HealthServiceDependency,
) -> OperationalIncidentSummaryResponse:
    """Return prioritized operational incidents."""

    try:
        freshness = load_source_freshness(
            database_path=Path(
                DEFAULT_DATABASE_PATH,
            )
        )

        health = health_service.snapshot()

        components = [
            ComponentState(
                name=name,
                status=component.status,
                detail=component.detail,
                latency_ms=component.latency_ms,
            )
            for name, component in health.items()
        ]

        incidents = build_operational_incidents(
            freshness=freshness,
            components=components,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=("Operational incident intelligence is currently unavailable."),
        ) from exc

    highest_severity = highest_operational_severity(incidents)

    return OperationalIncidentSummaryResponse(
        status=("healthy" if not incidents else "attention"),
        active_incidents=len(incidents),
        highest_severity=highest_severity,
        incidents=[
            OperationalIncidentResponse(
                incident_id=row.incident_id,
                severity=row.severity,
                category=row.category,
                title=row.title,
                source=row.source,
                current_state=row.current_state,
                evidence=row.evidence,
                recommended_action=row.recommended_action,
            )
            for row in incidents
        ],
    )


@app.get(
    "/api/v1/platform/freshness",
    response_model=list[SourceFreshnessResponse],
    tags=[
        "platform",
    ],
)
def source_freshness() -> list[SourceFreshnessResponse]:
    """Return source-level operational freshness intelligence."""

    try:
        rows = load_source_freshness(
            database_path=Path(
                DEFAULT_DATABASE_PATH,
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=("Source freshness intelligence is currently unavailable."),
        ) from exc

    return [
        SourceFreshnessResponse(
            source=row.source,
            display_name=row.display_name,
            dataset=row.dataset,
            state=row.state,
            latest_timestamp=row.latest_timestamp,
            age_hours=row.age_hours,
            timestamp_basis=row.timestamp_basis,
            fresh_within_hours=row.fresh_within_hours,
            stale_after_hours=row.stale_after_hours,
        )
        for row in rows
    ]


@app.get(
    "/api/v1/grid/anomalies",
    response_model=list[GridAnomalyResponse],
    tags=[
        "grid",
    ],
)
def grid_anomalies(
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 20,
) -> list[GridAnomalyResponse]:
    """Return explainable historical balancing-authority risk scores."""

    try:
        rows = load_grid_anomalies(
            database_path=Path(
                DEFAULT_DATABASE_PATH,
            ),
            limit=limit,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=("Grid anomaly intelligence is currently unavailable."),
        ) from exc

    return [
        GridAnomalyResponse(
            period=row.period,
            respondent=row.respondent,
            respondent_name=row.respondent_name,
            demand_mwh=row.demand_mwh,
            demand_forecast_mwh=row.demand_forecast_mwh,
            forecast_error_pct=row.forecast_error_pct,
            generation_gap_pct=row.generation_gap_pct,
            history_points=row.history_points,
            forecast_baseline_pct=row.forecast_baseline_pct,
            forecast_deviation_score=row.forecast_deviation_score,
            generation_baseline_pct=row.generation_baseline_pct,
            generation_deviation_score=row.generation_deviation_score,
            risk_score=row.risk_score,
            severity=row.severity,
        )
        for row in rows
    ]


@app.get(
    "/api/v1/grid/regions",
    response_model=list[RegionalGridResponse],
    tags=[
        "grid",
    ],
)
def grid_regions(
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
        ),
    ] = 20,
) -> list[RegionalGridResponse]:
    """Return explainable historical regional grid-pressure signals."""

    try:
        rows = load_regional_grid_signals(
            database_path=Path(
                DEFAULT_DATABASE_PATH,
            ),
            limit=limit,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=("Regional grid intelligence is currently unavailable."),
        ) from exc

    return [
        RegionalGridResponse(
            period=row.period,
            region=row.region,
            region_name=row.region_name,
            demand_mwh=row.demand_mwh,
            demand_forecast_mwh=row.demand_forecast_mwh,
            net_generation_mwh=row.net_generation_mwh,
            total_interchange_mwh=row.total_interchange_mwh,
            demand_baseline_mwh=row.demand_baseline_mwh,
            demand_vs_baseline_pct=row.demand_vs_baseline_pct,
            demand_change_pct=row.demand_change_pct,
            forecast_error_pct=row.forecast_error_pct,
            generation_gap_pct=row.generation_gap_pct,
            history_points=row.history_points,
            demand_deviation_score=row.demand_deviation_score,
            forecast_deviation_score=row.forecast_deviation_score,
            generation_deviation_score=row.generation_deviation_score,
            pressure_score=row.pressure_score,
            severity=row.severity,
        )
        for row in rows
    ]


@app.get(
    "/api/v1/grid/regions/{region}/history",
    response_model=list[RegionalGridHistoryResponse],
    tags=[
        "grid",
    ],
)
def regional_grid_history(
    region: str,
    hours: Annotated[
        int,
        Query(
            ge=24,
            le=720,
        ),
    ] = 168,
) -> list[RegionalGridHistoryResponse]:
    """Return recent historical observations for one EIA region."""

    try:
        rows = load_regional_history(
            database_path=Path(
                DEFAULT_DATABASE_PATH,
            ),
            region=region,
            hours=hours,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=("Regional history is currently unavailable."),
        ) from exc

    return [
        RegionalGridHistoryResponse(
            period=row.period,
            region=row.region,
            region_name=row.region_name,
            demand_mwh=row.demand_mwh,
            demand_forecast_mwh=row.demand_forecast_mwh,
            net_generation_mwh=row.net_generation_mwh,
            total_interchange_mwh=row.total_interchange_mwh,
            demand_baseline_mwh=row.demand_baseline_mwh,
            demand_vs_baseline_pct=row.demand_vs_baseline_pct,
            demand_change_pct=row.demand_change_pct,
            forecast_error_pct=row.forecast_error_pct,
            generation_gap_pct=row.generation_gap_pct,
            contains_replay=row.contains_replay,
        )
        for row in rows
    ]


@app.get(
    "/api/v1/grid/regions/timeline",
    response_model=list[RegionalGridTimelineResponse],
    tags=[
        "grid",
    ],
)
def regional_grid_timeline(
    hours: Annotated[
        int,
        Query(
            ge=24,
            le=720,
        ),
    ] = 168,
) -> list[RegionalGridTimelineResponse]:
    """Return historically scored regional pressure frames."""

    try:
        rows = load_regional_timeline(
            database_path=Path(
                DEFAULT_DATABASE_PATH,
            ),
            hours=hours,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=("Regional pressure timeline is currently unavailable."),
        ) from exc

    return [
        RegionalGridTimelineResponse(
            period=row.period,
            region=row.region,
            region_name=row.region_name,
            demand_mwh=row.demand_mwh,
            demand_forecast_mwh=row.demand_forecast_mwh,
            net_generation_mwh=row.net_generation_mwh,
            total_interchange_mwh=row.total_interchange_mwh,
            demand_baseline_mwh=row.demand_baseline_mwh,
            demand_vs_baseline_pct=row.demand_vs_baseline_pct,
            demand_change_pct=row.demand_change_pct,
            forecast_error_pct=row.forecast_error_pct,
            generation_gap_pct=row.generation_gap_pct,
            history_points=row.history_points,
            demand_deviation_score=row.demand_deviation_score,
            forecast_deviation_score=row.forecast_deviation_score,
            generation_deviation_score=row.generation_deviation_score,
            pressure_score=row.pressure_score,
            severity=row.severity,
            contains_replay=row.contains_replay,
        )
        for row in rows
    ]


@app.get(
    "/api/v1/grid/authorities",
    response_model=list[BalancingAuthorityPerformance],
    tags=[
        "grid",
    ],
)
def grid_authorities(
    repository: RepositoryDependency,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 20,
) -> list[BalancingAuthorityPerformance]:
    """Return balancing-authority performance analytics."""

    try:
        rows = repository.balancing_authorities(
            limit=limit,
        )

    except GridPulseRepositoryError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(
                exc,
            ),
        ) from exc

    return [BalancingAuthorityPerformance.model_validate(row) for row in rows]


@app.get(
    "/api/v1/ev/cities",
    response_model=list[EVCityRanking],
    tags=[
        "ev",
    ],
)
def ev_cities(
    repository: RepositoryDependency,
    state: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=2,
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
        ),
    ] = 25,
) -> list[EVCityRanking]:
    """Return EV infrastructure rankings."""

    try:
        rows = repository.ev_cities(
            state=state,
            limit=limit,
        )

    except GridPulseRepositoryError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(
                exc,
            ),
        ) from exc

    return [EVCityRanking.model_validate(row) for row in rows]


@app.get(
    "/api/v1/weather",
    response_model=list[WeatherForecast],
    tags=[
        "weather",
    ],
)
def weather(
    repository: RepositoryDependency,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=168,
        ),
    ] = 24,
) -> list[WeatherForecast]:
    """Return hourly weather forecasts."""

    try:
        rows = repository.weather_forecasts(
            limit=limit,
        )

    except GridPulseRepositoryError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(
                exc,
            ),
        ) from exc

    return [WeatherForecast.model_validate(row) for row in rows]
