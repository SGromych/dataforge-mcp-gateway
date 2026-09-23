"""Transport selection: config validation, dispatch, and the CLI surface.

`run_transport` is the one place a transport name turns into a running server,
so these tests pin that mapping and the validation in front of it. Before the
validator existed, a typo in MCP_TRANSPORT silently started stdio instead.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dataforge_mcp import transport
from dataforge_mcp.cli import parse_args
from dataforge_mcp.config import TRANSPORTS, Settings

# ---------------------------------------------------------------------------
# Validation and normalization
# ---------------------------------------------------------------------------


def test_default_transport_is_stdio() -> None:
    assert Settings().mcp_transport == "stdio"


@pytest.mark.parametrize("value", TRANSPORTS)
def test_every_declared_transport_is_accepted(value: str) -> None:
    assert Settings(mcp_transport=value).mcp_transport == value


@pytest.mark.parametrize(
    "value",
    ["streamable_http", "streamablehttp", "streamable", "http", "HTTP", " Streamable-HTTP "],
)
def test_streamable_http_aliases_normalize(value: str) -> None:
    assert Settings(mcp_transport=value).mcp_transport == "streamable-http"


@pytest.mark.parametrize("value", ["sse2", "websocket", "", "std io", "stdio,sse"])
def test_unknown_transport_is_rejected(value: str) -> None:
    """No silent fallback: a typo must fail at startup, not at connect time."""
    with pytest.raises(ValidationError):
        Settings(mcp_transport=value)


def test_surrounding_whitespace_is_tolerated() -> None:
    assert Settings(mcp_transport="  stdio  ").mcp_transport == "stdio"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("mcp", "/mcp"), ("/mcp/", "/mcp"), ("/df/mcp", "/df/mcp"), ("/", "/")],
)
def test_http_path_is_normalized(raw: str, expected: str) -> None:
    assert Settings(mcp_http_path=raw).mcp_http_path == expected


def test_csv_settings_split_and_strip() -> None:
    settings = Settings(
        mcp_allowed_hosts=" a.example:8080 , b.example ",
        mcp_allowed_origins="https://one.example,,https://two.example",
        mcp_cors_origins="",
    )
    assert settings.allowed_hosts_list == ["a.example:8080", "b.example"]
    assert settings.allowed_origins_list == ["https://one.example", "https://two.example"]
    assert settings.cors_origins_list == []


@pytest.mark.parametrize(
    ("host", "loopback"),
    [("127.0.0.1", True), ("localhost", True), ("::1", True), ("0.0.0.0", False)],
)
def test_loopback_detection(host: str, loopback: bool) -> None:
    assert Settings(host=host).binds_loopback_only is loopback


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_auth_token_means_no_auth(blank: str) -> None:
    """`MCP_AUTH_TOKEN=` used to install the middleware with an empty secret.

    Every well-formed request was then rejected while the log still said
    `auth=bearer` - the worst of both answers.
    """
    assert Settings(mcp_auth_token=blank).mcp_auth_token is None


def test_a_real_auth_token_survives() -> None:
    settings = Settings(mcp_auth_token="s3cret-token")
    assert settings.mcp_auth_token is not None
    assert settings.mcp_auth_token.get_secret_value() == "s3cret-token"


def test_assignment_goes_through_the_validators() -> None:
    """The CLI writes onto Settings, so assignment must validate like env does."""
    settings = Settings()
    settings.mcp_transport = "http"
    settings.mcp_http_path = "custom/"
    assert settings.mcp_transport == "streamable-http"
    assert settings.mcp_http_path == "/custom"
    with pytest.raises(ValidationError):
        settings.mcp_transport = "nope"


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Replace every runner so dispatch can be observed without serving."""
    called: dict[str, object] = {}

    async def fake_stdio(server: object) -> None:
        called["transport"] = "stdio"
        called["server"] = server

    async def fake_sse(server: object, settings: Settings) -> None:
        called["transport"] = "sse"
        called["server"] = server

    async def fake_streamable(server: object, settings: Settings) -> None:
        called["transport"] = "streamable-http"
        called["server"] = server

    monkeypatch.setattr("dataforge_mcp.transport.stdio.run_stdio", fake_stdio)
    monkeypatch.setattr("dataforge_mcp.transport.sse.run_sse", fake_sse)
    monkeypatch.setattr(
        "dataforge_mcp.transport.streamable_http.run_streamable_http", fake_streamable
    )
    return called


@pytest.mark.parametrize("name", TRANSPORTS)
@pytest.mark.asyncio
async def test_dispatch_picks_the_named_runner(
    name: str, spy: dict[str, object], settings: Settings
) -> None:
    sentinel = object()
    settings.mcp_transport = name
    await transport.run_transport(sentinel, settings)  # type: ignore[arg-type]
    assert spy["transport"] == name
    assert spy["server"] is sentinel


@pytest.mark.asyncio
async def test_sse_dispatch_warns_that_it_is_deprecated(
    spy: dict[str, object], settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    warnings: list[tuple[str, dict[str, object]]] = []

    def capture(event: str, **kwargs: object) -> None:
        warnings.append((event, kwargs))

    monkeypatch.setattr(transport.logger, "warning", capture)
    settings.mcp_transport = "sse"
    await transport.run_transport(object(), settings)  # type: ignore[arg-type]

    assert any(event == "transport_deprecated" for event, _ in warnings)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_accepts_streamable_http_and_its_flags() -> None:
    args = parse_args(
        ["--transport", "streamable-http", "--path", "/df/mcp", "--stateless", "--json-response"]
    )
    assert args.transport == "streamable-http"
    assert args.path == "/df/mcp"
    assert args.stateless is True
    assert args.json_response is True


def test_cli_defaults_leave_settings_untouched() -> None:
    args = parse_args([])
    assert args.transport is None
    assert args.path is None
    assert args.stateless is False
    assert args.json_response is False


def test_cli_rejects_an_unknown_transport() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--transport", "carrier-pigeon"])


def test_cli_offers_exactly_the_declared_transports() -> None:
    """Keeps argparse choices from drifting away from TRANSPORTS."""
    for name in TRANSPORTS:
        assert parse_args(["--transport", name]).transport == name
