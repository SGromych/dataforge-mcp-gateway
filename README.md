# DataForge Semantic MCP Server

> Give your AI agent full access to the DataForge semantic layer — measures, dimensions, facts, data marts, SQL generation **and the ability to change all of it** — through a single MCP interface.

---

> # ⚠️ **THIS SERVER IS NO LONGER READ-ONLY**
>
> ### **It can create, overwrite and permanently delete your DataForge data.**
>
> 41 of its 65 tools are not read-only, and **38 of them create, replace, update and delete**
> projects, versions, measures, dimensions, facts, dimension groups, fact tables, relationships,
> verification filters, project access grants and Git connections.
>
> - `df_delete_project` removes a project **together with all of its versions and their entire content**.
> - `df_import_version_from_git` with `target.method=replace` **overwrites an entire version**.
> - `df_write_measure` with `mode=replace` **resets every optional field you do not pass**.
>
> ### **There is no kill switch in this server.**
>
> The only thing standing between an LLM agent and your production semantic model is the
> **effective project role of the API key** you put in `DATAFORGE_API_KEY`.
>
> ### **Want read-only behaviour? Use a read-only key.**
>
> Issue an API key whose effective project role is **`analyst` or `viewer`**. Every write
> endpoint requires `developer` or above and answers `403 DF_API.WRITE_ACCESS_DENIED` for
> lower roles — the API enforces this, this server does not.
>
> Point agents at a **non-production project version** first. Every write is recorded in
> the DataForge audit log with before/after snapshots.

---

