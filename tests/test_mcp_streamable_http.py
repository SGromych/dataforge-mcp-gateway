"""Streamable HTTP transport tests, driven over a real ASGI stack.

No socket is bound and no lifespan runner is needed: `create_session_manager`
and `build_app` are separate, so the test enters the manager's context by hand
and speaks to the app through `httpx.ASGITransport`.

The protocol-level cases assert the wire contract an Open WebUI (or any
spec-conforming) client relies on; `test_end_to_end_*` drives the real MCP
client from the SDK over that same stack.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from dataforge_mcp.config import Settings
from dataforge_mcp.mcp.server import create_mcp_server
from dataforge_mcp.mcp.tools import HANDLERS
from dataforge_mcp.transport.streamable_http import (
    build_app,
    build_security_settings,
    create_session_manager,
)
from tests.fixtures import api_v2 as fx

BASE = "https://api.test.example.com"
API_KEY = "test-api-key-12345"
PROTOCOL_VERSION = "2025-06-18"

INIT_BODY: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "1.0"},
    },
}

BOTH_TYPES = "application/json, text/event-stream"


@pytest.fixture
def http_settings(tmp_path: Path) -> Settings:
    """Loopback bind, so the default Origin allow-list applies."""
    return Settings(
        dataforge_base_url=BASE,
        dataforge_api_key=API_KEY,
        default_language="ru",
        cache_dir=str(tmp_path / "cache"),
        cache_ttl_seconds=60,
        mcp_transport="streamable-http",
        host="127.0.0.1",
    )


@asynccontextmanager
async def running_app(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    """Serve the app in-process and yield a client pointed at it."""
    server = create_mcp_server(settings)
    manager = create_session_manager(server, settings)
    app = build_app(manager, settings)
    async with manager.run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:8080"
        ) as client:
            yield client


def mcp_headers(session_id: str | None = None, **extra: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": BOTH_TYPES}
    if session_id:
        headers["mcp-session-id"] = session_id
    headers.update(extra)
    return headers


async def initialize(client: httpx.AsyncClient, path: str = "/mcp") -> httpx.Response:
    return await client.post(path, json=INIT_BODY, headers=mcp_headers())


def sse_payloads(body: str) -> list[dict[str, Any]]:
    """Pull the JSON-RPC messages out of an SSE body."""
    return [
        json.loads(line[len("data:") :].strip())
        for line in body.splitlines()
        if line.startswith("data:")
    ]


# ---------------------------------------------------------------------------
# Health and routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_is_ok(http_settings: Settings) -> None:
    async with running_app(http_settings) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_endpoint_accepts_post(http_settings: Settings) -> None:
    """The Route-vs-bound-method trap: a bound method would make this a 405."""
    async with running_app(http_settings) as client:
        response = await initialize(client)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_trailing_slash_path_also_works(http_settings: Settings) -> None:
    async with running_app(http_settings) as client:
        response = await initialize(client, path="/mcp/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_custom_path_is_served(tmp_path: Path) -> None:
    settings = Settings(
        dataforge_base_url=BASE,
        dataforge_api_key=API_KEY,
        cache_dir=str(tmp_path / "cache"),
        host="127.0.0.1",
        mcp_http_path="/df/mcp",
    )
    async with running_app(settings) as client:
        assert (await initialize(client, path="/df/mcp")).status_code == 200
        other = await client.post("/mcp", json=INIT_BODY, headers=mcp_headers())
        assert other.status_code == 404


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialize_mints_a_session_id(http_settings: Settings) -> None:
    async with running_app(http_settings) as client:
        response = await initialize(client)

    assert response.status_code == 200
    session_id = response.headers.get("mcp-session-id")
    assert session_id
    # The spec restricts the id to visible ASCII.
    assert all("\x21" <= ch <= "\x7e" for ch in session_id)

    messages = sse_payloads(response.text)
    assert messages[0]["result"]["protocolVersion"]


@pytest.mark.asyncio
async def test_request_without_session_id_is_rejected(http_settings: Settings) -> None:
    async with running_app(http_settings) as client:
        await initialize(client)
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers=mcp_headers(),
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_unknown_session_id_is_404(http_settings: Settings) -> None:
    async with running_app(http_settings) as client:
        await initialize(client)
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers=mcp_headers(session_id="deadbeefdeadbeefdeadbeefdeadbeef"),
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_terminates_the_session(http_settings: Settings) -> None:
    async with running_app(http_settings) as client:
        init = await initialize(client)
        session_id = init.headers["mcp-session-id"]
        await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=mcp_headers(session_id=session_id),
        )

        deleted = await client.delete("/mcp", headers=mcp_headers(session_id=session_id))
        assert deleted.status_code == 200

        after = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
            headers=mcp_headers(session_id=session_id),
        )
    assert after.status_code == 404


@pytest.mark.asyncio
async def test_notification_returns_202(http_settings: Settings) -> None:
    async with running_app(http_settings) as client:
        init = await initialize(client)
        session_id = init.headers["mcp-session-id"]
        response = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=mcp_headers(session_id=session_id),
        )
    assert response.status_code == 202


# ---------------------------------------------------------------------------
# Content negotiation and verbs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accept_without_event_stream_is_rejected(http_settings: Settings) -> None:
    """The spec makes both media types mandatory on the Accept header."""
    async with running_app(http_settings) as client:
        response = await client.post(
            "/mcp",
            json=INIT_BODY,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
    assert response.status_code == 406


@pytest.mark.asyncio
async def test_get_without_session_is_rejected(http_settings: Settings) -> None:
    async with running_app(http_settings) as client:
        response = await client.get("/mcp", headers={"Accept": "text/event-stream"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_json_response_mode_returns_plain_json(tmp_path: Path) -> None:
    settings = Settings(
        dataforge_base_url=BASE,
        dataforge_api_key=API_KEY,
        cache_dir=str(tmp_path / "cache"),
        host="127.0.0.1",
        mcp_json_response=True,
    )
    async with running_app(settings) as client:
        response = await initialize(client)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["result"]["protocolVersion"]


@pytest.mark.asyncio
async def test_stateless_mode_mints_no_session(tmp_path: Path) -> None:
    settings = Settings(
        dataforge_base_url=BASE,
        dataforge_api_key=API_KEY,
        cache_dir=str(tmp_path / "cache"),
        host="127.0.0.1",
        mcp_stateless=True,
        mcp_json_response=True,
    )
    async with running_app(settings) as client:
        first = await initialize(client)
        second = await initialize(client)

    assert first.status_code == second.status_code == 200
    assert "mcp-session-id" not in first.headers


# ---------------------------------------------------------------------------
# Bearer authentication
# ---------------------------------------------------------------------------


@pytest.fixture
def authed_settings(tmp_path: Path) -> Settings:
    return Settings(
        dataforge_base_url=BASE,
        dataforge_api_key=API_KEY,
        cache_dir=str(tmp_path / "cache"),
        host="127.0.0.1",
        mcp_auth_token="s3cret-token",
    )


@pytest.mark.asyncio
async def test_no_token_configured_allows_everything(http_settings: Settings) -> None:
    assert http_settings.mcp_auth_token is None
    async with running_app(http_settings) as client:
        assert (await initialize(client)).status_code == 200


@pytest.mark.asyncio
async def test_missing_authorization_is_401(authed_settings: Settings) -> None:
    async with running_app(authed_settings) as client:
        response = await initialize(client)

    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")
    body = response.json()
    assert body["error"]["code"] == "MCP_UNAUTHORIZED"
    assert body["error"]["hint"]


@pytest.mark.asyncio
async def test_wrong_token_is_401(authed_settings: Settings) -> None:
    async with running_app(authed_settings) as client:
        response = await client.post(
            "/mcp",
            json=INIT_BODY,
            headers=mcp_headers(Authorization="Bearer wrong-token"),
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wrong_scheme_is_401(authed_settings: Settings) -> None:
    async with running_app(authed_settings) as client:
        response = await client.post(
            "/mcp",
            json=INIT_BODY,
            headers=mcp_headers(Authorization="Basic s3cret-token"),
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_correct_token_passes(authed_settings: Settings) -> None:
    async with running_app(authed_settings) as client:
        response = await client.post(
            "/mcp",
            json=INIT_BODY,
            headers=mcp_headers(Authorization="Bearer s3cret-token"),
        )
    assert response.status_code == 200
    assert response.headers.get("mcp-session-id")


@pytest.mark.asyncio
async def test_health_is_exempt_from_auth(authed_settings: Settings) -> None:
    async with running_app(authed_settings) as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_401_body_never_echoes_the_token(authed_settings: Settings) -> None:
    async with running_app(authed_settings) as client:
        response = await client.post(
            "/mcp", json=INIT_BODY, headers=mcp_headers(Authorization="Bearer wrong")
        )
    assert "s3cret-token" not in response.text
    assert "s3cret-token" not in str(dict(response.headers))


# ---------------------------------------------------------------------------
# Origin validation / DNS-rebinding protection
# ---------------------------------------------------------------------------


def test_loopback_bind_gets_protection_by_default() -> None:
    security = build_security_settings(Settings(host="127.0.0.1"))
    assert security.enable_dns_rebinding_protection
    assert "127.0.0.1:*" in security.allowed_hosts


def test_public_bind_without_allowlist_disables_protection() -> None:
    """Enabling it with an empty allow-list would reject every request."""
    security = build_security_settings(Settings(host="0.0.0.0"))
    assert not security.enable_dns_rebinding_protection


def test_explicit_allowlist_wins() -> None:
    security = build_security_settings(
        Settings(host="0.0.0.0", mcp_allowed_hosts="mcp.example:8080, host.docker.internal:8080")
    )
    assert security.enable_dns_rebinding_protection
    assert security.allowed_hosts == ["mcp.example:8080", "host.docker.internal:8080"]


@pytest.mark.asyncio
async def test_disallowed_origin_is_rejected(tmp_path: Path) -> None:
    settings = Settings(
        dataforge_base_url=BASE,
        dataforge_api_key=API_KEY,
        cache_dir=str(tmp_path / "cache"),
        host="127.0.0.1",
        mcp_allowed_origins="https://trusted.example",
        mcp_allowed_hosts="127.0.0.1:8080",
    )
    async with running_app(settings) as client:
        response = await client.post(
            "/mcp", json=INIT_BODY, headers=mcp_headers(Origin="https://evil.example")
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_allowed_origin_passes(tmp_path: Path) -> None:
    settings = Settings(
        dataforge_base_url=BASE,
        dataforge_api_key=API_KEY,
        cache_dir=str(tmp_path / "cache"),
        host="127.0.0.1",
        mcp_allowed_origins="https://trusted.example",
        mcp_allowed_hosts="127.0.0.1:8080",
    )
    async with running_app(settings) as client:
        response = await client.post(
            "/mcp", json=INIT_BODY, headers=mcp_headers(Origin="https://trusted.example")
        )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# End to end, over the real MCP client
# ---------------------------------------------------------------------------


@asynccontextmanager
async def mcp_client(settings: Settings, headers: dict[str, str] | None = None):
    """Drive the SDK's streamable-http client against the in-process app.

    `streamable_http_client` accepts a ready-made httpx client, so handing it one
    backed by an ASGI transport gives a true end-to-end protocol test - real
    initialize, real session id, real SSE framing - with no network.
    """
    server = create_mcp_server(settings)
    manager = create_session_manager(server, settings)
    app = build_app(manager, settings)

    async with manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            headers=headers,
            timeout=httpx.Timeout(30.0),
        ) as http_client:
            async with streamable_http_client(
                "http://127.0.0.1:8080/mcp", http_client=http_client
            ) as (read_stream, write_stream, _get_session_id):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session


@pytest.mark.asyncio
async def test_end_to_end_list_tools(http_settings: Settings) -> None:
    async with mcp_client(http_settings) as session:
        listing = await session.list_tools()

    names = {tool.name for tool in listing.tools}
    assert names == set(HANDLERS)
    assert "df_get_measures" in names
    assert "df_write_measure" in names


@respx.mock
@pytest.mark.asyncio
async def test_end_to_end_call_read_tool(http_settings: Settings) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=fx.PROJECTS_200)
    )
    async with mcp_client(http_settings) as session:
        result = await session.call_tool("df_list_projects", {"page": 1})

    payload = json.loads(result.content[0].text)
    assert "error" not in payload
    assert payload["projects"]


@respx.mock
@pytest.mark.asyncio
async def test_end_to_end_with_bearer_token(authed_settings: Settings) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=fx.PROJECTS_200)
    )
    async with mcp_client(authed_settings, headers={"Authorization": "Bearer s3cret-token"}) as s:
        result = await s.call_tool("df_list_projects", {"page": 1})

    payload = json.loads(result.content[0].text)
    assert payload["projects"]


@pytest.mark.asyncio
async def test_end_to_end_tool_annotations_survive_http(http_settings: Settings) -> None:
    """The annotations are a client's only pre-call warning; they must cross the wire."""
    async with mcp_client(http_settings) as session:
        listing = await session.list_tools()

    by_name = {tool.name: tool for tool in listing.tools}
    assert by_name["df_list_projects"].annotations.readOnlyHint is True
    assert by_name["df_delete_project"].annotations.destructiveHint is True
