# Configuration & Setup

## Installation

```bash
pip install -e ".[dev]"
```

## Environment Variables

Settings come from environment variables or a `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAFORGE_BASE_URL` | `https://api.prod-df.businessqlik.com` | DataForge API base URL |
| `DATAFORGE_API_KEY` | — (required) | API key sent as `X-Api-Key` |
| `DEFAULT_LANGUAGE` | `ru` | Default language for localized labels (`ru` / `en`) |
| `CACHE_BACKEND` | `file` | Cache backend (only `file` is implemented) |
| `CACHE_DIR` | `./cache` | Cache directory |
| `CACHE_TTL_SECONDS` | `3600` | Cache time-to-live |
| `MCP_SERVER_NAME` | `dataforge-semantic` | Name the server reports on initialize |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `sse` |
| `HOST` | `0.0.0.0` | Host for SSE mode |
| `PORT` | `8080` | Port for SSE mode |
| `LOG_LEVEL` | `INFO` | Logging level |

> ## ⚠️ `DATAFORGE_API_KEY` decides what an agent can destroy
>
> This server exposes 38 tools that **create, overwrite and permanently delete** DataForge
> data, and it has **no read-only switch**. The key's effective project role is the only
> limit:
>
> | Effective project role | What the agent can do |
> |---|---|
> | `viewer`, `analyst` | Read everything it has access to. Write tools answer `403 DF_API.WRITE_ACCESS_DENIED` — **the server is effectively read-only** |
> | `developer` and above | Create, update and **delete** RMD content, data model entities, versions and projects |
> | project owner / company admin | Additionally change project access and ownership |
> | company admin | Additionally manage the Git connection registry |
>
> **Issue a `viewer` or `analyst` key for read-only work.** Point agents at a
> non-production project version first. Every write lands in the DataForge audit log with
> before/after snapshots.

Credentials never leave the process: the API key is held as a `SecretStr`, and request
bodies for export/import and Git connection endpoints (which carry personal access tokens,
SSH keys and passwords) are never logged.

## Rate limits

The API allows **100 requests per 60 seconds per API key**, counted in shared storage
across all backend instances. Exceeding it yields `DATAFORGE_RATE_LIMIT_EXCEEDED` with
`retry_after_seconds`, and the request is **not** retried automatically.

`df_get_measures`, `df_get_dimensions` and `df_get_facts` page through their listings, so
a very large version costs several requests — the cache makes this a one-time price per
TTL window.

## Claude Desktop Config

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dataforge": {
      "command": "python",
      "args": ["-m", "dataforge_mcp"],
      "env": {
        "DATAFORGE_BASE_URL": "https://api.prod-df.businessqlik.com",
        "DATAFORGE_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

Write tools are annotated with `readOnlyHint=false` and, where they remove or overwrite
data, `destructiveHint=true`. A well-behaved MCP client uses those hints to ask for
confirmation — but that confirmation belongs to the client, not to this server.

## Docker (SSE mode)

```bash
cp .env.example .env
# edit .env with your API key
docker compose up
```

## Architecture

```
AI Agent / MCP Client
    │
    ▼
MCP Adapter (mcp/)             ── tool definitions + flat handler registry, no business logic
    │   tools_read.py  · 24 read-only tools
    │   tools_write.py · 41 state-changing tools (38 write to DataForge)
    ▼
SemanticService (application/) ── cache-first reads, scope-invalidating writes
    │   use_cases.py       · reads
    │   write_use_cases.py · writes
    │   invalidation.py    · which cache prefixes a write drops
    │
    ├──▶ DataForgeClient (dataforge/) ── HTTPS to DF API v2
    │       read_client.py   · 22 read methods
    │       write_client.py  · 55 write methods
    │       write_schemas.py · strict request bodies
    ├──▶ Normalizer (semantic/)       ── raw API → canonical models
    └──▶ FileCacheStore (cache/)      ── TTL, last-known-good, prefix invalidation
```

**Key design rules:**

- `SemanticService` is the single entry point for business logic; MCP tools only delegate.
- Reads are cache-first and fall back to the last successful response when the API fails.
- Writes never read the cache and never serve last-known-good — returning stale data as the
  outcome of a write would be a lie. Instead each write drops the whole cache scope it
  touched, so a read immediately afterwards always hits the API.
- Every write carries an `Idempotency-Key`, which is what makes retrying a `POST` after a
  5xx safe. A `POST` without one is never retried.

## Development

```bash
pytest                            # run all tests (415)
pytest tests/test_mcp_server.py -v  # end-to-end over the MCP protocol, no network
ruff check src/ tests/            # lint
ruff format src/ tests/           # format
```

| Test file | Covers |
|---|---|
| `tests/fixtures/api_v2.py` | Response fixtures transcribed verbatim from the API documentation |
| `test_client_read.py` | Query-parameter contract and response parsing for every read endpoint |
| `test_write_client.py` | Paths, verbs and bodies for every write endpoint |
| `test_transport.py` | Retries, idempotency, 204/207 handling |
| `test_errors.py` | The v2 error envelope, field details, status degradation |
| `test_service.py` | Normalization, caching, agent-level read flows |
| `test_write_use_cases.py` | Cache invalidation and local body validation |
| `test_mcp_contract.py` | Tool↔handler bijection, JSON Schema validity, safety annotations |
| `test_mcp_server.py` | Full MCP protocol through an in-memory client |

When the DataForge API changes, `tests/fixtures/api_v2.py` is what gets updated first.
