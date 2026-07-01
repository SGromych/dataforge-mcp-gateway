# Semantic Tools Reference

Tools for accessing the semantic layer: projects, versions, measures, dimensions, facts, and RMD.

---

## `df_health`

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

## `df_list_projects`

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

## `df_list_versions`

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
  "pagination": { "total": 5, "page": 1, "page_size": 100, "total_pages": 1 }
}
```

**Version fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `integer` | Unique version identifier |
| `name` | `string` | Version name |
| `is_global` | `boolean` | Whether this is the global (production) version |

---

## `df_get_measures`

Get all measures (business metrics) for a project version. Set `include_sql=true` to get generated SQL code for each measure.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default (`ru`) | Language for localized names |
| `include_sql` | `boolean` | no | `false` | Include generated SQL code for each measure |
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
      "sql_code": {
        "generated_at": "2026-06-01T10:00:00Z",
        "sql_scripts": [
          {
            "fact_table_id": "1",
            "fact_table_name": "orders",
            "sql": "SELECT SUM(amount) FROM orders"
          }
        ]
      },
      "status": "Active",
      "required": true,
      "raw": {}
    }
  ]
}
```

> **Note:** `sql_code` is only present when `include_sql=true`. Otherwise it's `null`.

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
| `connected_source` | `object \| null` | Database source mapping (see [Shared Schemas](schemas.md#connected-source-object)) |
| `sql_code` | `object \| null` | Generated SQL code (see [Shared Schemas](schemas.md#sql-code-object)) |
| `original_source_type` | `string \| null` | Source type (e.g. "Database") |
| `original_source` | `string \| null` | Original data source name |
| `original_object` | `string \| null` | Original object (table/view) name |
| `report_for_verification` | `string \| null` | Report used to verify this measure |
| `comment` | `string \| null` | Additional notes |
| `display_data_type` | `string \| null` | Display format type |
| `status` | `string \| null` | Status (e.g. "Active", "Draft") |
| `relevance` | `string \| null` | Relevance level |
| `required` | `boolean \| null` | Whether the measure is required |
| `visibility` | `string \| null` | Visibility level |
| `responsible_for_data` | `string \| null` | Team/person responsible for data quality |
| `variation` | `string \| null` | Measure variation/variant |
| `raw` | `object` | Original unmodified API response (empty by default) |

---

## `df_get_dimensions`

Get all dimensions (attributes for slicing/filtering data) for a project version.

**Input:** same as `df_get_measures` (without `include_sql`).

**Dimension fields:**

| Field | Type | Description |
|-------|------|-------------|
| `row_number` | `string \| integer \| null` | Row number from RMD spreadsheet |
| `group` | `string \| null` | Business group |
| `block` | `string \| null` | Block within a group |
| `name` | `string \| null` | Dimension name (localized) |
| `description` | `string \| null` | Human-readable description |
| `dimension_group` | `string \| null` | Logical grouping |
| `data_type` | `string \| null` | Data type |
| `connected_source` | `object \| null` | Database source mapping |
| `dimension_type` | `string \| null` | Dimension type classification |
| `formula` | `string \| null` | Calculation formula |
| `value_options` | `string \| array \| null` | Allowed values |
| `status` | `string \| null` | Status |
| `raw` | `object` | Original API response |

---

## `df_get_facts`

Get all facts for a project version.

**Input:** same as `df_get_measures` (without `include_sql`).

**Fact fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string \| null` | Fact name (localized) |
| `description` | `string \| null` | Description |
| `source_data_type` | `string \| null` | Data type in source system |
| `fact_type` | `string \| null` | Fact type (e.g. "Additive") |
| `formula` | `string \| null` | Calculation formula |
| `connected_source` | `object \| null` | Database source mapping |
| `status` | `string \| null` | Status |
| `raw` | `object` | Original API response |

---

## `df_get_rmd`

Get full RMD — all measures, dimensions, and facts in a single call.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default | Language |
| `use_cache` | `boolean` | no | `true` | Use cached data |
| `include_raw` | `boolean` | no | `false` | Include raw API response in each entity |

**Output:**

```json
{
  "project": { "id": 392, "name": "", "description": null },
  "version": { "id": 948, "name": "", "is_global": false },
  "measures": [ ... ],
  "dimensions": [ ... ],
  "facts": [ ... ],
  "stats": {
    "measure_count": 120,
    "dimension_count": 75,
    "fact_count": 30
  }
}
```

---

## `df_refresh_cache`

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
  "cache_key": "rmd:392:948:ru:False",
  "fetched_at": "2026-03-29T12:00:00+00:00"
}
```
