# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DataForge Semantic MCP Server — a standalone MCP server that connects to **DataForge Product API**, fetches the semantic layer (projects, versions, measures, dimensions, facts, full RMD) and data model entities (data marts, connections, dimension groups, fact tables, relationships), normalizes and caches it, and exposes it to AI agents via MCP protocol.

This is a **read-only semantic gateway**. Out of scope: SQL execution, text-to-SQL, database connections, schema introspection, BI rendering.

## Build & Run Commands

```bash
# Install dependencies (dev)
pip install -e ".[dev]"

# Run MCP server (stdio mode)
python -m dataforge_mcp

# Run all tests
pytest

# Run a single test file
pytest tests/test_client.py

# Run a single test
pytest tests/test_client.py::test_get_projects_success -v

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

## Architecture

The codebase follows a layered architecture under `src/dataforge_mcp/`:

```
Transport Layer (mcp/)         -> MCP protocol (stdio + SSE), tool registration
        |
Application Layer (application/) -> Use-case orchestration (calls client + cache + normalizer)
        |
DataForge Client (dataforge/)  -> HTTPS calls to RMD API + DF API with X-Api-Key auth
Normalization (semantic/)      -> Raw API response -> canonical Pydantic models
Cache (cache/)                 -> File-based cache with TTL, force-refresh, last-known-good fallback
```

**Key rule**: MCP transport logic must never mix with DataForge client logic. `mcp/tools.py` should contain no business logic — it delegates to application use cases.

### Canonical Models

All layers communicate via canonical Pydantic models defined in `semantic/models.py`: `CanonicalProject`, `CanonicalVersion`, `CanonicalMeasure`, `CanonicalDimension`, `CanonicalFact`, `CanonicalSemanticContext`.

### DataForge API Endpoints

All requests require `X-Api-Key` header. Base URL from config.

**RMD API (`/rmd-api/v1/`)**:
- `GET /rmd-api/v1/projects`
- `GET /rmd-api/v1/projects/{projectId}/versions`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/measures`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/dimensions`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/facts`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/rmd`

**DF API (`/df-api/v1/`)** — data model entities:
- `GET .../data-marts`, `GET .../data-marts/{id}`, `GET .../data-marts/{id}/view`, `POST .../data-marts/{id}/generate-sql`
- `GET .../connections`, `GET .../connections/{id}`, `GET .../connections/{id}/schema`
- `GET .../dimension-groups`, `GET .../dimension-groups/{id}`
- `GET .../fact-tables`, `GET .../fact-tables/{id}`
- `GET .../relationships`, `GET .../relationships/{id}`
- `GET .../rmd` (consolidated RMD export)

### MCP Tools

**RMD API tools**: `df_health`, `df_list_projects`, `df_list_versions`, `df_get_measures`, `df_get_dimensions`, `df_get_facts`, `df_get_rmd`, `df_refresh_cache`

**DF API tools**: `df_list_data_marts`, `df_get_data_mart`, `df_get_data_mart_view`, `df_generate_sql`, `df_list_connections`, `df_get_connection`, `df_get_connection_schema`, `df_list_dimension_groups`, `df_get_dimension_group`, `df_list_fact_tables`, `df_get_fact_table`, `df_list_relationships`, `df_get_relationship`, `df_get_consolidated_rmd`

## Tech Stack & Conventions

- Python 3.11+, type hints everywhere
- `pydantic` v2 for models, `pydantic-settings` for config (with `SecretStr` for API keys)
- `httpx` for HTTP, `structlog` for logging, `mcp` SDK for MCP protocol
- `pytest` + `pytest-asyncio` for tests, `respx` for HTTP mocking, `ruff` for linting
- Comments and code in English

## Config

Settings via env vars or `.env` file. Key variables: `DATAFORGE_BASE_URL`, `DATAFORGE_API_KEY` (secret), `DEFAULT_LANGUAGE` (default: `ru`), `CACHE_TTL_SECONDS`, `MCP_TRANSPORT` (`stdio`/`sse`), `LOG_LEVEL`.

## Error Handling

- Map DataForge API errors to normalized error codes (e.g., `DATAFORGE_API_KEY_INVALID`, `DATAFORGE_ACCOUNT_LOCKED`, `DATAFORGE_INVALID_PARAMETER`)
- Retry only on 5xx and network errors (exponential backoff, max 2-3 retries)
- No retry on 400/401/403/404
- Connect timeout: 5s, read timeout: 30s
- Never leak API keys in logs, error responses, or tool outputs

## Testing

Use `respx` to mock DataForge HTTP calls. Four test areas: client, normalizer, cache, MCP tools. Integration tests covering: projects -> versions -> rmd, and data marts -> detail -> SQL generation.
