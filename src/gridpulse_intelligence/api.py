"""FastAPI serving layer for GridPulse Intelligence."""

from collections.abc import Awaitable, Callable
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from gridpulse_intelligence.api_models import (
    APIHealth,
    BalancingAuthorityPerformance,
    EVCityRanking,
    PlatformStatus,
    WeatherForecast,
)
from gridpulse_intelligence.api_repository import (
    DEFAULT_DATABASE_PATH,
    GridPulseRepository,
    GridPulseRepositoryError,
)
from gridpulse_intelligence.metrics import get_metrics

FRONTEND_ORIGINS = [
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

app = FastAPI(
    title="GridPulse Intelligence API",
    version="0.1.0",
    description=(
        "Serving API for electricity, weather, EV infrastructure, and GridPulse platform analytics."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=[
        "GET",
    ],
    allow_headers=[
        "*",
    ],
)

metrics = get_metrics()

metrics_app = make_asgi_app()

app.mount(
    "/metrics",
    metrics_app,
)


def _route_label(
    request: Request,
) -> str:
    """Return a stable low-cardinality route label."""

    route: Any = request.scope.get("route")

    path = getattr(
        route,
        "path",
        None,
    )

    if (
        isinstance(
            path,
            str,
        )
        and path
    ):
        return path

    return request.url.path


@app.middleware("http")
async def observe_api_request(
    request: Request,
    call_next: Callable[
        [Request],
        Awaitable[Response],
    ],
) -> Response:
    """Record request count, status, and duration."""

    started_at = perf_counter()

    try:
        response = await call_next(request)

    except Exception:
        duration = perf_counter() - started_at

        metrics.record_api_request(
            method=request.method,
            route=_route_label(request),
            status_code=500,
            duration_seconds=duration,
        )

        raise

    duration = perf_counter() - started_at

    metrics.record_api_request(
        method=request.method,
        route=_route_label(request),
        status_code=response.status_code,
        duration_seconds=duration,
    )

    return response


@lru_cache
def get_repository() -> GridPulseRepository:
    """Return the process-wide API repository."""

    return GridPulseRepository(database_path=Path(DEFAULT_DATABASE_PATH))


RepositoryDependency = Annotated[
    GridPulseRepository,
    Depends(get_repository),
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
            detail=str(exc),
        ) from exc

    return PlatformStatus(
        status="ok",
        database="duckdb",
        **status,
    )


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
        rows = repository.balancing_authorities(limit=limit)

    except GridPulseRepositoryError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
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
            detail=str(exc),
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
        rows = repository.weather_forecasts(limit=limit)

    except GridPulseRepositoryError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return [WeatherForecast.model_validate(row) for row in rows]
