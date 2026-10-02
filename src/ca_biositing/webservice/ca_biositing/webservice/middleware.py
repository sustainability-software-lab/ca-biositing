"""Pure ASGI auth middleware for the /mcp mount.

/mcp is mounted as a raw Starlette ASGI app (``app.mount(...)``), not a
FastAPI APIRouter, so ``Depends(get_current_user)`` cannot be attached to it.
This middleware enforces auth at the ASGI level instead.

It is intentionally NOT a ``starlette.middleware.base.BaseHTTPMiddleware``:
that class buffers the inner app's response before re-emitting it, which
breaks the Server-Sent Events streaming the MCP transport relies on. This
middleware only ever touches the request side — on success it calls the
inner app with the original receive/send callables untouched.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import sessionmaker
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ca_biositing.webservice.config import WebServiceConfig
from ca_biositing.webservice.services.auth_service import (
    check_and_increment_rate_limit,
    validate_api_key,
)

logger = logging.getLogger(__name__)

_UNAUTHORIZED_BODY = {
    "jsonrpc": "2.0",
    "error": {
        "code": -32001,
        "message": "Could not validate credentials",
    },
}

_RATE_LIMITED_BODY = {
    "jsonrpc": "2.0",
    "error": {
        "code": -32002,
        "message": "Rate limit exceeded",
    },
}


def _get_header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin-1")
    return None


class MCPAuthMiddleware:
    """Gate a mounted ASGI app behind the existing ApiKey auth system.

    Checks X-API-Key first (the expected MCP client credential), falling
    back to an Authorization: Bearer <raw key> header for parity with
    clients that only support the Bearer convention. JWTs and cookies are
    not accepted here — MCP clients are machine callers, not browsers, and
    JWT's 30-minute expiry is a poor fit for long-lived agent sessions.
    """

    def __init__(
        self,
        app: ASGIApp,
        session_factory: sessionmaker,
        config: WebServiceConfig,
    ) -> None:
        self.app = app
        self.session_factory = session_factory
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if self.config.dev_mode:
            await self.app(scope, receive, send)
            return

        raw_key = _get_header(scope, b"x-api-key")
        if raw_key is None:
            auth_header = _get_header(scope, b"authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                raw_key = auth_header[len("bearer "):]

        if not raw_key:
            await self._reject(scope, send, _UNAUTHORIZED_BODY, 401)
            return

        with self.session_factory() as session:
            api_key = validate_api_key(session, raw_key)
            if api_key is None:
                await self._reject(scope, send, _UNAUTHORIZED_BODY, 401)
                return
            if not check_and_increment_rate_limit(session, api_key):
                await self._reject(scope, send, _RATE_LIMITED_BODY, 429)
                return

        await self.app(scope, receive, send)

    async def _reject(self, scope: Scope, send: Send, body: dict, status_code: int) -> None:
        response = JSONResponse(content=body, status_code=status_code)
        await response(scope, _noop_receive, send)


async def _noop_receive() -> dict:
    return {"type": "http.disconnect"}
