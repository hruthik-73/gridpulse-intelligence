"""Security middleware for the GridPulse public API."""

from __future__ import annotations

from typing import Final

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from gridpulse_intelligence.deployment_config import get_runtime_mode

SAFE_PORTFOLIO_METHODS: Final[frozenset[str]] = frozenset(
    {
        "GET",
        "HEAD",
        "OPTIONS",
    }
)

TRUSTED_HOSTS: Final[tuple[str, ...]] = (
    "localhost",
    "127.0.0.1",
    "testserver",
    "*.vercel.app",
)


class PortfolioReadOnlyMiddleware:
    """Reject state-changing HTTP methods in public Portfolio Mode."""

    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] == "http" and get_runtime_mode() == "portfolio":
            method = str(
                scope.get(
                    "method",
                    "GET",
                )
            ).upper()

            if method not in SAFE_PORTFOLIO_METHODS:
                response = JSONResponse(
                    status_code=405,
                    content={"detail": ("The public GridPulse portfolio API is read-only.")},
                    headers={
                        "Allow": "GET, HEAD, OPTIONS",
                    },
                )

                await response(
                    scope,
                    receive,
                    send,
                )

                return

        await self.app(
            scope,
            receive,
            send,
        )


class SecurityHeadersMiddleware:
    """Apply conservative security headers to API responses."""

    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        async def send_with_security_headers(
            message: Message,
        ) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)

                headers["X-Content-Type-Options"] = "nosniff"

                headers["X-Frame-Options"] = "DENY"

                headers["Referrer-Policy"] = "no-referrer"

                headers["Permissions-Policy"] = (
                    "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
                )

            await send(message)

        await self.app(
            scope,
            receive,
            send_with_security_headers,
        )
