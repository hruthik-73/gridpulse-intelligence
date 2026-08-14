"""Vercel entry point for the GridPulse Intelligence API."""

from __future__ import annotations

import sys
from pathlib import Path

# Vercel imports this file directly from /var/task/src/index.py.
# Add the src directory so the GridPulse package can be resolved
# without relying on an external PYTHONPATH configuration.
SRC_DIRECTORY = Path(__file__).resolve().parent

src_path = str(SRC_DIRECTORY)

if src_path not in sys.path:
    sys.path.insert(
        0,
        src_path,
    )


from gridpulse_intelligence.api import app  # noqa: E402

__all__ = [
    "app",
]
