"""End-to-end MCP tests over the real protocol, without a network or a subprocess.

`create_connected_server_and_client_session` wires a client and the server together
in memory, so these tests exercise initialize / list_tools / call_tool exactly as a
real MCP client would.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from mcp.shared.memory import create_connected_server_and_client_session

from dataforge_mcp.config import Settings
from dataforge_mcp.mcp.server import create_mcp_server
from dataforge_mcp.mcp.tools import HANDLERS, _dispatch
from tests.fixtures import api_v2 as fx

BASE = "https://api.test.example.com"
PFX = f"{BASE}/df-api/v2/projects/392/versions/948"
API_KEY = "test-api-key-12345"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        dataforge_base_url=BASE,
        dataforge_api_key=API_KEY,
        default_language="ru",
        cache_dir=str(tmp_path / "cache"),
        cache_ttl_seconds=60,
        mcp_server_name="dataforge-semantic",
    )


def payload_of(result) -> dict:
    return json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_initialize_and_list_tools(settings: Settings) -> None:
    server = create_mcp_server(settings)
    async with create_connected_server_and_client_session(server) as client:
        listing = await client.list_tools()

    names = {t.name for t in listing.tools}
    assert names == set(HANDLERS)
    assert "df_get_measures" in names
    assert "df_write_measure" in names


@respx.mock
@pytest.mark.asyncio
async def test_call_tool_returns_json_text(settings: Settings) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=fx.PROJECTS_200)
    )
    server = create_mcp_server(settings)
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("df_list_projects", {"page": 1})

    data = payload_of(result)
    assert [p["name"] for p in data["projects"]] == ["Sales Analytics", "Finance"]


@respx.mock
@pytest.mark.asyncio
async def test_api_error_is_returned_without_leaking_the_key(settings: Settings) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions").mock(
        return_value=httpx.Response(404, json=fx.ERR_404_PROJECT)
    )
    server = create_mcp_server(settings)
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("df_list_versions", {"project_id": 392})

    text = result.content[0].text
    assert API_KEY not in text
    error = json.loads(text)["error"]
    assert error["code"] == "DATAFORGE_PROJECT_NOT_FOUND"
    assert error["api_code"] == "project_not_found"


@respx.mock
@pytest.mark.asyncio
async def test_validation_error_reaches_the_agent_with_fields(settings: Settings) -> None:
    """A rejected write must tell the agent which field to fix."""
    respx.post(f"{PFX}/measures").mock(
        return_value=httpx.Response(400, json=fx.ERR_400_VALIDATION_FAILED)
    )
    server = create_mcp_server(settings)
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool(
            "df_write_measure",
            {
                "project_id": 392,
                "version_id": 948,
                "measure_name": "Total revenue",
                "measure_type": "Base",
            },
        )

    error = payload_of(result)["error"]
    assert error["code"] == "DATAFORGE_VALIDATION_FAILED"
    assert error["fields"][0]["field"] == "measures.1.measure_type"


@pytest.mark.asyncio
async def test_local_validation_uses_the_same_error_shape(settings: Settings) -> None:
    """Local and server-side rejections must be indistinguishable to the agent."""
    server = create_mcp_server(settings)
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool(
            "df_write_measure",
            {
                "project_id": 392,
                "version_id": 948,
                "measure_name": "X",
                "typo_field": "boom",
            },
        )

    error = payload_of(result)["error"]
    assert error["code"] == "DATAFORGE_VALIDATION_FAILED"
    assert error["fields"][0]["code"] == "unknown_field"


@pytest.mark.asyncio
async def test_bad_argument_type_does_not_kill_the_session(settings: Settings) -> None:
    server = create_mcp_server(settings)
    async with create_connected_server_and_client_session(server) as client:
        bad = await client.call_tool("df_list_versions", {"project_id": "not-an-int"})
        assert bad.isError or "error" in bad.content[0].text

        # The session survives and still answers.
        listing = await client.list_tools()
        assert listing.tools


@respx.mock
@pytest.mark.asyncio
async def test_write_tool_end_to_end(settings: Settings) -> None:
    respx.post(f"{PFX}/measures").mock(
        return_value=httpx.Response(201, json=fx.MEASURE_CREATED_201)
    )
    server = create_mcp_server(settings)
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool(
            "df_write_measure",
            {
                "project_id": 392,
                "version_id": 948,
                "mode": "create",
                "measure_name": "Total revenue",
                "measure_type": "Base",
            },
        )

    data = payload_of(result)
    assert data["status"] == "created"
    assert data["result"]["id"] == "1000"
    assert data["idempotency_key"]


@respx.mock
@pytest.mark.asyncio
async def test_health_reports_api_and_cache(settings: Settings) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=fx.PROJECTS_200)
    )
    server = create_mcp_server(settings)
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("df_health", {})

    data = payload_of(result)
    assert data["server_status"] == "ok"
    assert data["product_api_status"] == "ok"
    assert data["cache_status"] == "ok"


@pytest.mark.asyncio
async def test_unknown_tool_is_reported(settings: Settings) -> None:
    from dataforge_mcp import create_semantic_service

    service = create_semantic_service(settings)
    result = await _dispatch("df_not_a_tool", {}, service)
    assert result["error"]["code"] == "UNKNOWN_TOOL"


@pytest.mark.asyncio
async def test_missing_required_argument_is_a_clean_error(settings: Settings) -> None:
    server = create_mcp_server(settings)
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool("df_delete_measure", {"project_id": 392})

    text = result.content[0].text
    assert "version_id" in text or "missing" in text.lower()


@respx.mock
@pytest.mark.asyncio
async def test_secrets_never_appear_in_tool_output(settings: Settings) -> None:
    """Git credentials go out on the wire but must never come back to the agent."""
    respx.post(f"{PFX}/export/git").mock(return_value=httpx.Response(200, json=fx.EXPORT_GIT_200))
    server = create_mcp_server(settings)
    async with create_connected_server_and_client_session(server) as client:
        result = await client.call_tool(
            "df_export_version_to_git",
            {
                "project_id": 392,
                "version_id": 948,
                "repository_url": "https://gitlab.example.com/x.git",
                "branch": "main",
                "commit_message": "Export",
                "authentication": {"method": "pat", "token": "super-secret-token"},
            },
        )

    text = result.content[0].text
    assert "super-secret-token" not in text
    assert API_KEY not in text
