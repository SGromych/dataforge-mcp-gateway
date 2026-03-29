"""MCP tool registration — thin wrappers delegating to SemanticService."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from dataforge_mcp.application.use_cases import SemanticService
from dataforge_mcp.errors import DataForgeError

TOOLS = [
    Tool(
        name="df_health",
        description="Check DataForge MCP server health, API connectivity and cache status.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="df_list_projects",
        description="List available DataForge projects.",
        inputSchema={
            "type": "object",
            "properties": {
                "page": {"type": "integer", "default": 1},
                "page_size": {"type": "integer", "default": 100},
                "use_cache": {"type": "boolean", "default": True},
            },
            "required": [],
        },
    ),
    Tool(
        name="df_list_versions",
        description="List versions for a DataForge project.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "page": {"type": "integer", "default": 1},
                "page_size": {"type": "integer", "default": 100},
                "use_cache": {"type": "boolean", "default": True},
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="df_get_measures",
        description="Get measures (metrics) for a project version.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "version_id": {"type": "integer"},
                "language": {"type": "string", "default": "ru"},
                "use_cache": {"type": "boolean", "default": True},
            },
            "required": ["project_id", "version_id"],
        },
    ),
    Tool(
        name="df_get_dimensions",
        description="Get dimensions for a project version.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "version_id": {"type": "integer"},
                "language": {"type": "string", "default": "ru"},
                "use_cache": {"type": "boolean", "default": True},
            },
            "required": ["project_id", "version_id"],
        },
    ),
    Tool(
        name="df_get_rmd",
        description="Get full RMD (measures + dimensions) for a project version.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "version_id": {"type": "integer"},
                "language": {"type": "string", "default": "ru"},
                "use_cache": {"type": "boolean", "default": True},
                "include_raw": {"type": "boolean", "default": False},
            },
            "required": ["project_id", "version_id"],
        },
    ),
    Tool(
        name="df_refresh_cache",
        description="Force refresh cached RMD data for a project version.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer"},
                "version_id": {"type": "integer"},
                "language": {"type": "string", "default": "ru"},
            },
            "required": ["project_id", "version_id"],
        },
    ),
]


def register_tools(server: Server, service: SemanticService) -> None:
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            result = await _dispatch(name, arguments, service)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        except DataForgeError as exc:
            return [TextContent(type="text", text=json.dumps(exc.to_dict(), ensure_ascii=False))]


async def _dispatch(
    name: str, args: dict[str, Any], service: SemanticService
) -> dict[str, Any]:
    match name:
        case "df_health":
            return await service.check_health()
        case "df_list_projects":
            return await service.list_projects(
                page=args.get("page", 1),
                page_size=args.get("page_size", 100),
                use_cache=args.get("use_cache", True),
            )
        case "df_list_versions":
            return await service.list_versions(
                project_id=args["project_id"],
                page=args.get("page", 1),
                page_size=args.get("page_size", 100),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_measures":
            return await service.get_measures(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_dimensions":
            return await service.get_dimensions(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_rmd":
            return await service.get_rmd(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
                use_cache=args.get("use_cache", True),
                include_raw=args.get("include_raw", False),
            )
        case "df_refresh_cache":
            return await service.refresh_cache(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
            )
        case _:
            return {"error": {"code": "UNKNOWN_TOOL", "message": f"Unknown tool: {name}"}}
