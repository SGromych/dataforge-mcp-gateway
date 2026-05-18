# DataForge Semantic MCP Server

Read-only semantic gateway between AI agents and [DataForge](https://businessqlik.com) Product API. Fetches projects, versions, measures, dimensions, facts and full RMD (Reference Model Data) plus data model entities (data marts, connections, dimension groups, fact tables, relationships), normalizes and caches the data, and exposes it via MCP protocol or as a Python library.

## What This Server Provides

DataForge stores **semantic layer metadata** -- the business definitions of measures, dimensions, and facts used in analytics projects. This MCP server gives AI agents structured access to that metadata:

- **Projects** -- top-level containers for analytics models
- **Versions** -- snapshots of a project's semantic layer (one version can be marked as "global"/production)
- **Measures** -- business metrics (e.g. "Total Revenue", "Gross Margin") with formulas, data types, source mappings
- **Dimensions** -- attributes for slicing data (e.g. "Customer Segment", "Region") with grouping and source mappings
- **Facts** -- factual data elements (e.g. "Order Amount") with types, formulas, source mappings
- **RMD** -- full Reference Model Data combining all measures, dimensions, and facts in one response

Additionally, the **DF API** surface exposes data model entities:

- **Data Marts** -- logical data marts with selected measures, dimensions, facts
- **Connections** -- database connections with types and status
- **Dimension Groups** -- logical groupings of dimensions with primary keys
- **Fact Tables** -- physical fact tables with measures, dimensions, facts
- **Relationships** -- links between fact tables and dimension groups
- **Consolidated RMD** -- full data model export via DF API

All responses are **JSON**. The server normalizes raw DataForge API fields into a clean, stable schema so AI agents get consistent data regardless of API changes.

## Features

- **Library-first** -- use directly from Python, no MCP server required
- **MCP adapter** -- 22 tools for Claude Desktop, Cursor and other MCP clients
- **Caching** -- file-based cache with TTL and last-known-good fallback
- **Normalization** -- inconsistent API fields mapped to clean canonical models
- **Retry & error handling** -- exponential backoff on 5xx, proper error codes for auth issues

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
    print(f"Facts: {rmd['stats']['fact_count']}")

    # DF API: data model entities
    data_marts = await service.list_data_marts(project_id=392, version_id=948)
    print(data_marts)

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

---

## MCP Tools -- Detailed Reference

All tools return JSON via MCP `TextContent`. Every response has a stable schema described below.

---

### RMD API Tools

---

#### `df_health`

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

#### `df_list_projects`

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

#### `df_list_versions`

List versions for a specific project.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
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

#### `df_get_measures`

Get all measures (business metrics) for a project version.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
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
| `connected_source` | `object \| null` | Database source mapping (see [Connected Source](#connected-source-object)) |
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

#### `df_get_dimensions`

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
| `connected_source` | `object \| null` | Database source mapping (see [Connected Source](#connected-source-object)) |
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

#### `df_get_facts`

Get all facts for a project version.

**Input:** same as `df_get_measures`.

**Output:**

```json
{
  "project_id": 392,
  "version_id": 948,
  "facts": [
    {
      "row_number": "1",
      "group": "Sales",
      "block": "Orders",
      "name": "Order Amount",
      "description": "Total order amount",
      "original_source_type": "Database",
      "original_source": "Sales DB",
      "original_object": "orders_table",
      "source_data_type": "Decimal",
      "fact_type": "Additive",
      "formula": "[Amount]",
      "connected_source": {
        "db": "Sales DB",
        "schema": null,
        "table": "orders",
        "column": null
      },
      "report_for_verification": null,
      "comment": null,
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

**Fact fields:**

| Field | Type | Description |
|-------|------|-------------|
| `row_number` | `string \| integer \| null` | Row number from RMD spreadsheet |
| `group` | `string \| null` | Business group |
| `block` | `string \| null` | Block within a group |
| `name` | `string \| null` | Fact name (localized, from `fact_name`) |
| `description` | `string \| null` | Description (from `fact_description`) |
| `original_source_type` | `string \| null` | Source type |
| `original_source` | `string \| null` | Original data source name |
| `original_object` | `string \| null` | Original object name |
| `source_data_type` | `string \| null` | Data type in source system |
| `fact_type` | `string \| null` | Fact type (e.g. "Additive") |
| `formula` | `string \| null` | Calculation formula |
| `connected_source` | `object \| null` | Database source mapping (see [Connected Source](#connected-source-object)) |
| `report_for_verification` | `string \| null` | Verification report |
| `comment` | `string \| null` | Additional notes |
| `status` | `string \| null` | Status (e.g. "Active", "Draft") |
| `relevance` | `string \| null` | Relevance level |
| `required` | `boolean \| null` | Whether the fact is required |
| `visibility` | `string \| null` | Visibility level |
| `responsible_for_data` | `string \| null` | Responsible team/person |
| `raw` | `object` | Original unmodified API response (empty by default) |

---

#### `df_get_rmd`

Get full RMD -- all measures, dimensions, and facts for a project version in a single call. This is the most common starting point for AI agents.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `language` | `string` | no | config default | Language for localized names |
| `use_cache` | `boolean` | no | `true` | Use cached data |
| `include_raw` | `boolean` | no | `false` | Include raw API response in each entity |

**Output:**

```json
{
  "project": {
    "id": 392,
    "name": "",
    "description": null
  },
  "version": {
    "id": 948,
    "name": "",
    "is_global": false
  },
  "measures": [
    {
      "name": "Total Revenue",
      "description": "Total revenue from all sales",
      "measure_type": "Sum",
      "formula": "[Revenue]",
      "..."
    }
  ],
  "dimensions": [
    {
      "name": "Customer ID",
      "description": "Unique customer identifier",
      "dimension_group": "Customer Attributes",
      "..."
    }
  ],
  "facts": [
    {
      "name": "Order Amount",
      "description": "Total order amount",
      "fact_type": "Additive",
      "..."
    }
  ],
  "stats": {
    "measure_count": 120,
    "dimension_count": 75,
    "fact_count": 30
  }
}
```

When `include_raw` is `false` (default), the `raw` field is stripped from every measure, dimension, and fact to reduce response size. Each entity in `measures`, `dimensions`, `facts` has the same fields as described in `df_get_measures`, `df_get_dimensions`, `df_get_facts` respectively.

---

#### `df_refresh_cache`

Force refresh cached data for a project version. Invalidates measures, dimensions, facts, and RMD cache keys, then re-fetches RMD.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `language` | `string` | no | config default | Language |

**Output:**

```json
{
  "status": "refreshed",
  "cache_key": "rmd:392:948:ru",
  "fetched_at": "2026-03-29T12:00:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Always `"refreshed"` on success |
| `cache_key` | `string` | The primary cache key that was refreshed |
| `fetched_at` | `string` | ISO 8601 timestamp of when data was fetched |

---

### DF API Tools (Data Model)

All DF API tools require `project_id` and `version_id`. They use the same base URL and API key as RMD API tools. These tools expose the physical data model: how measures, dimensions, and facts are organized into data marts, fact tables, dimension groups, and connected via relationships.

---

#### `df_list_data_marts`

List data marts for a project version. Data marts are logical groupings that combine selected measures, dimensions, and facts from fact tables.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `language` | `string` | no | config default | Language |
| `type` | `string` | no | -- | Filter by data mart type |
| `merge_type` | `string` | no | -- | Filter by merge type |
| `search` | `string` | no | -- | Search by name |
| `page` | `integer` | no | `1` | Page number |
| `page_size` | `integer` | no | `100` | Items per page |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "project_id": 392,
  "version_id": 948,
  "data_marts": [
    {
      "id": 1,
      "name": "Sales Mart",
      "type": "standard",
      "merge_type": "union",
      "description": "Main sales data mart"
    }
  ],
  "pagination": {
    "total": 3,
    "page": 1,
    "page_size": 100,
    "total_pages": 1
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Unique data mart identifier |
| `name` | `string \| null` | Data mart name |
| `type` | `string \| null` | Data mart type |
| `merge_type` | `string \| null` | How multiple sources are merged |
| `description` | `string \| null` | Data mart description |

---

#### `df_get_data_mart`

Get data mart details including selected measures, dimensions, facts, and source fact tables.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `data_mart_id` | `integer` | yes | -- | Data mart ID |
| `language` | `string` | no | config default | Language |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "id": 1,
  "name": "Sales Mart",
  "type": "standard",
  "merge_type": "union",
  "description": "Main sales data mart",
  "measures": [
    { "id": 10, "name": "Revenue" }
  ],
  "dimensions": [
    { "id": 20, "name": "Date" }
  ],
  "facts": [],
  "source_fact_tables": [
    { "id": 30, "name": "orders" }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Data mart ID |
| `name` | `string \| null` | Data mart name |
| `type` | `string \| null` | Data mart type |
| `merge_type` | `string \| null` | Merge type |
| `description` | `string \| null` | Description |
| `measures` | `array` | Selected measures in this data mart |
| `dimensions` | `array` | Selected dimensions in this data mart |
| `facts` | `array` | Selected facts in this data mart |
| `source_fact_tables` | `array` | Fact tables that feed this data mart |

---

#### `df_get_data_mart_view`

Get physical view metadata for a data mart.

**Input:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `integer` | yes | Project ID |
| `version_id` | `integer` | yes | Version ID |
| `data_mart_id` | `integer` | yes | Data mart ID |

**Output:** object with physical view metadata (structure depends on the data mart configuration).

---

#### `df_generate_sql`

Generate SQL script for a data mart. This is **read-only** -- the SQL is generated but never executed.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `data_mart_id` | `integer` | yes | -- | Data mart ID |
| `limit` | `integer` | no | -- | Row limit for generated SQL |
| `offset` | `integer` | no | -- | Row offset for generated SQL |

**Output:**

```json
{
  "sql": "SELECT * FROM orders LIMIT 100"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `sql` | `string \| null` | Generated SQL query |

---

#### `df_list_connections`

List database connections for a project version.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `language` | `string` | no | config default | Language |
| `db_type` | `string` | no | -- | Filter by database type (e.g. "postgresql", "mssql") |
| `status` | `string` | no | -- | Filter by connection status |
| `page` | `integer` | no | `1` | Page number |
| `page_size` | `integer` | no | `100` | Items per page |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "project_id": 392,
  "version_id": 948,
  "connections": [
    {
      "id": 1,
      "name": "Main DB",
      "db_type": "postgresql",
      "status": "active"
    }
  ],
  "pagination": {
    "total": 2,
    "page": 1,
    "page_size": 100,
    "total_pages": 1
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Connection identifier |
| `name` | `string \| null` | Connection name |
| `db_type` | `string \| null` | Database type (e.g. "postgresql", "mssql", "clickhouse") |
| `status` | `string \| null` | Connection status |

---

#### `df_get_connection`

Get connection details. Optionally include database schema.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `connection_id` | `integer` | yes | -- | Connection ID |
| `language` | `string` | no | config default | Language |
| `include_db_schema` | `boolean` | no | `false` | Include full database schema in response |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "id": 1,
  "name": "Main DB",
  "db_type": "postgresql",
  "status": "active"
}
```

Response may contain additional fields depending on the connection type. When `include_db_schema` is `true`, the response includes the full database schema (tables, columns, types).

---

#### `df_get_connection_schema`

Get database schema snapshot for a connection -- tables, columns, and data types.

**Input:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `integer` | yes | Project ID |
| `version_id` | `integer` | yes | Version ID |
| `connection_id` | `integer` | yes | Connection ID |

**Output:** object with database schema structure (tables, columns, types). Structure depends on the database type.

---

#### `df_list_dimension_groups`

List dimension groups for a project version. Dimension groups are logical collections of related dimensions (e.g. "Customer Attributes", "Date Hierarchy") linked to fact tables.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `language` | `string` | no | config default | Language |
| `page` | `integer` | no | `1` | Page number |
| `page_size` | `integer` | no | `100` | Items per page |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "project_id": 392,
  "version_id": 948,
  "dimension_groups": [
    {
      "id": 1,
      "name": "Date Group",
      "primary_key": "date_id"
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

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Dimension group identifier |
| `name` | `string \| null` | Dimension group name |
| `primary_key` | `string \| null` | Primary key column name |

---

#### `df_get_dimension_group`

Get dimension group details including contained dimensions and related fact tables.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `dimension_group_id` | `integer` | yes | -- | Dimension group ID |
| `language` | `string` | no | config default | Language |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "id": 1,
  "name": "Date Group",
  "primary_key": "date_id",
  "dimensions": [
    { "id": 10, "name": "Year" },
    { "id": 11, "name": "Month" }
  ],
  "related_fact_tables": [
    { "id": 20, "name": "orders" }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Dimension group ID |
| `name` | `string \| null` | Dimension group name |
| `primary_key` | `string \| null` | Primary key column |
| `dimensions` | `array` | Dimensions belonging to this group |
| `related_fact_tables` | `array` | Fact tables linked to this dimension group |

---

#### `df_list_fact_tables`

List fact tables for a project version. Fact tables are the physical tables that store measures, dimensions, and facts.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `language` | `string` | no | config default | Language |
| `page` | `integer` | no | `1` | Page number |
| `page_size` | `integer` | no | `100` | Items per page |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "project_id": 392,
  "version_id": 948,
  "fact_tables": [
    {
      "id": 1,
      "name": "orders"
    }
  ],
  "pagination": {
    "total": 4,
    "page": 1,
    "page_size": 100,
    "total_pages": 1
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Fact table identifier |
| `name` | `string \| null` | Fact table name |

---

#### `df_get_fact_table`

Get fact table details including measures, dimensions, facts, dimension groups, and verification filters.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `fact_table_id` | `integer` | yes | -- | Fact table ID |
| `language` | `string` | no | config default | Language |
| `include_dependencies` | `boolean` | no | `false` | Include dependency information |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "id": 1,
  "name": "orders",
  "measures": [
    { "id": 10, "name": "Revenue" }
  ],
  "dimensions": [
    { "id": 20, "name": "Customer ID" }
  ],
  "facts": [
    { "id": 30, "name": "Order Amount" }
  ],
  "dimension_groups": [
    { "id": 1, "name": "Date Group" }
  ],
  "verification_filters": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Fact table ID |
| `name` | `string \| null` | Fact table name |
| `measures` | `array` | Measures in this fact table |
| `dimensions` | `array` | Dimensions in this fact table |
| `facts` | `array` | Facts in this fact table |
| `dimension_groups` | `array` | Dimension groups linked to this fact table |
| `verification_filters` | `array` | Verification filters configured for this fact table |

---

#### `df_list_relationships`

List relationships for a project version. Relationships define how fact tables connect to dimension groups (star schema links).

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `language` | `string` | no | config default | Language |
| `fact_table_id` | `integer` | no | -- | Filter by fact table |
| `dimension_group_id` | `integer` | no | -- | Filter by dimension group |
| `page` | `integer` | no | `1` | Page number |
| `page_size` | `integer` | no | `100` | Items per page |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "project_id": 392,
  "version_id": 948,
  "relationships": [
    {
      "id": 1,
      "fact_table_id": 1,
      "dimension_group_id": 1
    }
  ],
  "pagination": {
    "total": 8,
    "page": 1,
    "page_size": 100,
    "total_pages": 1
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Relationship identifier |
| `fact_table_id` | `integer \| null` | Linked fact table ID |
| `dimension_group_id` | `integer \| null` | Linked dimension group ID |

---

#### `df_get_relationship`

Get relationship details between a fact table and a dimension group.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `relationship_id` | `integer` | yes | -- | Relationship ID |
| `language` | `string` | no | config default | Language |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "id": 1,
  "fact_table_id": 1,
  "dimension_group_id": 1
}
```

Response may contain additional fields depending on the relationship configuration.

---

#### `df_get_consolidated_rmd`

Get consolidated RMD export via DF API -- the entire data model in one response. Includes project metadata, version info, all measures, dimensions, facts, dimension groups, fact tables, and relationships.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | -- | Project ID |
| `version_id` | `integer` | yes | -- | Version ID |
| `language` | `string` | no | config default | Language |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "project": { "id": 392, "name": "Fashion Retail" },
  "version": { "id": 948, "name": "Global Version" },
  "measures": [ ... ],
  "dimensions": [ ... ],
  "facts": [ ... ],
  "dimension_groups": [ ... ],
  "fact_tables": [ ... ],
  "relationships": [ ... ],
  "exported_at": "2026-05-18T12:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `project` | `object` | Project metadata |
| `version` | `object` | Version metadata |
| `measures` | `array` | All measures |
| `dimensions` | `array` | All dimensions |
| `facts` | `array` | All facts |
| `dimension_groups` | `array` | All dimension groups |
| `fact_tables` | `array` | All fact tables |
| `relationships` | `array` | All relationships |
| `exported_at` | `string \| null` | ISO 8601 export timestamp |

---

## Shared Response Structures

### Pagination Object

Paginated endpoints return a `pagination` object:

```json
{
  "total": 120,
  "page": 1,
  "page_size": 100,
  "total_pages": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total` | `integer` | Total number of items across all pages |
| `page` | `integer` | Current page number |
| `page_size` | `integer` | Items per page |
| `total_pages` | `integer` | Total number of pages |

### Connected Source Object

Measures, dimensions, and facts can reference their physical database source:

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

---

## Error Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "DATAFORGE_API_KEY_INVALID",
    "message": "API error: API_KEY.INVALID_KEY",
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
| `DATAFORGE_UNAUTHORIZED` | 401 | Unauthorized |
| `DATAFORGE_AUTH_FAILED` | 401 | Authentication failed |
| `DATAFORGE_ACCOUNT_LOCKED` | 403 | Account locked |
| `DATAFORGE_IP_BLOCKED` | 403 | IP address blocked |
| `DATAFORGE_LICENSE_INVALID` | 403 | No valid license |
| `DATAFORGE_INVALID_PARAMETER` | 400 | Invalid request parameter (DF API) |
| `DATAFORGE_PAGE_SIZE_EXCEEDED` | 400 | Page size too large (DF API) |
| `DATAFORGE_RESOURCE_NOT_FOUND` | 404 | Project, version, or entity not found |
| `DATAFORGE_SERVER_ERROR` | 5xx | Server-side error (retried automatically) |
| `DATAFORGE_TIMEOUT` | -- | Request timed out (retried automatically) |
| `DATAFORGE_CONNECTION_ERROR` | -- | Network connection error (retried automatically) |

---

## Typical AI Agent Workflow

A typical workflow for an AI agent using this server:

```
1. df_health              -> verify connectivity
2. df_list_projects       -> discover available projects
3. df_list_versions       -> find the global (production) version
4. df_get_rmd             -> fetch all measures, dimensions, and facts at once
   (or df_get_measures / df_get_dimensions / df_get_facts separately)
5. Use the semantic metadata to understand the data model,
   generate queries, or answer business questions
```

For exploring the physical data model:

```
6. df_list_fact_tables       -> see available fact tables
7. df_get_fact_table         -> inspect a fact table's contents
8. df_list_dimension_groups  -> see dimension groups
9. df_list_relationships     -> understand how fact tables connect to dimension groups
10. df_list_data_marts       -> explore data marts
11. df_get_data_mart         -> get data mart details
12. df_generate_sql          -> generate SQL for a data mart
13. df_get_consolidated_rmd  -> full data model export in one call
```

---

## Architecture

```
AI Agent / MCP Client
    |
    v
MCP Adapter (mcp/)           -- thin wrappers, no business logic
    |
    v
SemanticService (application/) -- cache-first orchestration (CORE)
    |
    +--> DataForgeClient (dataforge/) -- HTTP calls to RMD API + DF API with retry
    +--> Normalizer (semantic/)       -- raw API -> canonical models
    +--> FileCacheStore (cache/)      -- TTL + last-known-good fallback
```

`SemanticService` is the single entry point. MCP tools only delegate to it.

---

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

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAFORGE_BASE_URL` | `https://api.prod-df.businessqlik.com` | DataForge API base URL |
| `DATAFORGE_API_KEY` | -- | API key (required) |
| `DEFAULT_LANGUAGE` | `ru` | Default language for measures/dimensions/facts |
| `CACHE_DIR` | `./cache` | Cache directory path |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL in seconds |
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` or `sse` |
| `HOST` | `0.0.0.0` | Host for SSE mode |
| `PORT` | `8080` | Port for SSE mode |
| `LOG_LEVEL` | `INFO` | Log level |
