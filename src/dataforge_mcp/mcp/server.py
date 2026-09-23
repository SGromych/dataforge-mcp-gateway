"""MCP server factory."""

from __future__ import annotations

from mcp.server import Server

from dataforge_mcp import __version__, create_semantic_service
from dataforge_mcp.config import Settings

from .tools import build_tool_handlers


def create_mcp_server(settings: Settings) -> Server:
    """Build the low-level MCP server with the tool handlers wired in.

    SDK 2.x takes the protocol handlers as constructor arguments; the 1.x
    ``@server.list_tools()`` / ``@server.call_tool()`` decorators are gone.
    """
    service = create_semantic_service(settings)
    on_list_tools, on_call_tool = build_tool_handlers(service)

    return Server(
        settings.mcp_server_name,
        version=__version__,
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )
