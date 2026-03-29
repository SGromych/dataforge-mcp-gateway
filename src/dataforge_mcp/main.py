"""Main entry point for the MCP server."""

import asyncio

from dataforge_mcp.config import get_settings
from dataforge_mcp.logging import setup_logging


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    from dataforge_mcp.mcp.server import create_mcp_server

    server = create_mcp_server(settings)

    if settings.mcp_transport == "sse":
        from dataforge_mcp.transport.sse import run_sse

        asyncio.run(run_sse(server, settings))
    else:
        from dataforge_mcp.transport.stdio import run_stdio

        asyncio.run(run_stdio(server))
