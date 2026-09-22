"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Final

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Every transport the server can serve. `stdio` is the process default; `sse` is the
#: deprecated HTTP+SSE transport from protocol revision 2024-11-05.
TRANSPORTS: Final[tuple[str, ...]] = ("stdio", "sse", "streamable-http")

#: Spellings people reasonably type for the streamable-http transport.
_TRANSPORT_ALIASES: Final[dict[str, str]] = {
    "streamable_http": "streamable-http",
    "streamablehttp": "streamable-http",
    "streamable": "streamable-http",
    "http": "streamable-http",
}

#: Loopback binds get DNS-rebinding protection for free, the way FastMCP does it.
LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})
#: Both forms matter: the SDK matches a bare host exactly, and "host:*" only when a
#: port is present, so "localhost" on port 80 needs its own entry.
LOOPBACK_ALLOWED: Final[list[str]] = [
    "127.0.0.1",
    "127.0.0.1:*",
    "localhost",
    "localhost:*",
    "[::1]",
    "[::1]:*",
]


def _split_csv(raw: str) -> list[str]:
    """Parse a comma-separated env var into a clean list.

    List-valued settings are plain strings rather than ``list[str]`` on purpose:
    pydantic-settings only accepts JSON for complex types, which would make
    ``.env`` lines like ``MCP_ALLOWED_ORIGINS=https://a,https://b`` illegal.
    """
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings(BaseSettings):
    # validate_assignment keeps the CLI honest: `--path mcp/` and `--transport http`
    # go through the same validators as the env vars do.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", validate_assignment=True)

    dataforge_base_url: str = "https://api.prod-df.businessqlik.com"
    dataforge_api_key: SecretStr = SecretStr("replace_me")
    default_language: str = "ru"
    cache_backend: str = "file"
    cache_dir: str = "./cache"
    cache_ttl_seconds: int = 3600
    mcp_server_name: str = "dataforge-semantic"
    mcp_transport: str = "stdio"
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"

    # --- streamable-http transport -----------------------------------------
    mcp_http_path: str = "/mcp"
    mcp_json_response: bool = False
    mcp_stateless: bool = False
    mcp_auth_token: SecretStr | None = None
    mcp_allowed_hosts: str = ""
    mcp_allowed_origins: str = ""
    mcp_cors_origins: str = ""

    @field_validator("mcp_transport", mode="before")
    @classmethod
    def _normalize_transport(cls, value: object) -> str:
        """Accept common spellings, and reject unknown ones loudly.

        Before this validator any unrecognised value silently fell through to
        stdio, so a typo in ``MCP_TRANSPORT`` produced a server that started
        fine and never listened on the port the operator expected.
        """
        if not isinstance(value, str):
            raise ValueError(f"MCP_TRANSPORT must be a string, got {type(value).__name__}")
        normalized = _TRANSPORT_ALIASES.get(value.strip().lower(), value.strip().lower())
        if normalized not in TRANSPORTS:
            raise ValueError(
                f"unknown MCP_TRANSPORT {value!r}; expected one of {', '.join(TRANSPORTS)}"
            )
        return normalized

    @field_validator("mcp_http_path")
    @classmethod
    def _normalize_http_path(cls, value: str) -> str:
        path = value.strip()
        if not path.startswith("/"):
            path = f"/{path}"
        return path.rstrip("/") or "/"

    @property
    def allowed_hosts_list(self) -> list[str]:
        return _split_csv(self.mcp_allowed_hosts)

    @property
    def allowed_origins_list(self) -> list[str]:
        return _split_csv(self.mcp_allowed_origins)

    @property
    def cors_origins_list(self) -> list[str]:
        return _split_csv(self.mcp_cors_origins)

    @property
    def binds_loopback_only(self) -> bool:
        return self.host.strip().lower() in LOOPBACK_HOSTS


@lru_cache
def get_settings() -> Settings:
    return Settings()
