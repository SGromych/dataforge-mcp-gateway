"""MCP tool registration — thin wrappers delegating to SemanticService."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from dataforge_mcp.application.use_cases import SemanticService
from dataforge_mcp.errors import DataForgeError


def _build_tools(default_language: str) -> list[Tool]:
    """Build tool definitions using the configured default language."""
    pv_required = ["project_id", "version_id"]
    return [
        # -------------------------------------------------------------------
        # Existing RMD API tools
        # -------------------------------------------------------------------
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
            description=(
                "Get measures (metrics) for a project version."
                " Set include_sql=true to get generated SQL code for each measure."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "include_sql": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include generated SQL code for each measure",
                    },
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": pv_required,
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
                    "language": {"type": "string", "default": default_language},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": pv_required,
            },
        ),
        Tool(
            name="df_get_facts",
            description="Get facts for a project version.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": pv_required,
            },
        ),
        Tool(
            name="df_get_rmd",
            description="Get full RMD (measures + dimensions + facts) for a project version.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "use_cache": {"type": "boolean", "default": True},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": pv_required,
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
                    "language": {"type": "string", "default": default_language},
                },
                "required": pv_required,
            },
        ),
        # -------------------------------------------------------------------
        # DF API tools — Data Marts
        # -------------------------------------------------------------------
        Tool(
            name="df_list_data_marts",
            description=(
                "List data marts for a project version."
                " Supports filtering by type, merge_type, and search."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "type": {"type": "string", "description": "Filter by data mart type"},
                    "merge_type": {"type": "string", "description": "Filter by merge type"},
                    "search": {"type": "string", "description": "Search data marts by name"},
                    "page": {"type": "integer", "default": 1},
                    "page_size": {"type": "integer", "default": 100},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": pv_required,
            },
        ),
        Tool(
            name="df_get_data_mart",
            description=(
                "Get data mart details including selected measures,"
                " dimensions, facts, and source fact tables."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "data_mart_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": [*pv_required, "data_mart_id"],
            },
        ),
        Tool(
            name="df_get_data_mart_view",
            description="Get physical view metadata for a data mart.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "data_mart_id": {"type": "integer"},
                },
                "required": [*pv_required, "data_mart_id"],
            },
        ),
        Tool(
            name="df_generate_sql",
            description="Generate SQL script for a data mart (read-only, not executed).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "data_mart_id": {"type": "integer"},
                    "limit": {"type": "integer", "description": "Row limit for generated SQL"},
                    "offset": {"type": "integer", "description": "Row offset for generated SQL"},
                },
                "required": [*pv_required, "data_mart_id"],
            },
        ),
        # -------------------------------------------------------------------
        # DF API tools — Connections
        # -------------------------------------------------------------------
        Tool(
            name="df_list_connections",
            description=(
                "List database connections for a project version."
                " Supports filtering by db_type and status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "db_type": {"type": "string", "description": "Filter by database type"},
                    "status": {"type": "string", "description": "Filter by connection status"},
                    "page": {"type": "integer", "default": 1},
                    "page_size": {"type": "integer", "default": 100},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": pv_required,
            },
        ),
        Tool(
            name="df_get_connection",
            description="Get connection details. Optionally include database schema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "connection_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "include_db_schema": {"type": "boolean", "default": False},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": [*pv_required, "connection_id"],
            },
        ),
        Tool(
            name="df_get_connection_schema",
            description="Get database schema snapshot for a connection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "connection_id": {"type": "integer"},
                },
                "required": [*pv_required, "connection_id"],
            },
        ),
        # -------------------------------------------------------------------
        # DF API tools — Dimension Groups
        # -------------------------------------------------------------------
        Tool(
            name="df_list_dimension_groups",
            description="List dimension groups for a project version.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "page": {"type": "integer", "default": 1},
                    "page_size": {"type": "integer", "default": 100},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": pv_required,
            },
        ),
        Tool(
            name="df_get_dimension_group",
            description=(
                "Get dimension group details including dimensions and related fact tables."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "dimension_group_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": [*pv_required, "dimension_group_id"],
            },
        ),
        # -------------------------------------------------------------------
        # DF API tools — Fact Tables
        # -------------------------------------------------------------------
        Tool(
            name="df_list_fact_tables",
            description="List fact tables for a project version.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "page": {"type": "integer", "default": 1},
                    "page_size": {"type": "integer", "default": 100},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": pv_required,
            },
        ),
        Tool(
            name="df_get_fact_table",
            description=(
                "Get fact table details including measures, dimensions,"
                " facts, dimension groups, and verification filters."
                " Set include_dependencies=true to get measure dependency trees."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "fact_table_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "include_dependencies": {"type": "boolean", "default": False},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": [*pv_required, "fact_table_id"],
            },
        ),
        # -------------------------------------------------------------------
        # DF API tools — Relationships
        # -------------------------------------------------------------------
        Tool(
            name="df_list_relationships",
            description=(
                "List relationships for a project version."
                " Supports filtering by fact_table_id and dimension_group_id."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "fact_table_id": {"type": "integer", "description": "Filter by fact table"},
                    "dimension_group_id": {
                        "type": "integer",
                        "description": "Filter by dimension group",
                    },
                    "page": {"type": "integer", "default": 1},
                    "page_size": {"type": "integer", "default": 100},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": pv_required,
            },
        ),
        Tool(
            name="df_get_relationship",
            description="Get relationship details between a fact table and a dimension group.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "relationship_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": [*pv_required, "relationship_id"],
            },
        ),
        # -------------------------------------------------------------------
        # DF API tools — Consolidated RMD
        # -------------------------------------------------------------------
        Tool(
            name="df_get_consolidated_rmd",
            description=(
                "Get consolidated RMD export: project,"
                " version, measures, dimensions, facts, dimension"
                " groups, fact tables, relationships."
                " Set include_sql=true to include generated SQL code for measures."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "version_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    "include_sql": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include generated SQL code for measures",
                    },
                    "use_cache": {"type": "boolean", "default": True},
                },
                "required": pv_required,
            },
        ),
    ]


def register_tools(server: Server, service: SemanticService) -> None:
    tools = _build_tools(service.settings.default_language)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            result = await _dispatch(name, arguments, service)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        except DataForgeError as exc:
            return [TextContent(type="text", text=json.dumps(exc.to_dict(), ensure_ascii=False))]


async def _dispatch(name: str, args: dict[str, Any], service: SemanticService) -> dict[str, Any]:
    match name:
        # ---------------------------------------------------------------
        # Existing RMD API tools
        # ---------------------------------------------------------------
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
                include_sql=args.get("include_sql", False),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_dimensions":
            return await service.get_dimensions(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_facts":
            return await service.get_facts(
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
        # ---------------------------------------------------------------
        # DF API — Data Marts
        # ---------------------------------------------------------------
        case "df_list_data_marts":
            return await service.list_data_marts(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
                page=args.get("page", 1),
                page_size=args.get("page_size", 100),
                type=args.get("type"),
                merge_type=args.get("merge_type"),
                search=args.get("search"),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_data_mart":
            return await service.get_data_mart(
                project_id=args["project_id"],
                version_id=args["version_id"],
                data_mart_id=args["data_mart_id"],
                language=args.get("language"),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_data_mart_view":
            return await service.get_data_mart_view(
                project_id=args["project_id"],
                version_id=args["version_id"],
                data_mart_id=args["data_mart_id"],
            )
        case "df_generate_sql":
            return await service.generate_sql(
                project_id=args["project_id"],
                version_id=args["version_id"],
                data_mart_id=args["data_mart_id"],
                limit=args.get("limit"),
                offset=args.get("offset"),
            )
        # ---------------------------------------------------------------
        # DF API — Connections
        # ---------------------------------------------------------------
        case "df_list_connections":
            return await service.list_connections(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
                page=args.get("page", 1),
                page_size=args.get("page_size", 100),
                db_type=args.get("db_type"),
                status=args.get("status"),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_connection":
            return await service.get_connection(
                project_id=args["project_id"],
                version_id=args["version_id"],
                connection_id=args["connection_id"],
                language=args.get("language"),
                include_db_schema=args.get("include_db_schema", False),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_connection_schema":
            return await service.get_connection_schema(
                project_id=args["project_id"],
                version_id=args["version_id"],
                connection_id=args["connection_id"],
            )
        # ---------------------------------------------------------------
        # DF API — Dimension Groups
        # ---------------------------------------------------------------
        case "df_list_dimension_groups":
            return await service.list_dimension_groups(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
                page=args.get("page", 1),
                page_size=args.get("page_size", 100),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_dimension_group":
            return await service.get_dimension_group(
                project_id=args["project_id"],
                version_id=args["version_id"],
                dimension_group_id=args["dimension_group_id"],
                language=args.get("language"),
                use_cache=args.get("use_cache", True),
            )
        # ---------------------------------------------------------------
        # DF API — Fact Tables
        # ---------------------------------------------------------------
        case "df_list_fact_tables":
            return await service.list_fact_tables(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
                page=args.get("page", 1),
                page_size=args.get("page_size", 100),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_fact_table":
            return await service.get_fact_table(
                project_id=args["project_id"],
                version_id=args["version_id"],
                fact_table_id=args["fact_table_id"],
                language=args.get("language"),
                include_dependencies=args.get("include_dependencies", False),
                use_cache=args.get("use_cache", True),
            )
        # ---------------------------------------------------------------
        # DF API — Relationships
        # ---------------------------------------------------------------
        case "df_list_relationships":
            return await service.list_relationships(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
                page=args.get("page", 1),
                page_size=args.get("page_size", 100),
                fact_table_id=args.get("fact_table_id"),
                dimension_group_id=args.get("dimension_group_id"),
                use_cache=args.get("use_cache", True),
            )
        case "df_get_relationship":
            return await service.get_relationship(
                project_id=args["project_id"],
                version_id=args["version_id"],
                relationship_id=args["relationship_id"],
                language=args.get("language"),
                use_cache=args.get("use_cache", True),
            )
        # ---------------------------------------------------------------
        # DF API — Consolidated RMD
        # ---------------------------------------------------------------
        case "df_get_consolidated_rmd":
            return await service.get_consolidated_rmd(
                project_id=args["project_id"],
                version_id=args["version_id"],
                language=args.get("language"),
                include_sql=args.get("include_sql", False),
                use_cache=args.get("use_cache", True),
            )
        case _:
            return {"error": {"code": "UNKNOWN_TOOL", "message": f"Unknown tool: {name}"}}
