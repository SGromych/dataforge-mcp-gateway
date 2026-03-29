# DataForge Semantic MCP Server

Read-only semantic gateway between AI agents and [DataForge](https://businessqlik.com) Product API. Fetches projects, versions, measures, dimensions and full RMD, normalizes and caches the data, and exposes it via MCP protocol or as a Python library.

## Features

- **Library-first** — use directly from Python, no MCP server required
- **MCP adapter** — 7 tools for Claude Desktop, Cursor and other MCP clients
- **Caching** — file-based cache with TTL and last-known-good fallback
- **Normalization** — inconsistent API fields mapped to clean canonical models
- **Retry & error handling** — exponential backoff on 5xx, proper error codes for auth issues

## Quick Start

### Installation

```bash
pip install -e ".[dev]"
```

### Configuration

Copy `.env.example` to `.env` and set your values:

```env
DATAFORGE_BASE_URL=https://api.prod-df.businessqlik.com
DATAFORGE_API_KEY=your_api_key_here
DEFAULT_LANGUAGE=ru
```

### As a Python Library

```python
import asyncio
from dataforge_mcp import create_semantic_service

async def main():
    service = create_semantic_service()

    projects = await service.list_projects()
    print(projects)

    versions = await service.list_versions(project_id=392)
    print(versions)

    rmd = await service.get_rmd(project_id=392, version_id=948)
    print(f"Measures: {rmd['stats']['measure_count']}")
    print(f"Dimensions: {rmd['stats']['dimension_count']}")

asyncio.run(main())
```

### As an MCP Server (stdio)

```bash
python -m dataforge_mcp
```

Add to Claude Desktop config (`claude_desktop_config.json`):

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

### Docker (SSE mode)

```bash
cp .env.example .env
# edit .env with your API key
docker compose up
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `df_health` | Check server, API and cache status |
| `df_list_projects` | List available DataForge projects |
| `df_list_versions` | List versions for a project |
| `df_get_measures` | Get measures (metrics) for a project version |
| `df_get_dimensions` | Get dimensions for a project version |
| `df_get_rmd` | Get full RMD (measures + dimensions) |
| `df_refresh_cache` | Force refresh cached data |

## Architecture

```
AI Agent / MCP Client
    |
    v
MCP Adapter (mcp/)           — thin wrappers, no business logic
    |
    v
SemanticService (application/) — cache-first orchestration (CORE)
    |
    +--> DataForgeClient (dataforge/) — HTTP calls with retry
    +--> Normalizer (semantic/)       — raw API -> canonical models
    +--> FileCacheStore (cache/)      — TTL + last-known-good fallback
```

`SemanticService` is the single entry point. MCP tools only delegate to it.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAFORGE_BASE_URL` | `https://api.prod-df.businessqlik.com` | DataForge API base URL |
| `DATAFORGE_API_KEY` | — | API key (required) |
| `DEFAULT_LANGUAGE` | `ru` | Default language for measures/dimensions |
| `CACHE_DIR` | `./cache` | Cache directory path |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL in seconds |
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` or `sse` |
| `LOG_LEVEL` | `INFO` | Log level |

## Design Documents

Detailed specs are in the [`docs/`](docs/) directory.