**DataForge Semantic MCP Server** connects AI agents (Claude, Cursor, custom MCP clients) to the [DataForge](https://businessqlik.com) Public API v2. It fetches, normalizes and caches semantic metadata, and lets agents modify it.

## Why?

DataForge stores the **business definitions** behind your analytics: what "Total Revenue" means, which database columns feed it, how customer dimensions are grouped. Without this context, AI agents are working blind.

This server gives them that context — structured, cached and ready to use — plus a safe, idempotent way to evolve the model.

## What You Get

**65 MCP tools**: 24 read-only, 41 that change state — 38 of them write to DataForge, the
other three are cache refresh and two import dry runs.

| Category | Tools | What they do |
|----------|-------|--------------|
| **Discovery** | `df_list_projects`, `df_list_versions` | Find projects and their versions |
| **Semantic Layer** | `df_get_measures`, `df_get_dimensions`, `df_get_facts`, `df_get_rmd` | Business metrics, attributes, facts — everything an agent needs to understand the model |
| **SQL Generation** | `df_get_measures` with `include_sql=true`, `df_generate_sql` | Auto-generated SQL for measures and data marts |
| **Data Model** | `df_list_fact_tables`, `df_list_dimension_groups`, `df_list_relationships`, `df_get_*` | Physical model: tables, groups, star-schema links |
| **Data Marts** | `df_list_data_marts`, `df_get_data_mart`, `df_get_data_mart_view` | Data marts with composition and materialized view status |
| **Connections** | `df_list_connections`, `df_get_connection`, `df_get_connection_schema` | Database connections and their cached schemas |
| **Full Export** | `df_get_consolidated_rmd` | The whole version in one call, with optional SQL |
| **⚠️ RMD Writes** | `df_write_measure`, `df_write_dimension`, `df_write_fact`, `df_bulk_write_*`, `df_delete_*` | Create, replace, update and delete RMD content |
| **⚠️ Model Writes** | `df_write_dimension_group`, `df_write_fact_table`, `df_assign_to_fact_table`, `df_write_relationship`, `df_write_verification_filter`, … | Build and change the data model |
| **⚠️ Projects** | `df_create_project`, `df_create_version`, `df_delete_project`, `df_delete_version` | Manage projects and versions |
| **⚠️ Access** | `df_get_project_access`, `df_set_project_access`, `df_revoke_project_access`, `df_transfer_project_ownership` | Project permissions |
| **⚠️ Version Transfer** | `df_export_version_to_git`, `df_import_version_from_git`, `df_check_import_source`, `df_preview_import`, … | CI/CD: move a version between environments |
| **⚠️ Git Connections** | `df_list_git_connections`, `df_create_git_connection`, `df_test_git_connection`, … | The company's saved Git credentials registry |
| **Operations** | `df_health`, `df_refresh_cache` | Health checks and cache management |

See the [Write Tools Reference](docs/api/tools-write.md) for every write tool in detail.

## Quick Start

### 1. Install

```bash
pip install -e ".[dev]"
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATAFORGE_BASE_URL=https://api.prod-df.businessqlik.com
DATAFORGE_API_KEY=your_api_key_here
```

> **The key decides what an agent can do.** A key resolving to `analyst` or `viewer` makes
> this server effectively read-only. A key resolving to `developer` or above lets an agent
> delete data.

### 3. Run

**As an MCP server** (for Claude Desktop, Cursor, etc.):

```bash
python -m dataforge_mcp
```

**As a Python library** (no MCP needed):

```python
import asyncio
from dataforge_mcp import create_semantic_service

async def main():
    service = create_semantic_service()

    # Discover projects
    projects = await service.list_projects()
    project_id = projects["projects"][0]["id"]

    # Get versions, find the production one
    versions = await service.list_versions(project_id=project_id)
    version_id = next(v["id"] for v in versions["versions"] if v["is_global"])

    # Fetch the full semantic model
    rmd = await service.get_rmd(project_id=project_id, version_id=version_id)
    print(f"{rmd['stats']['measure_count']} measures")
    print(f"{rmd['stats']['dimension_count']} dimensions")
    print(f"{rmd['stats']['fact_count']} facts")

asyncio.run(main())
```

## Example: Read, then write

Every measure, dimension and fact carries a stable `id`. That id is what the write tools
take, so a result you just read can be fed straight back:

```python
measures = await service.get_measures(project_id=392, version_id=948)
target = next(m for m in measures["measures"] if m["name"] == "Total revenue")

# mode="update" (PATCH) changes only what you pass
await service.write_measure(
    project_id=392,
    version_id=948,
    mode="update",
    measure_id=int(target["id"]),
    measure_description="Gross revenue across all channels",
)
```

`mode="replace"` (PUT) resets every optional field you omit — use `mode="update"` unless
you intend a full overwrite.

## Example: SQL Code Generation

```python
measures = await service.get_measures(
    project_id=392, version_id=948, include_sql=True
)

for m in measures["measures"]:
    if m.get("sql_code"):
        print(f"--- {m['name']} ---")
        for script in m["sql_code"]["sql_scripts"]:
            print(f"  Table: {script['fact_table_name']}")
            print(f"  SQL:   {script['sql']}")
```

## Example: Explore the Data Model

```python
tables = await service.list_fact_tables(project_id=392, version_id=948)
for ft in tables["fact_tables"]:
    print(f"{ft['name']}: {ft['measures_count']} measures, "
          f"{ft['dimensions_count']} dimensions")

rels = await service.list_relationships(project_id=392, version_id=948)
for r in rels["relationships"]:
    src = r["source_fact_table"]["name"]
    tgt = r["target_dimension_group"]["name"]
    print(f"{src} -> {tgt} ({r['relationship_type']})")  # many_to_one
```

## Example: Generate SQL for a Data Mart

Generation failures come back as data, not as errors — that is what distinguishes
"this data mart cannot produce SQL right now" from "this data mart does not exist":

```python
marts = await service.list_data_marts(project_id=392, version_id=948, search="Sales")
mart_id = int(marts["data_marts"][0]["id"])

result = await service.generate_sql(
    project_id=392, version_id=948, data_mart_id=mart_id, limit=100
)

if result["succeeded"]:
    print(result["sql_script"])
    print("target:", result["target_db_type"])   # postgres | clickhouse | sqlserver
else:
    for err in result["validation_errors"]:
        print("cannot generate:", err["message"])
```

## Write Operations

### Idempotency

Every write generates an `Idempotency-Key` (UUID v4) automatically, and you can supply your
own. Within 24 hours, repeating a `POST` with the same key replays the original response
instead of applying the change twice. This is what makes a retry after a 5xx safe — a
`POST` sent *without* a key is never retried, and a timeout on one is reported with
`possibly_applied: true` so you can verify before resending.

### Partial results

Bulk and assignment calls apply each item in its own transaction. When some items are
rejected, the result comes back with `status: "partial"` and a `failed[]` array addressing
each rejected row by index:

```python
result = await service.bulk_write_measures(
    project_id=392, version_id=948,
    measures=[
        {"measure_name": "Net revenue", "measure_type": "Base"},
        {"id": "1000", "measure_description": "Updated description"},
    ],
)

if result["status"] == "partial":
    for failure in result["failed"]:
        print(failure["index"], failure["error"]["code"])
```

### Required roles

| Operation group | Effective project role |
|---|---|
| All reads | any access to the project |
| RMD and data model writes | `developer` or above |
| Project access management | project owner or company administrator |
| Version export and import dry runs | `analyst` or above |
| Version import | `developer` or above |
| Git connection management | company administrator |

A project the key cannot see answers `404`, not `403` — existence is never disclosed.

### Cache invalidation

A write drops the entire cache scope it touched (the version, or the project), because the
exact set of affected entries cannot be derived from the write's arguments. A read
immediately after a write therefore always hits the API.

### Rate limits

100 requests per 60 seconds per API key. Exceeding it yields
`DATAFORGE_RATE_LIMIT_EXCEEDED` with `retry_after_seconds` taken from the response headers.

## Claude Desktop Integration

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

> ### ⚠️ Before you paste this
>
> The key you put here decides whether an agent can **delete your projects**. Use a key
> with the `analyst` or `viewer` project role for read-only work. Write tools are annotated
> with `readOnlyHint=false` and `destructiveHint=true`, so a well-behaved MCP client asks
> you to confirm — but that confirmation is the client's, not this server's.

Then ask Claude: *"What measures are available in the Fashion Retail project?"* — and it will call `df_list_projects`, `df_list_versions`, `df_get_measures` automatically.

## Docker (SSE mode)

```bash
cp .env.example .env
docker compose up
```

## Documentation

| Document | Description |
|----------|-------------|
| [Semantic Tools Reference](docs/api/tools-semantic.md) | Read tools for measures, dimensions, facts, RMD |
| [Data Model Tools Reference](docs/api/tools-data-model.md) | Read tools for data marts, connections, fact tables, relationships |
| [⚠️ Write Tools Reference](docs/api/tools-write.md) | Every tool that modifies DataForge |
| [Shared Schemas & Errors](docs/api/schemas.md) | Pagination, source objects, error envelope, code catalogue |
| [Configuration & Setup](docs/api/configuration.md) | Environment variables, Docker, architecture |

## Key Features

- **Full DF API v2 surface** — reads, writes, version transfer and Git connection management
- **Safety annotations** — every tool carries MCP `readOnlyHint` / `destructiveHint` so clients can warn before a destructive call
- **Idempotent writes** — automatic `Idempotency-Key` makes retries safe
- **Caching** — file-based cache with TTL and last-known-good fallback for reads; writes never serve stale data and always invalidate their scope
- **Actionable errors** — the v2 error envelope is surfaced with `api_code`, the offending `fields[]` and a hint on how to fix the request
- **Rate limit handling** — 100 req/60 s per key, with `retry_after_seconds`
- **Retry logic** — exponential backoff on 5xx and timeouts; never on 4xx; never on a non-idempotent POST
- **Credential hygiene** — API keys and Git credentials never appear in logs or tool output
- **Library-first** — use directly from Python without running an MCP server

## Development

```bash
pip install -e ".[dev]"    # install
pytest                      # test (412 tests)
ruff check src/ tests/      # lint
ruff format src/ tests/     # format
```

Test fixtures in `tests/fixtures/api_v2.py` are transcribed verbatim from the DataForge
Public API documentation. When the API changes, that file is what gets updated first.

## License

Proprietary. For use with DataForge Product API.
