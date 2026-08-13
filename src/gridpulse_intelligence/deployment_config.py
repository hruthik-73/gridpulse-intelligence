"""Deployment-aware configuration for GridPulse serving components."""

from __future__ import annotations

import os
from pathlib import Path

MODULE_DIRECTORY = Path(__file__).resolve().parent

LOCAL_DATABASE_PATH = Path("data/warehouse/gridpulse.duckdb")

PORTFOLIO_DATABASE_PATH = MODULE_DIRECTORY / "assets" / "gridpulse_portfolio.duckdb"

LOCAL_CORS_ORIGINS = (
    "http://localhost:3001",
    "http://127.0.0.1:3001",
)


def get_runtime_mode() -> str:
    """Return the configured GridPulse runtime mode."""

    return (
        os.getenv(
            "GRIDPULSE_RUNTIME_MODE",
            "local",
        )
        .strip()
        .lower()
    )


def get_database_path() -> Path:
    """Return the configured GridPulse analytics database."""

    configured = os.getenv("GRIDPULSE_DATABASE_PATH")

    if configured:
        return Path(configured).expanduser()

    if get_runtime_mode() == "portfolio":
        return PORTFOLIO_DATABASE_PATH

    return LOCAL_DATABASE_PATH


def get_cors_origins() -> list[str]:
    """Return browser origins allowed to call the API."""

    configured = os.getenv("GRIDPULSE_CORS_ORIGINS")

    if not configured:
        return list(LOCAL_CORS_ORIGINS)

    return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
