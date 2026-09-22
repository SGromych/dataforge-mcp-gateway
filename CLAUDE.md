# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DataForge Semantic MCP Server — a standalone MCP server that connects to the **DataForge Public API v2**, exposing the semantic layer (projects, versions, measures, dimensions, facts, full RMD) and the data model (data marts, connections, dimension groups, fact tables, relationships) to AI agents, **and letting them modify it**.

Out of scope: SQL execution, text-to-SQL, direct database connections, schema introspection, BI rendering.

> ## ⚠️ THIS SERVER WRITES TO DATAFORGE
>
> 38 of its 65 tools create, replace, update or **permanently delete** data — including
> whole projects and versions. There is no read-only switch: the only limit is the
> effective project role of the API key in `DATAFORGE_API_KEY` (`analyst`/`viewer` makes
> it effectively read-only; `developer` and above can delete). Keep the warning blocks in
> `README.md`, `docs/api/*.md` and `.env.example` accurate whenever the write surface
> changes.

## Build & Run Commands

```bash
# Install dependencies (dev)
pip install -e ".[dev]"

# Run MCP server (stdio mode)
python -m dataforge_mcp

# Run all tests
pytest

# Run a single test file
pytest tests/test_client_read.py

# Run a single test
pytest tests/test_service.py::test_measures_are_normalized -v

# Lint / format
ruff check src/ tests/
ruff format src/ tests/
```

## Architecture

```
Transport Layer (mcp/)           -> MCP protocol (stdio + SSE), tool definitions, handler registry
        |
Application Layer (application/) -> Use-case orchestration (client + cache + normalizer)
        |
DataForge Client (dataforge/)    -> HTTPS calls to DF API v2 with X-Api-Key auth
Normalization (semantic/)        -> Raw API response -> canonical Pydantic models
Cache (cache/)                   -> File-based cache with TTL, last-known-good, prefix invalidation
```

Module map:

| Module | Role |
|---|---|
| `mcp/tools_read.py` / `tools_write.py` | Tool definitions + `Handler` registries |
| `mcp/schema_fragments.py` | Reusable inputSchema pieces and filter value catalogues |
| `mcp/tools.py` | Composition, `register_tools`, `_dispatch` |
| `application/use_cases.py` | `SemanticService` — reads |
| `application/write_use_cases.py` | `WriteUseCasesMixin` — writes |
| `application/invalidation.py` | `WriteScope` and the cache prefixes each scope drops |
| `dataforge/read_client.py` / `write_client.py` | `ReadMixin` / `WriteMixin` of `DataForgeClient` |
| `dataforge/client.py` | Transport: retries, idempotency, `_write`, path helpers |
| `dataforge/schemas.py` | Raw response models |
| `dataforge/write_schemas.py` | Strict request bodies |

**Key rule**: MCP transport logic must never mix with DataForge client logic. `mcp/tools*.py` contains no business logic — it delegates to `SemanticService`.

### Canonical Models

Layers communicate via canonical Pydantic models in `semantic/models.py`: `CanonicalProject`, `CanonicalVersion`, `CanonicalMeasure`, `CanonicalDimension`, `CanonicalFact`, `CanonicalSemanticContext`. Raw data-model entities (data marts, fact tables, …) pass through untouched.

## Invariants

These are easy to break and are enforced by tests:

- **Query parameters are snake_case.** `pageSize` is the only camelCase parameter in the entire v2 surface. Sending `mergeType` instead of `merge_type` silently drops the filter.
- **No camelCase aliases on v2 response models.** An alias without `populate_by_name` makes the field parse as empty — this is how `df_list_data_marts` once returned an empty list forever.
- **Every response model allows unknown fields** (`extra="allow"`), so an additive API change never breaks a running server.
- **Request bodies are strict** (`extra="forbid"`), mirroring the server's `unknown_field` rule so typos fail locally with the same error shape.
- **Reference columns are strings, not booleans.** `required`, `relevance`, `visibility` come back as localized labels and are written as `"true"` / `"false"`.
- **Test fixtures are transcribed from the API documentation**, never invented. `tests/fixtures/api_v2.py` is what gets updated first when the API changes.

## DataForge API v2 (`/df-api/v2/`)

All requests send `X-Api-Key`. `{v}` = `/df-api/v2/projects/{project_id}/versions/{version_id}`.

