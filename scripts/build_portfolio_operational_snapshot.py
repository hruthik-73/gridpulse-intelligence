"""Capture sanitized operational evidence for the public GridPulse portfolio."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from gridpulse_intelligence.api import app

OUTPUT_PATH = Path("src/gridpulse_intelligence/assets/gridpulse_operational_snapshot.json")

PROJECT_ROOT = str(Path.cwd().resolve())


def sanitize(
    value: Any,
) -> Any:
    """Remove local-only implementation details from public evidence."""

    if isinstance(
        value,
        dict,
    ):
        return {key: sanitize(item) for key, item in value.items() if "command" not in key.lower()}

    if isinstance(
        value,
        list,
    ):
        return [sanitize(item) for item in value]

    if isinstance(
        value,
        str,
    ):
        return value.replace(
            PROJECT_ROOT,
            "<local-project>",
        )

    return value


def capture(
    client: TestClient,
    request_path: str,
    storage_path: str,
) -> tuple[
    str,
    Any,
]:
    """Capture one successful API response."""

    response = client.get(request_path)

    if response.status_code != 200:
        raise RuntimeError(f"{request_path} returned {response.status_code}: {response.text}")

    print(f"✓ {request_path}")

    return (
        storage_path,
        sanitize(response.json()),
    )


def main() -> None:
    """Build the public operational evidence snapshot."""

    client = TestClient(app)

    requests = [
        (
            "/api/v1/platform/freshness",
            "/api/v1/platform/freshness",
        ),
        (
            "/api/v1/platform/incidents",
            "/api/v1/platform/incidents",
        ),
        (
            "/api/v1/platform/lineage",
            "/api/v1/platform/lineage",
        ),
        (
            "/api/v1/platform/runs?limit=100",
            "/api/v1/platform/runs",
        ),
        (
            "/api/v1/platform/data-quality",
            "/api/v1/platform/data-quality",
        ),
    ]

    routes = dict(
        capture(
            client,
            request_path,
            storage_path,
        )
        for (
            request_path,
            storage_path,
        ) in requests
    )

    payload = {
        "captured_at": (datetime.now(UTC).isoformat()),
        "description": (
            "Sanitized operational evidence "
            "captured from the validated local "
            "GridPulse engineering environment."
        ),
        "routes": routes,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            payload,
            indent=2,
        )
        + "\n"
    )

    print()
    print("Portfolio operational snapshot:")
    print(OUTPUT_PATH)

    print(
        "Size:",
        f"{OUTPUT_PATH.stat().st_size / 1024:.1f} KB",
    )


if __name__ == "__main__":
    main()
