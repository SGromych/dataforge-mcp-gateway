"""Streamable HTTP transport for the MCP server.

This is the transport defined in MCP protocol revision 2025-03-26 and refined
through 2025-11-25: one HTTP endpoint that accepts POST (JSON-RPC in, JSON or
SSE out), GET (the server-to-client SSE stream) and DELETE (session teardown).
It replaces the deprecated HTTP+SSE transport in `sse.py`, and it is the only
transport Open WebUI speaks natively.

The module is split into separate pieces on purpose. `create_session_manager`
and `build_app` are callable on their own, so a test can enter the session
manager's context by hand and drive the Starlette app through
`httpx.ASGITransport` without binding a socket or running a lifespan.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator, Awaitable, Callable, MutableMapping
from typing import Any

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from dataforge_mcp.config import LOOPBACK_ALLOWED, Settings
from dataforge_mcp.logging import get_logger

from .auth import BearerAuthMiddleware

logger = get_logger(__name__)

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]

#: The session id the server mints must survive the round trip through a browser.
_EXPOSED_HEADERS = ["Mcp-Session-Id", "MCP-Protocol-Version"]


class StreamableHTTPASGIApp:
    """ASGI wrapper around the session manager.

    Starlette's `Route` inspects its endpoint: a *bound method* is treated as an
    HTTP handler and silently restricted to `methods=["GET"]`, which would break
    every POST to the MCP endpoint. A class instance is neither a function nor a
    method, so Starlette mounts it as a raw ASGI app and lets every verb through.
    """

    def __init__(self, session_manager: StreamableHTTPSessionManager) -> None:
        self.session_manager = session_manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.session_manager.handle_request(scope, receive, send)


def build_security_settings(settings: Settings) -> TransportSecuritySettings:
    """Decide how to answer the spec's "MUST validate the Origin header" rule.

    Three cases, in order:

    1. An explicit allow-list is configured -> honour it.
    2. Nothing configured but the server binds loopback -> use the localhost
       defaults, matching what the SDK's FastMCP does for the same situation.
    3. Nothing configured and the bind is public (`0.0.0.0` in Docker, say) ->
       protection off, with a warning. Enabling it here would reject everything,
       because no sane default allow-list covers the name a container is reached
       by: `host.docker.internal`, a compose service name, a proxy's Host header.
    """
    hosts = settings.allowed_hosts_list
    origins = settings.allowed_origins_list

    if hosts or origins:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=hosts,
            allowed_origins=origins,
        )

    if settings.binds_loopback_only:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=list(LOOPBACK_ALLOWED),
            allowed_origins=list(LOOPBACK_ALLOWED),
        )

    return TransportSecuritySettings(enable_dns_rebinding_protection=False)


def create_session_manager(server: Server, settings: Settings) -> StreamableHTTPSessionManager:
    """Build the session manager. One per process - it cannot be reused."""
    return StreamableHTTPSessionManager(
        app=server,
        event_store=None,  # no resumability: Last-Event-ID replay is not supported
        json_response=settings.mcp_json_response,
        stateless=settings.mcp_stateless,
        security_settings=build_security_settings(settings),
    )


def build_app(manager: StreamableHTTPSessionManager, settings: Settings) -> Starlette:
    """Wire the session manager into a Starlette app with health, auth and CORS."""

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with manager.run():
            yield

    endpoint = StreamableHTTPASGIApp(manager)
    path = settings.mcp_http_path

    routes = [
        Route("/health", health),
        Route(path, endpoint=endpoint),
    ]
    # Register the trailing-slash variant explicitly. Starlette would otherwise
    # answer `/mcp/` with a 307, and several HTTP clients drop the body or
    # downgrade the method when they follow a redirect on POST.
    if path != "/":
        routes.append(Route(f"{path}/", endpoint=endpoint))

    middleware: list[Middleware] = []
    if settings.cors_origins_list:
        middleware.append(
            Middleware(
                CORSMiddleware,
                allow_origins=settings.cors_origins_list,
                allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                allow_headers=["*"],
                expose_headers=_EXPOSED_HEADERS,
            )
        )
    if settings.mcp_auth_token is not None:
        middleware.append(
            Middleware(
                BearerAuthMiddleware,
                token=settings.mcp_auth_token.get_secret_value(),
            )
        )

    return Starlette(routes=routes, middleware=middleware, lifespan=lifespan)


def log_startup(settings: Settings) -> None:
    """Announce the effective posture, and warn when the endpoint is unprotected."""
    security = build_security_settings(settings)
    protection_on = security.enable_dns_rebinding_protection
    auth_on = settings.mcp_auth_token is not None

    logger.info(
        "mcp_transport_starting",
        transport="streamable-http",
        host=settings.host,
        port=settings.port,
        path=settings.mcp_http_path,
        auth="bearer" if auth_on else "none",
        dns_rebinding_protection=protection_on,
        json_response=settings.mcp_json_response,
        stateless=settings.mcp_stateless,
        cors=bool(settings.cors_origins_list),
    )

    if not auth_on and not settings.binds_loopback_only:
        logger.warning(
            "mcp_endpoint_unauthenticated",
            message=(
                "The MCP endpoint is reachable beyond localhost with no authentication. "
                "38 tools write to DataForge, including permanent deletion. "
                "Set MCP_AUTH_TOKEN, or restrict the port to a trusted network."
            ),
            host=settings.host,
            port=settings.port,
        )
    if not protection_on:
        logger.warning(
            "mcp_origin_validation_disabled",
            message=(
                "Origin validation is off because no allow-list is configured and the "
                "bind is not loopback. Set MCP_ALLOWED_HOSTS / MCP_ALLOWED_ORIGINS to "
                "enable DNS-rebinding protection."
            ),
        )


async def run_streamable_http(server: Server, settings: Settings) -> None:
    """Serve the MCP endpoint over Streamable HTTP with uvicorn."""
    import uvicorn

    log_startup(settings)

    manager = create_session_manager(server, settings)
    app = build_app(manager, settings)

    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    await uvicorn.Server(config).serve()
