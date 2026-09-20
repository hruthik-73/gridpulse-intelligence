"""Vercel entry point for the GridPulse Intelligence API."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIRECTORY = PROJECT_ROOT / "src"

src_path = str(SRC_DIRECTORY)

if src_path not in sys.path:
    sys.path.insert(0, src_path)


from gridpulse_intelligence.api import app  # noqa: E402


__all__ = [
    "app",
]
