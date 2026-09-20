"""Vercel FastAPI entrypoint for GridPulse Intelligence."""

from __future__ import annotations

import sys
from pathlib import Path


SRC_DIRECTORY = Path(__file__).resolve().parent / "src"
src_path = str(SRC_DIRECTORY)

if src_path not in sys.path:
    sys.path.insert(0, src_path)


from gridpulse_intelligence.api import app  # noqa: E402


@app.get(
    "/",
    include_in_schema=False,
)
def vercel_root() -> dict[str, str]:
    """Return a simple production landing response."""

    return {
        "service": "GridPulse Intelligence API",
        "status": "ok",
        "status_endpoint": "/api/v1/status",
        "health_endpoint": "/api/v1/platform/health",
        "docs": "/docs",
    }


__all__ = ["app"]
