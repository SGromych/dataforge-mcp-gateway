"""Tool-argument preparation: what the agent is allowed to send, and what it is told.

Both halves come from a live integration: a client kept its ids as strings and every
call was rejected, and the rejection arrived as a bare sentence instead of the error
envelope this server documents, so the agent could not repair the call.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from mcp import Client

from dataforge_mcp.config import Settings
from dataforge_mcp.errors import DataForgeError, ErrorCode
from dataforge_mcp.mcp.arguments import prepare_arguments
from dataforge_mcp.mcp.server import create_mcp_server
from dataforge_mcp.mcp.tools import _build_tools
from tests.fixtures import api_v2 as fx

SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {"type": "integer"},
        "version_id": {"type": "integer"},
        "ratio": {"type": "number"},
        "use_cache": {"type": "boolean"},
        "language": {"type": "string"},
        "mode": {"type": "string", "enum": ["create", "replace", "update"]},
        "required_flag": {"type": "string", "enum": ["true", "false"]},
        "options": {"type": "object", "properties": {"include_rmd": {"type": "boolean"}}},
        "ids": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["project_id", "version_id"],
}

TOOLS_BY_NAME = {tool.name: tool for tool in _build_tools("ru")}


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        dataforge_base_url="https://api.test.example.com",
        dataforge_api_key="test-api-key-12345",
        cache_dir=str(tmp_path / "cache"),
    )


# ---------------------------------------------------------------------------
# Coercion
# ---------------------------------------------------------------------------


def test_string_ids_are_accepted() -> None:
    prepared = prepare_arguments(SCHEMA, {"project_id": "18", "version_id": " 948 "})
    assert prepared == {"project_id": 18, "version_id": 948}


def test_numbers_and_booleans_are_coerced() -> None:
    prepared = prepare_arguments(
        SCHEMA,
        {
            "project_id": 18,
            "version_id": 948.0,
            "ratio": "1.5",
            "use_cache": "false",
            "language": 42,
        },
    )
    assert prepared["version_id"] == 948
    assert prepared["ratio"] == 1.5
    assert prepared["use_cache"] is False
    assert prepared["language"] == "42"


def test_boolean_for_a_reference_column_becomes_its_label() -> None:
    """Reference columns travel as the strings "true"/"false" (see CLAUDE.md)."""
    prepared = prepare_arguments(SCHEMA, {"project_id": 1, "version_id": 1, "required_flag": True})
    assert prepared["required_flag"] == "true"


def test_nested_objects_and_arrays_are_coerced_too() -> None:
    prepared = prepare_arguments(
        SCHEMA,
        {
            "project_id": 1,
            "version_id": 1,
            "options": {"include_rmd": "true"},
            "ids": ["1", "2"],
        },
    )
    assert prepared["options"] == {"include_rmd": True}
    assert prepared["ids"] == [1, 2]


def test_values_that_are_already_right_are_untouched() -> None:
    args = {"project_id": 392, "version_id": 948, "mode": "update", "use_cache": True}
    assert prepare_arguments(SCHEMA, args) == args


# ---------------------------------------------------------------------------
# Rejection, in the documented envelope
# ---------------------------------------------------------------------------


def test_unconvertible_value_is_reported_with_the_field() -> None:
    with pytest.raises(DataForgeError) as exc_info:
        prepare_arguments(SCHEMA, {"project_id": "not-an-int", "version_id": 948})

    error = exc_info.value
    assert error.code is ErrorCode.DATAFORGE_VALIDATION_FAILED
    assert error.field_errors == [
        {
            "field": "project_id",
            "code": "invalid_value",
            "expected": "integer",
            "received": "str",
        }
    ]
    assert error.hint


def test_missing_required_arguments_are_all_listed_at_once() -> None:
    with pytest.raises(DataForgeError) as exc_info:
        prepare_arguments(SCHEMA, {})

    fields = exc_info.value.field_errors
    assert [f["field"] for f in fields] == ["project_id", "version_id"]
    assert {f["code"] for f in fields} == {"missing_field"}


def test_unknown_argument_is_named() -> None:
    with pytest.raises(DataForgeError) as exc_info:
        prepare_arguments(SCHEMA, {"project_id": 1, "version_id": 1, "projectId": 1})

    assert exc_info.value.field_errors == [{"field": "projectId", "code": "unknown_field"}]


def test_value_outside_the_enum_is_rejected_with_the_catalogue() -> None:
    with pytest.raises(DataForgeError) as exc_info:
        prepare_arguments(SCHEMA, {"project_id": 1, "version_id": 1, "mode": "upsert"})

    field = exc_info.value.field_errors[0]
    assert field["field"] == "mode"
    assert "create" in field["expected"]


def test_a_boolean_is_not_an_integer() -> None:
    """`True` is an int in Python; it is not a project id anywhere."""
    with pytest.raises(DataForgeError):
        prepare_arguments(SCHEMA, {"project_id": True, "version_id": 1})


# ---------------------------------------------------------------------------
# The same rules over the real protocol
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_real_tool_accepts_string_ids_over_mcp(settings: Settings) -> None:
    """The exact call that used to be rejected: ids kept as strings by the client."""
    route = respx.get("https://api.test.example.com/df-api/v2/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=fx.RMD_EXPORT_200)
    )

    server = create_mcp_server(settings)
    async with Client(server) as client:
        result = await client.call_tool(
            "df_refresh_cache", {"project_id": "392", "version_id": "948"}
        )

    # The coerced ids reached the URL as numbers, not as quoted strings.
    assert route.called

    payload = json.loads(result.content[0].text)
    assert "error" not in payload
    assert result.is_error is False


@pytest.mark.asyncio
async def test_invalid_argument_reaches_the_agent_as_an_error_envelope(
    settings: Settings,
) -> None:
    server = create_mcp_server(settings)
    async with Client(server) as client:
        result = await client.call_tool("df_get_measures", {"project_id": "abc"})

    assert result.is_error is True
    error = json.loads(result.content[0].text)["error"]
    assert error["code"] == "DATAFORGE_VALIDATION_FAILED"
    assert {f["field"] for f in error["fields"]} == {"project_id", "version_id"}
    assert error["hint"]


def test_every_tool_schema_can_be_prepared() -> None:
    """Schema shapes the preparer must understand, checked against all 65 tools."""
    for tool in TOOLS_BY_NAME.values():
        properties = tool.input_schema.get("properties", {})
        assert isinstance(properties, dict)
        # Required names must exist as properties, or a caller could never satisfy them.
        for name in tool.input_schema.get("required", []):
            assert name in properties, f"{tool.name}.{name}"
