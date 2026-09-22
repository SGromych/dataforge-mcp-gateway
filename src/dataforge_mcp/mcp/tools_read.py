"""Read-only MCP tools. All of them carry ``readOnlyHint=True``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.types import Tool, ToolAnnotations

from dataforge_mcp.application.use_cases import SemanticService

from .schema_fragments import (
    CONNECTION_STATUSES,
    DATA_MART_TYPES,
    DB_TYPES,
    MERGE_TYPES,
    PV_REQUIRED,
    obj,
    paging_props,
    pv_props,
)

Handler = Callable[[dict[str, Any], SemanticService], Awaitable[dict[str, Any]]]

_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)

_USE_CACHE = {"use_cache": {"type": "boolean", "default": True}}


def build_read_tools(default_language: str) -> list[Tool]:
    pv = pv_props(default_language)

    return [
        Tool(
            name="df_health",
            description="Check server health, DataForge API connectivity and cache status.",
            inputSchema=obj({}),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_list_projects",
            description="List DataForge projects visible to the configured API key.",
            inputSchema=obj({**paging_props(), **_USE_CACHE}),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_list_versions",
            description="List versions of a DataForge project.",
            inputSchema=obj(
                {
                    "project_id": {"type": "integer"},
                    **paging_props(),
                    **_USE_CACHE,
                },
                ["project_id"],
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_measures",
            description=(
                "Get all measures (business metrics) of a project version, paged through"
                " automatically. Each measure carries a stable `id` that the write tools"
                " accept. Set include_sql=true to also get generated SQL per measure."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "include_sql": {"type": "boolean", "default": False},
                    **_USE_CACHE,
                },
                PV_REQUIRED,
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_dimensions",
            description=(
                "Get all dimensions of a project version. Each dimension carries a stable"
                " `id` and, where bound to a database, a `connected_source` naming its"
                " connection, table and column."
            ),
            inputSchema=obj({**pv, **_USE_CACHE}, PV_REQUIRED),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_facts",
            description="Get all facts of a project version.",
            inputSchema=obj({**pv, **_USE_CACHE}, PV_REQUIRED),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_rmd",
            description=(
                "Get the normalized semantic context of a project version: project,"
                " version, measures, dimensions, facts and counts. Shares one API call"
                " and one cache entry with df_get_consolidated_rmd."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "include_sql": {"type": "boolean", "default": False},
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                        "description": "Keep the untouched API payload of every row",
                    },
                    **_USE_CACHE,
                },
                PV_REQUIRED,
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_consolidated_rmd",
            description=(
                "Get the full raw export of a project version: RMD content plus dimension"
                " groups, fact tables and relationships in one payload."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "include_sql": {"type": "boolean", "default": False},
                    **_USE_CACHE,
                },
                PV_REQUIRED,
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_refresh_cache",
            description=(
                "Drop the cached state of a project version (or the whole project) and"
                " re-fetch its RMD snapshot."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "scope": {
                        "type": "string",
                        "enum": ["version", "project", "global"],
                        "default": "version",
                    },
                },
                PV_REQUIRED,
            ),
            annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=False, idempotentHint=True
            ),
        ),
        # -- data marts ------------------------------------------------------
        Tool(
            name="df_list_data_marts",
            description="List data marts of a project version.",
            inputSchema=obj(
                {
                    **pv,
                    "mart_type": {"type": "string", "enum": DATA_MART_TYPES},
                    "merge_type": {"type": "string", "enum": MERGE_TYPES},
                    "search": {
                        "type": "string",
                        "description": "Case-insensitive substring of name or description",
                    },
                    **paging_props(),
                    **_USE_CACHE,
                },
                PV_REQUIRED,
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_data_mart",
            description=(
                "Get one data mart in full: source fact tables, selected measures, facts"
                " and dimensions with their aggregation and filter settings."
            ),
            inputSchema=obj(
                {**pv, "data_mart_id": {"type": "integer"}, **_USE_CACHE},
                [*PV_REQUIRED, "data_mart_id"],
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_data_mart_view",
            description=(
                "Get the physical view materialized for a data mart: existence, object"
                " type, database, status, staleness and last refresh."
            ),
            inputSchema=obj(
                {**pv, "data_mart_id": {"type": "integer"}, **_USE_CACHE},
                [*PV_REQUIRED, "data_mart_id"],
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_generate_sql",
            description=(
                "Generate the SQL query of a data mart. Nothing is executed and nothing is"
                " stored. A generation failure comes back as succeeded=false with"
                " validation_errors, not as an error."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "data_mart_id": {"type": "integer"},
                    "limit": {"type": "integer", "minimum": 1},
                    "offset": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Ignored unless limit is also given",
                    },
                },
                [*PV_REQUIRED, "data_mart_id"],
            ),
            annotations=_READ_ONLY,
        ),
        # -- connections -----------------------------------------------------
        Tool(
            name="df_list_connections",
            description=(
                "List database connections of a project version. Credentials are never"
                " returned. Unsupported engines (e.g. MySQL) are excluded entirely."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "db_type": {"type": "string", "enum": DB_TYPES},
                    "status": {"type": "string", "enum": CONNECTION_STATUSES},
                    **paging_props(),
                    **_USE_CACHE,
                },
                PV_REQUIRED,
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_connection",
            description=(
                "Get one connection: host, port, database, schema and username."
                " Set include_db_schema=true to get the full cached table/column schema."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "connection_id": {"type": "integer"},
                    "include_db_schema": {"type": "boolean", "default": False},
                    **_USE_CACHE,
                },
                [*PV_REQUIRED, "connection_id"],
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_connection_schema",
            description=(
                "Get the cached schema of a connection (tables and columns). This is a"
                " snapshot taken when the connection was last refreshed, not a live query."
                " Use it to pick valid table and column names for write operations."
            ),
            inputSchema=obj(
                {**pv, "connection_id": {"type": "integer"}, **_USE_CACHE},
                [*PV_REQUIRED, "connection_id"],
            ),
            annotations=_READ_ONLY,
        ),
        # -- data model ------------------------------------------------------
        Tool(
            name="df_list_dimension_groups",
            description="List dimension groups (shared reference hierarchies) of a version.",
            inputSchema=obj({**pv, **paging_props(), **_USE_CACHE}, PV_REQUIRED),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_dimension_group",
            description=(
                "Get one dimension group: primary key, member dimensions with their"
                " hierarchy levels, and the fact tables related to it."
            ),
            inputSchema=obj(
                {**pv, "dimension_group_id": {"type": "integer"}, **_USE_CACHE},
                [*PV_REQUIRED, "dimension_group_id"],
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_list_fact_tables",
            description="List fact tables of a project version with element counts.",
            inputSchema=obj({**pv, **paging_props(), **_USE_CACHE}, PV_REQUIRED),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_fact_table",
            description=(
                "Get one fact table: assigned measures, dimensions, facts, dimension"
                " groups and verification filters. Set include_dependencies=true to get"
                " the formula dependency tree of each measure."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "fact_table_id": {"type": "integer"},
                    "include_dependencies": {"type": "boolean", "default": False},
                    **_USE_CACHE,
                },
                [*PV_REQUIRED, "fact_table_id"],
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_list_relationships",
            description=(
                "List star-schema relationships (fact table to dimension group joins)."
                " relationship_type is the raw slug many_to_one."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "fact_table_id": {"type": "integer"},
                    "dimension_group_id": {"type": "integer"},
                    **paging_props(),
                    **_USE_CACHE,
                },
                PV_REQUIRED,
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_relationship",
            description="Get one relationship with its foreign and primary key source objects.",
            inputSchema=obj(
                {**pv, "relationship_id": {"type": "integer"}, **_USE_CACHE},
                [*PV_REQUIRED, "relationship_id"],
            ),
            annotations=_READ_ONLY,
        ),
        # -- access and Git registry ----------------------------------------
        Tool(
            name="df_get_project_access",
            description="List the owner and every user with explicit access to a project.",
            inputSchema=obj(
                {
                    "project_id": {"type": "integer"},
                    "language": {"type": "string", "default": default_language},
                    **_USE_CACHE,
                },
                ["project_id"],
            ),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_list_git_connections",
            description=(
                "List the company's saved Git connections. Credentials are never returned."
                " Requires a company administrator API key."
            ),
            inputSchema=obj({**paging_props(), **_USE_CACHE}),
            annotations=_READ_ONLY,
        ),
        Tool(
            name="df_get_git_connection",
            description="Get one saved Git connection.",
            inputSchema=obj(
                {"connection_id": {"type": "integer"}, **_USE_CACHE}, ["connection_id"]
            ),
            annotations=_READ_ONLY,
        ),
    ]


READ_HANDLERS: dict[str, Handler] = {
    "df_health": lambda a, s: s.check_health(),
    "df_list_projects": lambda a, s: s.list_projects(
        page=a.get("page", 1),
        page_size=a.get("page_size", 100),
        use_cache=a.get("use_cache", True),
    ),
    "df_list_versions": lambda a, s: s.list_versions(
        project_id=a["project_id"],
        page=a.get("page", 1),
        page_size=a.get("page_size", 100),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_measures": lambda a, s: s.get_measures(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        include_sql=a.get("include_sql", False),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_dimensions": lambda a, s: s.get_dimensions(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_facts": lambda a, s: s.get_facts(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_rmd": lambda a, s: s.get_rmd(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        include_sql=a.get("include_sql", False),
        use_cache=a.get("use_cache", True),
        include_raw=a.get("include_raw", False),
    ),
    "df_get_consolidated_rmd": lambda a, s: s.get_consolidated_rmd(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        include_sql=a.get("include_sql", False),
        use_cache=a.get("use_cache", True),
    ),
    "df_refresh_cache": lambda a, s: s.refresh_cache(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        scope=a.get("scope", "version"),
    ),
    "df_list_data_marts": lambda a, s: s.list_data_marts(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        page=a.get("page", 1),
        page_size=a.get("page_size", 100),
        mart_type=a.get("mart_type"),
        merge_type=a.get("merge_type"),
        search=a.get("search"),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_data_mart": lambda a, s: s.get_data_mart(
        project_id=a["project_id"],
        version_id=a["version_id"],
        data_mart_id=a["data_mart_id"],
        language=a.get("language"),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_data_mart_view": lambda a, s: s.get_data_mart_view(
        project_id=a["project_id"],
        version_id=a["version_id"],
        data_mart_id=a["data_mart_id"],
        language=a.get("language"),
        use_cache=a.get("use_cache", True),
    ),
    "df_generate_sql": lambda a, s: s.generate_sql(
        project_id=a["project_id"],
        version_id=a["version_id"],
        data_mart_id=a["data_mart_id"],
        limit=a.get("limit"),
        offset=a.get("offset"),
        language=a.get("language"),
    ),
    "df_list_connections": lambda a, s: s.list_connections(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        page=a.get("page", 1),
        page_size=a.get("page_size", 100),
        db_type=a.get("db_type"),
        status=a.get("status"),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_connection": lambda a, s: s.get_connection(
        project_id=a["project_id"],
        version_id=a["version_id"],
        connection_id=a["connection_id"],
        language=a.get("language"),
        include_db_schema=a.get("include_db_schema", False),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_connection_schema": lambda a, s: s.get_connection_schema(
        project_id=a["project_id"],
        version_id=a["version_id"],
        connection_id=a["connection_id"],
        language=a.get("language"),
        use_cache=a.get("use_cache", True),
    ),
    "df_list_dimension_groups": lambda a, s: s.list_dimension_groups(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        page=a.get("page", 1),
        page_size=a.get("page_size", 100),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_dimension_group": lambda a, s: s.get_dimension_group(
        project_id=a["project_id"],
        version_id=a["version_id"],
        dimension_group_id=a["dimension_group_id"],
        language=a.get("language"),
        use_cache=a.get("use_cache", True),
    ),
    "df_list_fact_tables": lambda a, s: s.list_fact_tables(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        page=a.get("page", 1),
        page_size=a.get("page_size", 100),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_fact_table": lambda a, s: s.get_fact_table(
        project_id=a["project_id"],
        version_id=a["version_id"],
        fact_table_id=a["fact_table_id"],
        language=a.get("language"),
        include_dependencies=a.get("include_dependencies", False),
        use_cache=a.get("use_cache", True),
    ),
    "df_list_relationships": lambda a, s: s.list_relationships(
        project_id=a["project_id"],
        version_id=a["version_id"],
        language=a.get("language"),
        page=a.get("page", 1),
        page_size=a.get("page_size", 100),
        fact_table_id=a.get("fact_table_id"),
        dimension_group_id=a.get("dimension_group_id"),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_relationship": lambda a, s: s.get_relationship(
        project_id=a["project_id"],
        version_id=a["version_id"],
        relationship_id=a["relationship_id"],
        language=a.get("language"),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_project_access": lambda a, s: s.get_project_access(
        project_id=a["project_id"],
        language=a.get("language"),
        use_cache=a.get("use_cache", True),
    ),
    "df_list_git_connections": lambda a, s: s.list_git_connections(
        page=a.get("page", 1),
        page_size=a.get("page_size", 100),
        use_cache=a.get("use_cache", True),
    ),
    "df_get_git_connection": lambda a, s: s.get_git_connection(
        connection_id=a["connection_id"],
        use_cache=a.get("use_cache", True),
    ),
}