**Reads**: `GET /projects`, `GET /projects/{id}/versions`, `{v}/measures` (`include_sql`), `{v}/dimensions`, `{v}/facts`, `{v}/rmd` (`include_sql`), `{v}/data-marts[/{id}[/view]]`, `POST {v}/data-marts/{id}/generate-sql` (limit/offset in the **query**, answers **200**), `{v}/connections[/{id}[/schema]]` (`include_db_schema`), `{v}/dimension-groups[/{id}]`, `{v}/fact-tables[/{id}]` (`include_dependencies`), `{v}/relationships[/{id}]` (`fact_table_id`, `dimension_group_id`), `GET /projects/{projectId}/access`, `GET /git-connections[/{id}]`.

`{v}/rmd` serves both `df_get_rmd` (normalized projection) and `df_get_consolidated_rmd` (raw export) — one request, one cache entry.

**Writes** (sections 9.9.6–9.9.11 of the product API doc): full CRUD for projects, versions, measures/dimensions/facts (plus `/bulk`), dimension groups and their membership, fact tables and their composition, verification filters at both levels, relationships; project access management; version export/import (Git and file); Git connection registry.

**Write conventions**: POST → 201, POST `/bulk` and assignment → 201/207/422, PUT = full replace (unset optional fields are reset), PATCH = partial, DELETE → 204. `Idempotency-Key` (UUID v4) on POST only, ignored by `generate-sql`, `export/file`, `import/validate`, `import/preview`, git `test`.

**Rate limiting**: 100 req / 60 s per API key → HTTP 429 `DATAFORGE_RATE_LIMIT_EXCEEDED`, no retry.

## MCP Tools

65 tools: 24 read-only, 41 that change state (38 of which write to DataForge; the rest are
cache refresh and two import dry runs). Every tool carries `ToolAnnotations` — `readOnlyHint` for reads, `destructiveHint` for anything that deletes or overwrites. These annotations are the only pre-call warning a client can show, so they must stay accurate.

`df_write_*` tools take `mode: create|replace|update` — one tool per entity instead of three near-identical ones. Fact-table composition collapses 8 endpoints into `df_assign_to_fact_table` / `df_unassign_from_fact_table` with `element_type`; verification filters collapse 8 into two tools that pick the path by the presence of `fact_table_id`.

See `docs/api/tools-semantic.md`, `tools-data-model.md` and `tools-write.md`.

## Tech Stack & Conventions

- Python 3.11+, type hints everywhere
- `pydantic` v2 for models, `pydantic-settings` for config (`SecretStr` for API keys)
- `httpx` for HTTP, `structlog` for logging, `mcp` SDK for the protocol
- `pytest` + `pytest-asyncio`, `respx` for HTTP mocking, `jsonschema` for schema checks, `ruff` for linting
- Line length 99; comments and code in English

## Config

Settings via env vars or `.env`. Key variables: `DATAFORGE_BASE_URL`, `DATAFORGE_API_KEY` (secret), `DEFAULT_LANGUAGE` (default `ru`), `CACHE_TTL_SECONDS`, `MCP_TRANSPORT` (`stdio`/`sse`), `LOG_LEVEL`.

## Error Handling

- Parse the v2 envelope (`message`, `originalMessage`, `statusCode`, `error`, `code`, `details[]`) and surface `api_code`, `fields[]` and a `hint` — that is what lets an agent repair a rejected request.
- Unknown keys degrade by HTTP status, exactly as the API does.
- Retry only on 5xx, timeouts and network errors (exponential backoff, max 3). Never on 4xx, never on 429, and **never on a POST without an `Idempotency-Key`** — such a timeout is reported with `possibly_applied: true`.
- Connect timeout 5 s, read timeout 30 s; version transfer uses 180 s.
- Never leak API keys or Git credentials in logs, error responses or tool output.

## Caching

- Read: cache-first with TTL, last-known-good fallback when the API fails.
- Write: never reads the cache, never serves last-known-good, and invalidates its whole scope (`WriteScope.VERSION` / `PROJECT` / `GLOBAL` / `GIT`) by key prefix. The exact set of affected keys is not derivable from a write's arguments, so the scope is dropped wholesale.

## Testing

Mock DataForge with `respx`; fixtures come from `tests/fixtures/api_v2.py`. Coverage spans the client (read and write), transport, errors, normalizer, cache, service and the MCP layer — including an in-memory end-to-end test over the real MCP protocol (`tests/test_mcp_server.py`) and a contract test asserting the tool↔handler bijection and JSON Schema validity (`tests/test_mcp_contract.py`).
