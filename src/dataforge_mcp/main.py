"""Main entry point for the MCP server."""

import asyncio

from dataforge_mcp.config import get_settings
from dataforge_mcp.logging import setup_logging


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    from dataforge_mcp.mcp.server import create_mcp_server
    from dataforge_mcp.transport import run_transport

    server = create_mcp_server(settings)
    asyncio.run(run_transport(server, settings))
