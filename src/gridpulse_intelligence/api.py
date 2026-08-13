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
    PlatformHealthResponse,
    PlatformStatus,
    WeatherForecast,
)
from gridpulse_intelligence.api_repository import (
    GridPulseRepository,
    GridPulseRepositoryError,
)
from gridpulse_intelligence.grid_anomaly import load_grid_anomalies
from gridpulse_intelligence.platform_health import PlatformHealthService

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
        "EV infrastructure, platform health, and historical "
        "grid-risk intelligence."
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
    """Return explainable historical grid-risk scores."""

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
