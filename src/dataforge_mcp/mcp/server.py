"""MCP server factory."""

from __future__ import annotations

from mcp.server import Server

from dataforge_mcp import create_semantic_service
from dataforge_mcp.config import Settings

from .tools import register_tools


def create_mcp_server(settings: Settings) -> Server:
    server = Server(settings.mcp_server_name)
    service = create_semantic_service(settings)
    register_tools(server, service)
    return server
