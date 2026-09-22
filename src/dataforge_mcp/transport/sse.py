"""Deprecated HTTP+SSE transport for the MCP server.

This is the transport from MCP protocol revision 2024-11-05. It was deprecated
in revision 2025-03-26 and replaced by Streamable HTTP (`streamable_http.py`).
It is kept so existing deployments keep working; new ones should set
`MCP_TRANSPORT=streamable-http`. Unlike the streamable-http transport, this one
has no authentication and no Origin validation - do not expose it directly.
"""

from __future__ import annotations

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from dataforge_mcp.config import Settings


async def run_sse(server: Server, settings: Settings) -> None:
    import uvicorn

    sse_transport = SseServerTransport("/messages/")

    async def handle_sse(request: Request):  # noqa: ANN201
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0],
                streams[1],
                server.create_initialization_options(),
            )

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    app = Starlette(
        routes=[
            Route("/health", health),
            Route("/sse", handle_sse),
            Mount("/messages/", app=sse_transport.handle_post_message),
        ],
    )

    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    server_instance = uvicorn.Server(config)
    await server_instance.serve()
