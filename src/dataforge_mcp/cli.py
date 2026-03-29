"""CLI entry point for dataforge-mcp command."""

from __future__ import annotations

import argparse
import asyncio

from dataforge_mcp.config import get_settings
from dataforge_mcp.logging import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DataForge Semantic MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=None,
        help="Transport mode (default: from config)",
    )
    parser.add_argument("--host", default=None, help="Host for SSE transport")
    parser.add_argument("--port", type=int, default=None, help="Port for SSE transport")
    parser.add_argument("--log-level", default=None, help="Log level")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()

    if args.transport:
        settings.mcp_transport = args.transport
    if args.host:
        settings.host = args.host
    if args.port:
        settings.port = args.port
    if args.log_level:
        settings.log_level = args.log_level

    setup_logging(settings.log_level)

    from dataforge_mcp.mcp.server import create_mcp_server

    server = create_mcp_server(settings)

    if settings.mcp_transport == "sse":
        from dataforge_mcp.transport.sse import run_sse

        asyncio.run(run_sse(server, settings))
    else:
        from dataforge_mcp.transport.stdio import run_stdio

        asyncio.run(run_stdio(server))
