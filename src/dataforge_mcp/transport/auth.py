"""Bearer-token authentication for the HTTP transports.

This is deliberately raw ASGI rather than a Starlette ``BaseHTTPMiddleware``:
``BaseHTTPMiddleware`` wraps the response in an anyio task pair and buffers it,
which breaks the long-lived ``text/event-stream`` responses the MCP endpoint
depends on. A plain ASGI callable passes ``send`` through untouched.
"""

from __future__ import annotations

import hmac
import json
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from dataforge_mcp.errors import DataForgeError, ErrorCode

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]

_SCHEME = "bearer"


def _unauthorized_body(message: str) -> bytes:
    """Render a 401 in the same envelope every tool error uses."""
    error = DataForgeError(
        ErrorCode.MCP_UNAUTHORIZED,
        message,
        http_status=401,
    ).to_dict()
    return json.dumps(error, ensure_ascii=False).encode("utf-8")


class BearerAuthMiddleware:
    """Require ``Authorization: Bearer <token>`` on every request but the exempt paths."""

    def __init__(
        self,
        app: Callable[[Scope, Receive, Send], Awaitable[None]],
        token: str,
        exempt_paths: frozenset[str] = frozenset({"/health"}),
    ) -> None:
        self._app = app
        self._token = token
        self._exempt_paths = exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in self._exempt_paths:
            await self._app(scope, receive, send)
            return

        presented = _extract_bearer(scope)
        if presented is None:
            await _send_401(send, "Missing Authorization: Bearer header.")
            return
        # Constant-time compare so the endpoint does not leak the token by timing.
        if not hmac.compare_digest(presented, self._token):
            await _send_401(send, "Invalid bearer token.")
            return

        await self._app(scope, receive, send)


def _extract_bearer(scope: Scope) -> str | None:
    """Pull the bearer credential out of the raw ASGI headers, or None."""
    for raw_name, raw_value in scope.get("headers", []):
        if raw_name.lower() != b"authorization":
            continue
        try:
            value = raw_value.decode("latin-1")
        except UnicodeDecodeError:  # pragma: no cover - ASGI servers reject these first
            return None
        scheme, _, credential = value.partition(" ")
        if scheme.lower() != _SCHEME:
            return None
        return credential.strip()
    return None


async def _send_401(send: Send, message: str) -> None:
    body = _unauthorized_body(message)
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(body)).encode("ascii")),
                # RFC 9110 requires a challenge on a 401.
                (b"www-authenticate", b'Bearer realm="dataforge-mcp"'),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
