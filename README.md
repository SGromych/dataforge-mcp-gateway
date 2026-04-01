# DataForge Semantic MCP Server

Read-only semantic gateway between AI agents and [DataForge](https://businessqlik.com) Product API. Fetches projects, versions, measures, dimensions and full RMD (Reference Model Data), normalizes and caches the data, and exposes it via MCP protocol or as a Python library.

## What This Server Provides

DataForge stores **semantic layer metadata** — the business definitions of measures and dimensions used in analytics projects. This MCP server gives AI agents structured access to that metadata:

- **Projects** — top-level containers for analytics models
- **Versions** — snapshots of a project's semantic layer (one version can be marked as "global"/production)
- **Measures** — business metrics (e.g. "Total Revenue", "Gross Margin") with formulas, data types, source mappings
- **Dimensions** — attributes for slicing data (e.g. "Customer Segment", "Region") with grouping and source mappings
- **RMD** — full Reference Model Data combining all measures and dimensions in one response

All responses are **JSON**. The server normalizes raw DataForge API fields into a clean, stable schema so AI agents get consistent data regardless of API changes.

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

## MCP Tools — Detailed Reference

All tools return JSON via MCP `TextContent`. Every response has a stable schema described below.

### `df_health`

Check server, API and cache status.

**Input:** none

**Output:**

```json
{
  "server_status": "ok",
  "product_api_status": "ok",
  "base_url": "https://api.prod-df.businessqlik.com",
  "cache_status": "ok"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `server_status` | `string` | Always `"ok"` if the server is running |
| `product_api_status` | `string` | `"ok"` or `"unavailable"` |
| `base_url` | `string` | Configured DataForge API base URL |
| `cache_status` | `string` | `"ok"` or `"unavailable"` |

---

### `df_list_projects`

List available DataForge projects accessible with the configured API key.

**Input:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `integer` | `1` | Page number |
| `page_size` | `integer` | `100` | Items per page |
| `use_cache` | `boolean` | `true` | Use cached data if available |

**Output:**

```json
{
  "projects": [
    {
      "id": 392,
      "name": "Fashion Retail",
      "description": "Retail analytics project"
    }
  ],
  "pagination": {
    "total": 10,
    "page": 1,
    "page_size": 100,
    "total_pages": 1
  }
}
```

**Project fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Unique project identifier |
| `name` | `string` | Project name |
| `description` | `string \| null` | Project description |

---

### `df_list_versions`

List versions for a specific project.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `page` | `integer` | no | `1` | Page number |
| `page_size` | `integer` | no | `100` | Items per page |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "project_id": 392,
  "versions": [
    {
      "id": 948,
      "name": "Global Version",
      "is_global": true
    }
  ],
  "pagination": {
    "total": 5,
    "page": 1,
    "page_size": 100,
    "total_pages": 1
  }
}
```

**Version fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Unique version identifier |
| `name` | `string` | Version name |
| `is_global` | `boolean` | Whether this is the global (production) version |

---

### `df_get_measures`

Get all measures (business metrics) for a project version.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default (`ru`) | Language for localized names |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "project_id": 392,
  "version_id": 948,
  "measures": [
    {
      "row_number": "1",
      "group": "Sales",
      "block": "Revenue",
      "name": "Total Revenue",
      "description": "Total revenue from all sales",
      "data_type": "Numeric",
      "measure_type": "Sum",
      "formula": "[Revenue]",
      "restrictions": null,
      "connected_source": {
        "db": "Sales DB",
        "schema": null,
        "table": "sales_table",
        "column": null
      },
      "original_source_type": "Database",
      "original_source": "Sales DB",
      "original_object": "sales_table",
      "report_for_verification": null,
      "comment": "Primary revenue metric",
      "display_data_type": null,
      "status": "Active",
      "relevance": "High",
      "required": true,
      "visibility": "Public",
      "responsible_for_data": "Data Team",
      "variation": null,
      "raw": {}
    }
  ]
}
```

**Measure fields:**

| Field | Type | Description |
|-------|------|-------------|
| `row_number` | `string \| integer \| null` | Row number from RMD spreadsheet |
| `group` | `string \| null` | Business group (e.g. "Sales", "Finance") |
| `block` | `string \| null` | Block within a group (e.g. "Revenue", "Costs") |
| `name` | `string \| null` | Measure name (localized) |
| `description` | `string \| null` | Human-readable description |
| `data_type` | `string \| null` | Data type (e.g. "Numeric", "String") |
| `measure_type` | `string \| null` | Aggregation type (e.g. "Sum", "Count", "Average") |
| `formula` | `string \| null` | Calculation formula |
| `restrictions` | `string \| null` | Any restrictions or filters applied |
| `connected_source` | `object \| null` | Database source mapping (see below) |
| `original_source_type` | `string \| null` | Source type (e.g. "Database") |
| `original_source` | `string \| null` | Original data source name |
| `original_object` | `string \| null` | Original object (table/view) name |
| `report_for_verification` | `string \| null` | Report used to verify this measure |
| `comment` | `string \| null` | Additional notes |
| `display_data_type` | `string \| null` | Display format type |
| `status` | `string \| null` | Status (e.g. "Active", "Draft") |
| `relevance` | `string \| null` | Relevance level (e.g. "High", "Medium", "Low") |
| `required` | `boolean \| null` | Whether the measure is required |
| `visibility` | `string \| null` | Visibility level (e.g. "Public", "Internal") |
| `responsible_for_data` | `string \| null` | Team/person responsible for data quality |
| `variation` | `string \| null` | Measure variation/variant |
| `raw` | `object` | Original unmodified API response (empty by default) |

---

### `df_get_dimensions`

Get all dimensions (attributes for slicing/filtering data) for a project version.

**Input:** same as `df_get_measures`.

**Output:**

```json
{
  "project_id": 392,
  "version_id": 948,
  "dimensions": [
    {
      "row_number": "1",
      "group": "Sales",
      "block": "Customer",
      "name": "Customer ID",
      "description": "Unique customer identifier",
      "dimension_group": "Customer Attributes",
      "data_type": "String",
      "connected_source": {
        "db": 161,
        "schema": null,
        "table": "customers",
        "column": "CompanyName"
      },
      "dimension_type": null,
      "original_source_type": "Database",
      "original_source": "Sales DB",
      "original_object": "customers_table",
      "comment": "Primary key for customers",
      "formula": null,
      "value_options": null,
      "display_data_type": null,
      "source_data_type": null,
      "status": "Active",
      "relevance": "High",
      "required": true,
      "visibility": "Public",
      "responsible_for_data": "Data Team",
      "raw": {}
    }
  ]
}
```

**Dimension fields:**

| Field | Type | Description |
|-------|------|-------------|
| `row_number` | `string \| integer \| null` | Row number from RMD spreadsheet |
| `group` | `string \| null` | Business group |
| `block` | `string \| null` | Block within a group |
| `name` | `string \| null` | Dimension name (localized) |
| `description` | `string \| null` | Human-readable description |
| `dimension_group` | `string \| null` | Logical grouping of dimensions (e.g. "Customer Attributes") |
| `data_type` | `string \| null` | Data type (e.g. "String", "Integer", "Date") |
| `connected_source` | `object \| null` | Database source mapping (see below) |
| `dimension_type` | `string \| null` | Dimension type classification |
| `original_source_type` | `string \| null` | Source type |
| `original_source` | `string \| null` | Original data source name |
| `original_object` | `string \| null` | Original object name |
| `comment` | `string \| null` | Additional notes |
| `formula` | `string \| null` | Calculation formula (if computed) |
| `value_options` | `string \| array \| null` | Allowed values or value list |
| `display_data_type` | `string \| null` | Display format type |
| `source_data_type` | `string \| null` | Data type in the source system |
| `status` | `string \| null` | Status (e.g. "Active", "Draft") |
| `relevance` | `string \| null` | Relevance level |
| `required` | `boolean \| null` | Whether the dimension is required |
| `visibility` | `string \| null` | Visibility level |
| `responsible_for_data` | `string \| null` | Team/person responsible for data quality |
| `raw` | `object` | Original unmodified API response (empty by default) |

---

### `df_get_rmd`

Get full RMD — all measures and dimensions for a project version in a single call.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default | Language for localized names |
| `use_cache` | `boolean` | no | `true` | Use cached data |
| `include_raw` | `boolean` | no | `false` | Include raw API response in each entity |

**Output:**

```json
{
  "project": {
    "id": 392,
    "name": "Fashion Retail",
    "description": null
  },
  "version": {
    "id": 948,
    "name": "Global Version",
    "is_global": true
  },
  "measures": [ /* array of Measure objects (see df_get_measures) */ ],
  "dimensions": [ /* array of Dimension objects (see df_get_dimensions) */ ],
  "stats": {
    "measure_count": 120,
    "dimension_count": 75
  }
}
```

When `include_raw` is `false` (default), the `raw` field is stripped from every measure and dimension to reduce response size.

---

### `df_refresh_cache`

Force refresh cached data for a project version.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default | Language |

**Output:**

```json
{
  "status": "refreshed",
  "cache_key": "rmd:392:948:ru",
  "fetched_at": "2026-03-29T12:00:00+00:00"
}
```

---

## Connected Source Object

Measures and dimensions can reference their physical database source:

```json
{
  "db": "Sales DB",
  "schema": null,
  "table": "sales_table",
  "column": "revenue"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `db` | `string \| integer \| null` | Database name or ID |
| `schema` | `string \| null` | Database schema |
| `table` | `string \| null` | Table or view name |
| `column` | `string \| null` | Column name |

## Error Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "DATAFORGE_API_KEY_INVALID",
    "message": "Invalid API key",
    "details": {
      "http_status": 401
    }
  }
}
```

**Error codes:**

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `DATAFORGE_API_KEY_MISSING` | 401 | `X-Api-Key` header not provided |
| `DATAFORGE_API_KEY_INVALID` | 401 | Invalid API key |
| `DATAFORGE_UNAUTHORIZED` | 401 | Unauthorized (IP not whitelisted, account blocked, etc.) |
| `DATAFORGE_AUTH_FAILED` | 401 | Authentication failed |
| `DATAFORGE_RESOURCE_NOT_FOUND` | 404 | Project, version, or resource not found |
| `DATAFORGE_API_ERROR` | 5xx | Server-side error (retried automatically) |

## Typical AI Agent Workflow

A typical workflow for an AI agent using this server:

```
1. df_health              → verify connectivity
2. df_list_projects       → discover available projects
3. df_list_versions       → find the global (production) version
4. df_get_rmd             → fetch all measures and dimensions at once
   (or df_get_measures / df_get_dimensions separately)
5. Use the semantic metadata to understand the data model,
   generate queries, or answer business questions
```

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
