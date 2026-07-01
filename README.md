# DataForge Semantic MCP Server

> Give your AI agent access to the DataForge semantic layer — measures, dimensions, facts, data marts, and SQL code generation — through a simple MCP interface.

**DataForge Semantic MCP Server** is a read-only gateway that connects AI agents (Claude, Cursor, custom MCP clients) to [DataForge](https://businessqlik.com) Product API v2. It fetches, normalizes, and caches the semantic metadata so your agent always gets clean, consistent data.

## Why?

DataForge stores the **business definitions** behind your analytics: what "Total Revenue" means, which database columns feed it, how customer dimensions are grouped. Without this context, AI agents are working blind.

This server gives them that context — structured, cached, and ready to use.

## What You Get

**22 MCP tools** covering the full semantic layer:

| Category | Tools | What they do |
|----------|-------|-------------|
| **Discovery** | `df_list_projects`, `df_list_versions` | Find projects and their versions |
| **Semantic Layer** | `df_get_measures`, `df_get_dimensions`, `df_get_facts`, `df_get_rmd` | Business metrics, attributes, facts — everything an agent needs to understand the data model |
| **SQL Generation** | `df_get_measures` with `include_sql=true`, `df_generate_sql` | Get auto-generated SQL code for measures and data marts |
| **Data Model** | `df_list_fact_tables`, `df_list_dimension_groups`, `df_list_relationships` | Physical model: tables, groups, star schema links |
| **Data Marts** | `df_list_data_marts`, `df_get_data_mart`, `df_get_data_mart_view` | Logical data marts with their composition |
| **Connections** | `df_list_connections`, `df_get_connection`, `df_get_connection_schema` | Database connections and schemas |
| **Full Export** | `df_get_consolidated_rmd` | Everything in one call, with optional SQL code |
| **Operations** | `df_health`, `df_refresh_cache` | Health checks and cache management |

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

## Example: SQL Code Generation

The killer feature of v2 — get generated SQL for any measure:

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

Output:

```
--- Total Revenue ---
  Table: orders
  SQL:   SELECT SUM(amount) FROM orders
--- Gross Margin ---
  Table: orders
  SQL:   SELECT SUM(amount) - SUM(cost) FROM orders
```

## Example: Explore the Data Model

```python
# List fact tables with metadata
tables = await service.list_fact_tables(project_id=392, version_id=948)
for ft in tables["fact_tables"]:
    print(f"{ft['name']}: {ft.get('measures_count', '?')} measures, "
          f"{ft.get('dimensions_count', '?')} dimensions")

# Get relationships between tables and dimension groups
rels = await service.list_relationships(project_id=392, version_id=948)
for r in rels["relationships"]:
    src = r["source_fact_table"]["name"]
    tgt = r["target_dimension_group"]["name"]
    print(f"{src} -> {tgt} ({r.get('relationship_type', 'unknown')})")
```

## Example: Generate SQL for a Data Mart

```python
# Find a data mart
marts = await service.list_data_marts(project_id=392, version_id=948, search="Sales")
mart_id = marts["data_marts"][0]["id"]

# Generate SQL (read-only, never executed)
result = await service.generate_sql(project_id=392, version_id=948, data_mart_id=mart_id)
print(result["sql"])
```

## Claude Desktop Integration

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

Then ask Claude: *"What measures are available in the Fashion Retail project?"* — and it will call `df_list_projects`, `df_list_versions`, `df_get_measures` automatically.

## Docker (SSE mode)

```bash
cp .env.example .env
docker compose up
```

## Documentation

| Document | Description |
|----------|-------------|
| [Semantic Tools Reference](docs/api/tools-semantic.md) | Detailed docs for all semantic tools (measures, dimensions, facts, RMD) |
| [Data Model Tools Reference](docs/api/tools-data-model.md) | Detailed docs for data model tools (data marts, fact tables, relationships) |
| [Shared Schemas & Errors](docs/api/schemas.md) | Pagination, connected sources, SQL code objects, error codes |
| [Configuration & Setup](docs/api/configuration.md) | Environment variables, Docker setup, architecture |

## Key Features

- **DF API v2** — unified API surface, SQL code generation for measures
- **Caching** — file-based cache with TTL and last-known-good fallback (if the API goes down, you still get the last successful response)
- **Normalization** — inconsistent API field names mapped to clean canonical models
- **Rate Limit Handling** — HTTP 429 gracefully mapped to `DATAFORGE_RATE_LIMIT_EXCEEDED`
- **Retry Logic** — exponential backoff on 5xx errors and timeouts (no retry on 4xx)
- **Library-first** — use directly from Python without running an MCP server

## Development

```bash
pip install -e ".[dev]"    # install
pytest                      # test (88 tests)
ruff check src/ tests/      # lint
ruff format src/ tests/     # format
```

## License

Proprietary. For use with DataForge Product API.
