<div align="center">

# DataForge Semantic MCP Server

**Give your AI agent the business meaning behind your analytics — and the power to change it.**

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP%20SDK-2.x-6E56CF)](https://modelcontextprotocol.io/)
[![DataForge API](https://img.shields.io/badge/DataForge%20API-v2-2479BC)](https://businessqlik.com)
[![Tools](https://img.shields.io/badge/tools-65-success)](#what-you-get)
[![Tests](https://img.shields.io/badge/tests-502%20passing-brightgreen)](#development)
[![License](https://img.shields.io/badge/license-Proprietary-lightgrey)](#license)

[Quick start](#quick-start) · [Tools](#what-you-get) · [Writing data](#writing-data) · [Open WebUI](#open-webui) · [Documentation](#documentation)

</div>

---

> [!CAUTION]
> ## THIS SERVER IS **NOT** READ-ONLY — IT CAN **DELETE YOUR DATA**
>
> **38 of its 65 tools create, overwrite and permanently delete** DataForge content:
> projects, versions, measures, dimensions, facts, dimension groups, fact tables,
> relationships, access grants and Git connections.
>
> | Tool | What it does |
> |---|---|
> | `df_delete_project` | Deletes a project **with every version and all of its content** |
> | `df_import_version_from_git` (`method=replace`) | **Overwrites an entire version** |
> | `df_write_measure` (`mode=replace`) | **Resets every optional field** you do not pass |
>
> ### There is no kill switch in this server.
>
> The only thing between an LLM agent and your production semantic model is the
> **effective project role of the API key** in `DATAFORGE_API_KEY`.
>
> ### ➜ Want read-only? Use a read-only key.
>
> Issue a key whose project role is **`analyst` or `viewer`**. Every write endpoint requires
> `developer` or above and answers `403 DF_API.WRITE_ACCESS_DENIED` — **the API enforces
> this, this server does not.** Point agents at a non-production version first.
>
> Every write lands in the DataForge audit log with before/after snapshots.

---

## Why

DataForge holds the **business definitions** behind your analytics: what "Total Revenue"
actually means, which database column feeds it, how customers are grouped. Without that
context an AI agent is guessing.

This server hands the agent that context — structured, normalized and cached — and gives
it a safe, idempotent way to evolve the model.

## What You Get

**65 MCP tools** — 24 read-only, 41 that change state (38 of them write to DataForge).

### Read — 24 tools

| Group | Tools |
|---|---|
| **Discovery** | `df_list_projects` · `df_list_versions` |
| **Semantic layer** | `df_get_measures` · `df_get_dimensions` · `df_get_facts` · `df_get_rmd` |
| **SQL generation** | `df_generate_sql` · `df_get_measures(include_sql=true)` |
| **Data model** | `df_list_fact_tables` · `df_get_fact_table` · `df_list_dimension_groups` · `df_get_dimension_group` · `df_list_relationships` · `df_get_relationship` |
| **Data marts** | `df_list_data_marts` · `df_get_data_mart` · `df_get_data_mart_view` |
| **Connections** | `df_list_connections` · `df_get_connection` · `df_get_connection_schema` |
| **Full export** | `df_get_consolidated_rmd` |
| **Access & Git** | `df_get_project_access` · `df_list_git_connections` · `df_get_git_connection` |
| **Ops** | `df_health` |

### Write — 41 tools ⚠️

| Group | Tools |
|---|---|
| **RMD content** | `df_write_measure` · `df_write_dimension` · `df_write_fact` · `df_bulk_write_measures` · `df_bulk_write_dimensions` · `df_bulk_write_facts` · `df_delete_measure` · `df_delete_dimension` · `df_delete_fact` |
| **Dimension groups** | `df_write_dimension_group` · `df_set_group_dimensions` · `df_remove_group_dimension` · `df_delete_dimension_group` |
| **Fact tables** | `df_write_fact_table` · `df_assign_to_fact_table` · `df_unassign_from_fact_table` · `df_delete_fact_table` |
| **Filters & links** | `df_write_verification_filter` · `df_delete_verification_filter` · `df_write_relationship` · `df_delete_relationship` |
| **Projects & versions** | `df_create_project` · `df_update_project` · `df_delete_project` · `df_create_version` · `df_update_version` · `df_delete_version` |
| **Access** | `df_set_project_access` · `df_revoke_project_access` · `df_transfer_project_ownership` |
| **Version transfer** | `df_export_version_to_git` · `df_export_version_to_file` · `df_check_import_source` · `df_preview_import` · `df_import_version_from_git` · `df_import_version_from_file` |
| **Git connections** | `df_create_git_connection` · `df_update_git_connection` · `df_delete_git_connection` · `df_test_git_connection` |
| **Local state** | `df_refresh_cache` — clears this server's cache, touches no DataForge data |

Full reference: [read tools](docs/api/tools-semantic.md) · [data model](docs/api/tools-data-model.md) · [**write tools**](docs/api/tools-write.md)

## Quick Start

### 1 · Install

```bash
pip install -e ".[dev]"
```

### 2 · Configure

```bash
cp .env.example .env
```

```env
DATAFORGE_BASE_URL=https://api.prod-df.businessqlik.com
DATAFORGE_API_KEY=your_api_key_here
```

`DATAFORGE_BASE_URL` is the root of the **API**, not of the site — requests go to
`<base>/df-api/v2/…`. Installations that serve the API behind a prefix need it spelled out
(`https://dataforge.example.com/api`); point it at the site root and the web app answers
with HTML and `HTTP 200`, which the server reports as `DATAFORGE_INVALID_RESPONSE`.

> [!WARNING]
> **The key decides what an agent can destroy.** `analyst` / `viewer` → effectively
> read-only. `developer` and above → can delete measures, versions and whole projects.

### 3 · Run

```bash
python -m dataforge_mcp          # stdio, for Claude Desktop / Cursor
docker compose up                # Streamable HTTP on http://localhost:8080/mcp
```

| Transport | `MCP_TRANSPORT` | Clients |
|---|---|---|
| stdio | `stdio` (default) | Claude Desktop, Cursor |
| Streamable HTTP | `streamable-http` | Open WebUI, MCP Inspector, remote deployments |
| HTTP+SSE | `sse` | **Deprecated** — kept for existing deployments |

Over HTTP the port is the only thing between the network and the 38 write tools, so set
`MCP_AUTH_TOKEN` for any bind that is not loopback. Full reference:
[docs/api/transports.md](docs/api/transports.md).

Or skip MCP entirely and use it as a library:

```python
import asyncio
from dataforge_mcp import create_semantic_service

async def main():
    service = create_semantic_service()

    projects = await service.list_projects()
    project_id = projects["projects"][0]["id"]

    versions = await service.list_versions(project_id=project_id)
    version_id = next(v["id"] for v in versions["versions"] if v["is_global"])

    rmd = await service.get_rmd(project_id=project_id, version_id=version_id)
    print(f"{rmd['stats']['measure_count']} measures, "
          f"{rmd['stats']['dimension_count']} dimensions, "
          f"{rmd['stats']['fact_count']} facts")

asyncio.run(main())
```

## Claude Desktop

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

> [!CAUTION]
> **Before you paste this:** the key above decides whether an agent can delete your
> projects. Use an `analyst` / `viewer` key for read-only work. Write tools carry
> `readOnlyHint=false` and `destructiveHint=true`, so a well-behaved client asks you to
> confirm — but that confirmation belongs to the client, not to this server.

Then ask Claude: *"What measures are available in the Fashion Retail project?"* — it will
chain `df_list_projects` → `df_list_versions` → `df_get_measures` on its own.

## Open WebUI

Open WebUI speaks **Streamable HTTP only**, which this server now serves natively — no
`mcpo` proxy needed.

```bash
cp .env.example .env
# set DATAFORGE_API_KEY, and MCP_AUTH_TOKEN:
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
docker compose up -d
```

Then in Open WebUI, as an administrator: **Settings → Admin → Integrations → + Add
Connection**, type **MCP (Streamable HTTP)**, URL `http://host.docker.internal:8080/mcp`,
Auth **Bearer** with your `MCP_AUTH_TOKEN`. All 65 tools appear.

> [!WARNING]
> Every Open WebUI user who can use the tools gets all 65, including the 38 that delete
> data — and they all share one DataForge key. Start with an `analyst` / `viewer` key and a
> non-production version.

Full walkthrough, URL table and troubleshooting: [docs/api/open-webui.md](docs/api/open-webui.md).

## Examples

### Read, then write

Every measure, dimension and fact carries a stable `id`. That id is exactly what the write
tools take, so a row you just read goes straight back:

```python
measures = await service.get_measures(project_id=392, version_id=948)
target = next(m for m in measures["measures"] if m["name"] == "Total revenue")

await service.write_measure(
    project_id=392, version_id=948,
    mode="update",                       # PATCH — touches only what you pass
    measure_id=int(target["id"]),
    measure_description="Gross revenue across all channels",
)
```

> `mode="replace"` is a PUT: it **resets every optional field you omit**. Use `update`
> unless you mean a full overwrite.

### SQL for a measure

```python
measures = await service.get_measures(project_id=392, version_id=948, include_sql=True)

for m in measures["measures"]:
    if m.get("sql_code"):
        for script in m["sql_code"]["sql_scripts"]:
            print(f"{m['name']} @ {script['fact_table_name']}:\n  {script['sql']}")
```

### SQL for a data mart

A generation failure comes back as **data, not an error** — that is what separates "this
mart cannot produce SQL right now" from "this mart does not exist":

```python
marts = await service.list_data_marts(project_id=392, version_id=948, search="Sales")
mart_id = int(marts["data_marts"][0]["id"])

result = await service.generate_sql(
    project_id=392, version_id=948, data_mart_id=mart_id, limit=100
)

if result["succeeded"]:
    print(result["target_db_type"], result["sql_script"])   # postgres | clickhouse | sqlserver
else:
    for err in result["validation_errors"]:
        print("cannot generate:", err["message"])
```

### Explore the star schema

```python
tables = await service.list_fact_tables(project_id=392, version_id=948)
for ft in tables["fact_tables"]:
    print(f"{ft['name']}: {ft['measures_count']}M / {ft['dimensions_count']}D")

rels = await service.list_relationships(project_id=392, version_id=948)
for r in rels["relationships"]:
    print(f"{r['source_fact_table']['name']} -> "
          f"{r['target_dimension_group']['name']} ({r['relationship_type']})")
```

## Writing Data

<details>
<summary><b>Idempotency — why a retry is safe</b></summary>

Every write generates an `Idempotency-Key` (UUID v4); you can also supply your own. Within
24 hours, repeating a `POST` with the same key **replays the original response** instead of
applying the change twice.

That is what makes a retry after a 5xx safe. A `POST` sent *without* a key is **never
retried**, and a timeout on one is reported with `possibly_applied: true` so you verify
before resending.

</details>

<details>
<summary><b>Partial results — 207 is never hidden</b></summary>

Bulk and assignment calls apply each item in its own transaction. When some are rejected,
the result says so explicitly:

```python
result = await service.bulk_write_measures(
    project_id=392, version_id=948,
    measures=[
        {"measure_name": "Net revenue", "measure_type": "Base"},   # created
        {"id": "1000", "measure_description": "Updated"},          # updated
    ],
)

if result["status"] == "partial":
    for failure in result["failed"]:
        print(failure["index"], failure["error"]["code"])
```

</details>

<details>
<summary><b>Required roles</b></summary>

| Operation | Effective project role |
|---|---|
| All reads | any access to the project |
| RMD and data model writes | `developer` or above |
| Project access management | project owner or company administrator |
| Version export, import dry runs | `analyst` or above |
| Version import | `developer` or above |
| Git connection management | company administrator |

A project the key cannot see answers `404`, never `403` — existence is never disclosed.

</details>

<details>
<summary><b>Errors an agent can actually fix</b></summary>

The v2 error envelope is surfaced in full, including which field was wrong and why:

```json
{
  "error": {
    "code": "DATAFORGE_INVALID_SOURCE_TABLE",
    "api_code": "invalid_source_table",
    "message": "Table not found in the connection schema",
    "fields": [{ "field": "connected_source.table", "code": "invalid_value" }],
    "hint": "Call df_get_connection_schema to list the tables cached for this connection.",
    "retryable": false
  }
}
```

Local validation produces the **same shape**, so the agent never learns two formats.

</details>

<details>
<summary><b>Cache behaviour</b></summary>

Reads are cache-first with TTL and a last-known-good fallback: if the API goes down you
still get the last successful response.

Writes do the opposite — they never read the cache, never serve stale data, and drop the
whole scope they touched. A read right after a write always hits the API.

</details>

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Tools fail with `DATAFORGE_INVALID_RESPONSE`, or `df_health` returns `product_api_status: unavailable` with a `product_api_error` about HTML | `DATAFORGE_BASE_URL` points at the site root, so the web app answers instead of the API | Add the API prefix, usually `/api` |
| `ModuleNotFoundError: No module named 'dataforge_mcp.cache'` | Installed from a tree older than 0.3.1, where `.gitignore` kept the package out of the wheel | Reinstall from 0.3.1 or newer |
| `AttributeError: 'Server' object has no attribute 'list_tools'` | MCP SDK version mismatch | This server needs `mcp>=2.2,<3`; re-run `pip install -e ".[dev]"` |
| `Invalid tool arguments` | An argument is missing, misspelled, or a type that cannot be coerced | Read `fields[]` — each entry names the argument and what was expected. Ids may be strings: `"18"` is accepted |
| On Windows, the endpoint 404s although the container started cleanly | Git Bash rewrote `-e MCP_HTTP_PATH=/mcp` into `C:/Program Files/Git/mcp` | Prefix the command with `MSYS_NO_PATHCONV=1`, or use `docker compose` |
| Every request gets `401` and no token was ever set | `MCP_AUTH_TOKEN` present but empty | Unset it, or give it a real value |

More, per area: [configuration.md](docs/api/configuration.md#troubleshooting) ·
[transports.md](docs/api/transports.md#troubleshooting)

## Documentation

| | |
|---|---|
| [Semantic Tools](docs/api/tools-semantic.md) | Measures, dimensions, facts, RMD |
| [Data Model Tools](docs/api/tools-data-model.md) | Data marts, connections, fact tables, relationships |
| [**Write Tools** ⚠️](docs/api/tools-write.md) | Everything that modifies DataForge |
| [Schemas & Errors](docs/api/schemas.md) | Source objects, pagination, error catalogue |
| [Configuration](docs/api/configuration.md) | Environment, Docker, architecture |
| [Transports](docs/api/transports.md) | stdio, Streamable HTTP, auth, Origin validation, proxies |
| [Open WebUI](docs/api/open-webui.md) | Step-by-step connection guide |
| [Transport Decisions](docs/api/transport-decisions.md) | Why the transport works the way it does |

## Key Features

- **Complete DF API v2 surface** — reads, writes, version transfer, Git connection registry
- **Three transports** — stdio, Streamable HTTP (Open WebUI-ready, with bearer auth and Origin validation), and legacy SSE
- **Safety annotations** — every tool carries MCP `readOnlyHint` / `destructiveHint`, so clients can warn before a destructive call
- **Idempotent writes** — automatic `Idempotency-Key` makes retries safe
- **Smart caching** — TTL + last-known-good for reads; scope invalidation for writes
- **Actionable errors** — `api_code`, offending `fields[]` and a fix hint
- **Rate-limit aware** — 100 req/60 s per key, with `retry_after_seconds`
- **Credential hygiene** — API keys and Git tokens never reach logs or tool output
- **Library-first** — usable from plain Python, no MCP server required

## Development

```bash
pip install -e ".[dev]"
pytest                                       # 502 tests
pytest tests/test_mcp_server.py -v           # end-to-end over MCP, stdio path
pytest tests/test_mcp_streamable_http.py -v  # end-to-end over MCP, HTTP path
ruff check src/ tests/
ruff format src/ tests/
```

Fixtures in `tests/fixtures/api_v2.py` are transcribed **verbatim from the DataForge API
documentation**. When the API changes, that file is what gets updated first — inventing
fixtures is how a v1-shaped test suite once hid five real defects.

## License

Proprietary. For use with the DataForge Product API.
