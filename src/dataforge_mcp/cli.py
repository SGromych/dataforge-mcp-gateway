"""CLI entry point for dataforge-mcp command."""

from __future__ import annotations

import argparse
import asyncio

from dataforge_mcp.config import TRANSPORTS, get_settings
from dataforge_mcp.logging import setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dataforge-mcp",
        description=(
            "DataForge Semantic MCP Server. Exposes the DataForge semantic layer and "
            "data model to MCP clients. WARNING: 38 of the 65 tools write to DataForge, "
            "including permanent deletion; the API key's project role is the only limit."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=list(TRANSPORTS),
        default=None,
        help=(
            "Transport to serve. 'stdio' for Claude Desktop / Cursor, 'streamable-http' "
            "for Open WebUI and other HTTP clients, 'sse' is deprecated "
            "(default: MCP_TRANSPORT, or stdio)"
        ),
    )
    parser.add_argument(
        "--host", default=None, help="Bind address for the HTTP transports (default: HOST)"
    )
    parser.add_argument(
        "--port", type=int, default=None, help="Bind port for the HTTP transports (default: PORT)"
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Path of the MCP endpoint for streamable-http (default: MCP_HTTP_PATH, or /mcp)",
    )
    parser.add_argument(
        "--json-response",
        action="store_true",
        default=False,
        help="Answer POSTs with a single JSON object instead of an SSE stream",
    )
    parser.add_argument(
        "--stateless",
        action="store_true",
        default=False,
        help="Run without sessions: every request is independent, no Mcp-Session-Id is minted",
    )
    parser.add_argument("--log-level", default=None, help="Log level (default: LOG_LEVEL)")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main() -> None:
    args = parse_args()
    settings = get_settings()

    if args.transport:
        settings.mcp_transport = args.transport
    if args.host:
        settings.host = args.host
    if args.port:
        settings.port = args.port
    if args.path:
        settings.mcp_http_path = args.path
    if args.json_response:
        settings.mcp_json_response = True
    if args.stateless:
        settings.mcp_stateless = True
    if args.log_level:
        settings.log_level = args.log_level

    setup_logging(settings.log_level)

    from dataforge_mcp.mcp.server import create_mcp_server
    from dataforge_mcp.transport import run_transport

    server = create_mcp_server(settings)
    asyncio.run(run_transport(server, settings))
