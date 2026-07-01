# Configuration & Setup

## Installation

```bash
pip install -e ".[dev]"
```

## Environment Variables

Settings via environment variables or `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAFORGE_BASE_URL` | `https://api.prod-df.businessqlik.com` | DataForge API base URL |
| `DATAFORGE_API_KEY` | — (required) | API key for authentication |
| `DEFAULT_LANGUAGE` | `ru` | Default language for localized names |
| `CACHE_DIR` | `./cache` | Cache directory path |
| `CACHE_TTL_SECONDS` | `3600` | Cache time-to-live in seconds |
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `sse` |
| `HOST` | `0.0.0.0` | Host for SSE mode |
| `PORT` | `8080` | Port for SSE mode |
| `LOG_LEVEL` | `INFO` | Logging level |

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
MCP Adapter (mcp/)            ── thin wrappers, no business logic
    │
    ▼
SemanticService (application/) ── cache-first orchestration
    │
    ├──▶ DataForgeClient (dataforge/) ── HTTPS calls to DF API v2 with retry
    ├──▶ Normalizer (semantic/)       ── raw API → canonical models
    └──▶ FileCacheStore (cache/)      ── TTL + last-known-good fallback
```

**Key design rules:**
- `SemanticService` is the single entry point for all business logic
- MCP tools (`mcp/tools.py`) contain no business logic — they only delegate to `SemanticService`
- The cache implements "last-known-good" fallback: if an API call fails, the last successful response is returned

## Development

```bash
pytest                     # run all tests
pytest tests/test_client.py -v  # run specific test file
ruff check src/ tests/     # lint
ruff format src/ tests/    # format
```
