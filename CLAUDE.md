# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DataForge Semantic MCP Server — a standalone MCP server that connects to **DataForge Product API**, fetches the semantic layer (projects, versions, measures, dimensions, full RMD), normalizes and caches it, and exposes it to AI agents via MCP protocol.

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
Transport Layer (mcp/)         → MCP protocol (stdio + SSE), tool registration
        ↓
Application Layer (application/) → Use-case orchestration (calls client + cache + normalizer)
        ↓
DataForge Client (dataforge/)  → HTTPS calls to Product API with X-Api-Key auth
Normalization (semantic/)      → Raw API response → canonical Pydantic models
Cache (cache/)                 → File-based cache with TTL, force-refresh, last-known-good fallback
```

**Key rule**: MCP transport logic must never mix with DataForge client logic. `mcp/tools.py` should contain no business logic — it delegates to application use cases.

### Canonical Models

All layers communicate via canonical Pydantic models defined in `semantic/models.py`: `CanonicalProject`, `CanonicalVersion`, `CanonicalMeasure`, `CanonicalDimension`, `CanonicalSemanticContext`.

### DataForge Product API Endpoints

All requests require `X-Api-Key` header. Base URL from config.

- `GET /rmd-api/v1/projects`
- `GET /rmd-api/v1/projects/{projectId}/versions`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/measures`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/dimensions`
- `GET /rmd-api/v1/projects/{projectId}/versions/{versionId}/rmd`

### MCP Tools (MVP)

`df_health`, `df_list_projects`, `df_list_versions`, `df_get_measures`, `df_get_dimensions`, `df_get_rmd`, `df_refresh_cache`

Post-MVP: `df_get_semantic_summary`, `df_search_semantic_entities`

## Tech Stack & Conventions

- Python 3.11+, type hints everywhere
- `pydantic` v2 for models, `pydantic-settings` for config (with `SecretStr` for API keys)
- `httpx` for HTTP, `structlog` for logging, `mcp` SDK for MCP protocol
- `pytest` + `pytest-asyncio` for tests, `respx` for HTTP mocking, `ruff` for linting
- Comments and code in English

## Config

Settings via env vars or `.env` file. Key variables: `DATAFORGE_BASE_URL`, `DATAFORGE_API_KEY` (secret), `DEFAULT_LANGUAGE` (default: `ru`), `CACHE_TTL_SECONDS`, `MCP_TRANSPORT` (`stdio`/`sse`), `LOG_LEVEL`.

## Error Handling

- Map DataForge API errors to normalized error codes (e.g., `DATAFORGE_API_KEY_INVALID`)
- Retry only on 5xx and network errors (exponential backoff, max 2-3 retries)
- No retry on 401/403/404
- Connect timeout: 5s, read timeout: 30s
- Never leak API keys in logs, error responses, or tool outputs

## Testing

Use `respx` to mock DataForge HTTP calls. Four test areas: client, normalizer, cache, MCP tools. At least one integration test covering the full flow: projects → versions → rmd.

## Design Documents

Detailed specs are in the numbered markdown files (`01_PRODUCT_SCOPE.md` through `10_BUILD_PROMPTS.md`) at the repo root. Refer to these for full API contracts, canonical model field definitions, and implementation plans.
