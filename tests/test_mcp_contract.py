"""Contract of the MCP surface: registry, schemas and safety annotations.

This layer had no tests at all before, which is how a tool could lose its dispatch
branch or ship an invalid inputSchema without anything failing.
"""

from __future__ import annotations

import json

import jsonschema
import pytest
from mcp.types import Tool

from dataforge_mcp.mcp.tools import HANDLERS, _build_tools
from dataforge_mcp.mcp.tools_read import READ_HANDLERS
from dataforge_mcp.mcp.tools_write import WRITE_HANDLERS

TOOLS = _build_tools("ru")
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


def test_every_tool_has_a_handler_and_vice_versa() -> None:
    assert set(TOOLS_BY_NAME) == set(HANDLERS)


def test_read_and_write_handlers_do_not_overlap() -> None:
    assert not set(READ_HANDLERS) & set(WRITE_HANDLERS)


def test_tool_names_are_unique_and_prefixed() -> None:
    names = [t.name for t in TOOLS]
    assert len(names) == len(set(names))
    assert all(name.startswith("df_") for name in names)


def test_every_tool_has_a_description() -> None:
    assert all(t.description and len(t.description) > 20 for t in TOOLS)


@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t.name)
def test_input_schema_is_valid_json_schema(tool: Tool) -> None:
    """mcp >= 1.10 validates arguments server-side; a broken schema breaks the call."""
    jsonschema.Draft202012Validator.check_schema(tool.inputSchema)


@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t.name)
def test_required_properties_are_declared(tool: Tool) -> None:
    properties = tool.inputSchema.get("properties", {})
    for name in tool.inputSchema.get("required", []):
        assert name in properties, f"{tool.name}: required '{name}' is not a property"


@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t.name)
def test_tool_round_trips_and_serializes(tool: Tool) -> None:
    assert Tool.model_validate(tool.model_dump()).name == tool.name
    json.dumps(tool.model_dump())


# ---------------------------------------------------------------------------
# Safety annotations — this server has no write kill switch, so the hints a client
# shows to a human are the only pre-call warning.
# ---------------------------------------------------------------------------

_READ_TOOLS = {
    "df_health",
    "df_list_projects",
    "df_list_versions",
    "df_get_measures",
    "df_get_dimensions",
    "df_get_facts",
    "df_get_rmd",
    "df_get_consolidated_rmd",
    "df_list_data_marts",
    "df_get_data_mart",
    "df_get_data_mart_view",
    "df_generate_sql",
    "df_list_connections",
    "df_get_connection",
    "df_get_connection_schema",
    "df_list_dimension_groups",
    "df_get_dimension_group",
    "df_list_fact_tables",
    "df_get_fact_table",
    "df_list_relationships",
    "df_get_relationship",
    "df_get_project_access",
    "df_list_git_connections",
    "df_get_git_connection",
}


def test_every_tool_carries_annotations() -> None:
    assert all(t.annotations is not None for t in TOOLS)


@pytest.mark.parametrize("name", sorted(_READ_TOOLS))
def test_read_tools_are_marked_read_only(name: str) -> None:
    assert TOOLS_BY_NAME[name].annotations.readOnlyHint is True


def test_write_tools_are_not_marked_read_only() -> None:
    for tool in TOOLS:
        if tool.name not in _READ_TOOLS:
            assert tool.annotations.readOnlyHint is False, tool.name


def test_destructive_tools_are_flagged() -> None:
    """Anything that deletes or overwrites must warn the client."""
    destructive = {t.name for t in TOOLS if t.annotations.destructiveHint}
    for name in TOOLS_BY_NAME:
        if name.startswith(("df_delete_", "df_unassign_", "df_remove_")):
            assert name in destructive, name
    assert "df_import_version_from_git" in destructive
    assert "df_import_version_from_file" in destructive


def test_write_tool_descriptions_warn() -> None:
    for tool in TOOLS:
        if tool.name in _READ_TOOLS:
            continue
        if tool.name in {
            "df_refresh_cache",
            "df_check_import_source",
            "df_preview_import",
        }:
            continue  # these change no DataForge data
        assert "WRITES TO DATAFORGE" in tool.description or (
            "PERMANENTLY DELETES" in tool.description
        ), tool.name


def test_delete_project_spells_out_the_blast_radius() -> None:
    description = TOOLS_BY_NAME["df_delete_project"].description
    assert "ALL OF ITS VERSIONS" in description
    assert "cannot be undone" in description


# ---------------------------------------------------------------------------
# Filter enums must match the API catalogues
# ---------------------------------------------------------------------------


def test_filter_enums_match_the_documented_catalogues() -> None:
    marts = TOOLS_BY_NAME["df_list_data_marts"].inputSchema["properties"]
    assert marts["merge_type"]["enum"] == ["union", "join"]
    assert marts["mart_type"]["enum"] == [
        "with_grouping",
        "without_grouping",
        "with_grouping_and_pivoting",
    ]

    connections = TOOLS_BY_NAME["df_list_connections"].inputSchema["properties"]
    assert connections["db_type"]["enum"] == ["postgresql", "clickhouse", "sqlserver"]
    assert connections["status"]["enum"] == [
        "active",
        "inactive",
        "never_verified",
        "failed",
    ]

    assert TOOLS_BY_NAME["df_write_relationship"].inputSchema["properties"]["relationship_type"][
        "enum"
    ] == ["many_to_one"]


def test_generate_sql_bounds() -> None:
    props = TOOLS_BY_NAME["df_generate_sql"].inputSchema["properties"]
    assert props["limit"]["minimum"] == 1
    assert props["offset"]["minimum"] == 0


def test_page_size_is_capped_at_the_api_limit() -> None:
    props = TOOLS_BY_NAME["df_list_data_marts"].inputSchema["properties"]
    assert props["page_size"]["maximum"] == 100


def test_write_tools_expose_idempotency_key() -> None:
    for name in ("df_write_measure", "df_create_project", "df_bulk_write_measures"):
        assert "idempotency_key" in TOOLS_BY_NAME[name].inputSchema["properties"]


def test_mode_default_is_create() -> None:
    for name in ("df_write_measure", "df_write_dimension", "df_write_fact"):
        assert TOOLS_BY_NAME[name].inputSchema["properties"]["mode"]["default"] == "create"
