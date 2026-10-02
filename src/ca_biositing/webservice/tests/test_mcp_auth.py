"""Unit tests for MCPAuthMiddleware.

These drive MCPAuthMiddleware directly over raw ASGI scope/receive/send,
bypassing the FastAPI app and its lifespan entirely. This is deliberate:
mcp 1.30.0's StreamableHTTPSessionManager is a module-level singleton whose
.run() raises if entered more than once per process, so a second TestClient
context (as used by test_mcp.py's integration smoke test) cannot coexist
with these in the same pytest session. Testing the middleware class in
isolation avoids that constraint and needs no live database — the end-to-end
"valid key succeeds through the real MCP app" path is covered by the
integration test in test_mcp.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ca_biositing.datamodels.models import ApiKey
from ca_biositing.webservice.config import WebServiceConfig
from ca_biositing.webservice.middleware import MCPAuthMiddleware


async def _inner_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def _make_scope(headers: dict[str, str]) -> dict:
    return {
        "type": "http",
        "method": "POST",
        "path": "/mcp/mcp",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }


async def _receive():
    return {"type": "http.request", "body": b"", "more_body": False}


class _CapturingSend:
    def __init__(self):
        self.messages = []

    async def __call__(self, message):
        self.messages.append(message)

    @property
    def status(self) -> int | None:
        for m in self.messages:
            if m["type"] == "http.response.start":
                return m["status"]
        return None


def _config(dev_mode: bool) -> WebServiceConfig:
    return WebServiceConfig(dev_mode=dev_mode)


@pytest.mark.anyio
async def test_dev_mode_allows_request_without_auth():
    middleware = MCPAuthMiddleware(_inner_app, session_factory=MagicMock(), config=_config(True))
    send = _CapturingSend()
    await middleware(_make_scope({}), _receive, send)
    assert send.status == 200


@pytest.mark.anyio
async def test_rejects_with_401_when_no_credentials_and_dev_mode_off():
    middleware = MCPAuthMiddleware(_inner_app, session_factory=MagicMock(), config=_config(False))
    send = _CapturingSend()
    await middleware(_make_scope({}), _receive, send)
    assert send.status == 401


@pytest.mark.anyio
async def test_rejects_with_401_for_invalid_api_key():
    middleware = MCPAuthMiddleware(_inner_app, session_factory=MagicMock(), config=_config(False))
    send = _CapturingSend()
    with patch("ca_biositing.webservice.middleware.validate_api_key", return_value=None):
        await middleware(_make_scope({"X-API-Key": "not-a-real-key"}), _receive, send)
    assert send.status == 401


def _fake_api_key() -> ApiKey:
    return ApiKey(
        id=1,
        api_user_id=1,
        name="test",
        key_prefix="abcd1234",
        key_hash="irrelevant",
        is_active=True,
        rate_limit_per_minute=0,
    )


@pytest.mark.anyio
async def test_accepts_valid_x_api_key_and_calls_inner_app():
    middleware = MCPAuthMiddleware(_inner_app, session_factory=MagicMock(), config=_config(False))
    send = _CapturingSend()
    with (
        patch("ca_biositing.webservice.middleware.validate_api_key", return_value=_fake_api_key()),
        patch("ca_biositing.webservice.middleware.check_and_increment_rate_limit", return_value=True),
    ):
        await middleware(_make_scope({"X-API-Key": "abcd1234somerandomkey"}), _receive, send)
    assert send.status == 200


@pytest.mark.anyio
async def test_accepts_bearer_header_as_api_key_source():
    middleware = MCPAuthMiddleware(_inner_app, session_factory=MagicMock(), config=_config(False))
    send = _CapturingSend()
    with (
        patch("ca_biositing.webservice.middleware.validate_api_key", return_value=_fake_api_key()),
        patch("ca_biositing.webservice.middleware.check_and_increment_rate_limit", return_value=True),
    ):
        await middleware(
            _make_scope({"Authorization": "Bearer abcd1234somerandomkey"}), _receive, send
        )
    assert send.status == 200


@pytest.mark.anyio
async def test_rejects_with_429_when_rate_limited():
    middleware = MCPAuthMiddleware(_inner_app, session_factory=MagicMock(), config=_config(False))
    send = _CapturingSend()
    with (
        patch("ca_biositing.webservice.middleware.validate_api_key", return_value=_fake_api_key()),
        patch("ca_biositing.webservice.middleware.check_and_increment_rate_limit", return_value=False),
    ):
        await middleware(_make_scope({"X-API-Key": "abcd1234somerandomkey"}), _receive, send)
    assert send.status == 429


@pytest.mark.anyio
async def test_non_http_scope_passes_through_unchanged():
    """WebSocket/lifespan scopes must bypass auth entirely (never buffered/rejected)."""
    middleware = MCPAuthMiddleware(_inner_app, session_factory=MagicMock(), config=_config(False))
    send = _CapturingSend()
    scope = {"type": "websocket"}
    await middleware(scope, _receive, send)
    assert send.status == 200
