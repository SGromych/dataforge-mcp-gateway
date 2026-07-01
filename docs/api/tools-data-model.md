# Data Model Tools Reference

Tools for exploring the physical data model: data marts, connections, dimension groups, fact tables, relationships, and consolidated RMD export.

All tools require `project_id` and `version_id`.

---

## `df_list_data_marts`

List data marts for a project version.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default | Language |
| `type` | `string` | no | — | Filter by data mart type |
| `merge_type` | `string` | no | — | Filter by merge type |
| `search` | `string` | no | — | Search by name |
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
  "pagination": { "total": 3, "page": 1, "page_size": 100, "total_pages": 1 }
}
```

---

## `df_get_data_mart`

Get data mart details including selected measures, dimensions, facts, and source fact tables.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `data_mart_id` | `integer` | yes | — | Data mart ID |
| `language` | `string` | no | config default | Language |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "id": 1,
  "name": "Sales Mart",
  "type": "standard",
  "measures": [{ "id": 10, "name": "Revenue" }],
  "dimensions": [{ "id": 20, "name": "Date" }],
  "facts": [],
  "source_fact_tables": [{ "id": 30, "name": "orders" }]
}
```

---

## `df_get_data_mart_view`

Get physical view metadata for a data mart.

**Input:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `integer` | yes | Project ID |
| `version_id` | `integer` | yes | Version ID |
| `data_mart_id` | `integer` | yes | Data mart ID |

**Output:** object with physical view metadata (structure depends on configuration).

---

## `df_generate_sql`

Generate SQL script for a data mart. **Read-only** — the SQL is generated but never executed.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `data_mart_id` | `integer` | yes | — | Data mart ID |
| `limit` | `integer` | no | — | Row limit for generated SQL |
| `offset` | `integer` | no | — | Row offset for generated SQL |

**Output:**

```json
{
  "sql": "SELECT * FROM orders LIMIT 100"
}
```

---

## `df_list_connections`

List database connections for a project version.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default | Language |
| `db_type` | `string` | no | — | Filter by database type |
| `status` | `string` | no | — | Filter by connection status |
| `page` | `integer` | no | `1` | Page number |
| `page_size` | `integer` | no | `100` | Items per page |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "project_id": 392,
  "version_id": 948,
  "connections": [
    { "id": 1, "name": "Main DB", "db_type": "postgresql", "status": "active" }
  ],
  "pagination": { "total": 2, "page": 1, "page_size": 100, "total_pages": 1 }
}
```

---

## `df_get_connection`

Get connection details. Optionally include database schema.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `connection_id` | `integer` | yes | — | Connection ID |
| `language` | `string` | no | config default | Language |
| `include_db_schema` | `boolean` | no | `false` | Include full database schema |
| `use_cache` | `boolean` | no | `true` | Use cached data |

---

## `df_get_connection_schema`

Get database schema snapshot for a connection.

**Input:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `integer` | yes | Project ID |
| `version_id` | `integer` | yes | Version ID |
| `connection_id` | `integer` | yes | Connection ID |

---

## `df_list_dimension_groups`

List dimension groups for a project version.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default | Language |
| `page` | `integer` | no | `1` | Page number |
| `page_size` | `integer` | no | `100` | Items per page |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "dimension_groups": [
    {
      "id": 1,
      "name": "Date Group",
      "description": "Date hierarchy",
      "primary_key": "date_id",
      "related_fact_tables": ["orders"],
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

## `df_get_dimension_group`

Get dimension group details including dimensions and related fact tables.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `dimension_group_id` | `integer` | yes | — | Dimension group ID |
| `language` | `string` | no | config default | Language |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "id": 1,
  "name": "Date Group",
  "description": "Date hierarchy",
  "primary_key": "date_id",
  "dimensions": [{ "id": 10, "name": "Year", "level": 1 }],
  "related_fact_tables": [{ "fact_table_name": "orders", "foreign_key_column": "date_id" }],
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-02-01T00:00:00Z"
}
```

---

## `df_list_fact_tables`

List fact tables for a project version. Returns enriched metadata including entity counts.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default | Language |
| `page` | `integer` | no | `1` | Page number |
| `page_size` | `integer` | no | `100` | Items per page |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "fact_tables": [
    {
      "id": 1,
      "name": "orders",
      "description": "Main orders table",
      "owner": "analytics_team",
      "created_at": "2026-01-01T00:00:00Z",
      "measures_count": 15,
      "dimensions_count": 8,
      "facts_count": 5,
      "verification_filters_count": 2,
      "related_dimension_groups_count": 3
    }
  ]
}
```

---

## `df_get_fact_table`

Get fact table details. Set `include_dependencies=true` to get measure dependency trees.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `fact_table_id` | `integer` | yes | — | Fact table ID |
| `language` | `string` | no | config default | Language |
| `include_dependencies` | `boolean` | no | `false` | Include measure dependency trees |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "id": 1,
  "name": "orders",
  "description": "Main orders table",
  "owner": "analytics_team",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-06-01T00:00:00Z",
  "measures": [{ "id": 10, "name": "Revenue" }],
  "dimensions": [{ "id": 20, "name": "Customer ID" }],
  "facts": [{ "id": 30, "name": "Order Amount" }],
  "dimension_groups": [{ "id": 1, "name": "Date Group" }],
  "verification_filters": []
}
```

---

## `df_list_relationships`

List relationships for a project version. Supports filtering by fact table and dimension group.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default | Language |
| `fact_table_id` | `integer` | no | — | Filter by fact table |
| `dimension_group_id` | `integer` | no | — | Filter by dimension group |
| `page` | `integer` | no | `1` | Page number |
| `page_size` | `integer` | no | `100` | Items per page |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:**

```json
{
  "relationships": [
    {
      "id": 1,
      "source_fact_table": { "id": 1, "name": "orders" },
      "target_dimension_group": { "id": 1, "name": "Date Group" },
      "foreign_key": { "db": "main", "schema": "public", "table": "orders", "column": "date_id" },
      "primary_key": { "db": "main", "schema": "public", "table": "dates", "column": "id" },
      "relationship_type": "many_to_one",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

## `df_get_relationship`

Get relationship details between a fact table and a dimension group.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `relationship_id` | `integer` | yes | — | Relationship ID |
| `language` | `string` | no | config default | Language |
| `use_cache` | `boolean` | no | `true` | Use cached data |

**Output:** same fields as list item plus `updated_at`.

---

## `df_get_consolidated_rmd`

Get the entire data model in one response. Set `include_sql=true` to include SQL code for measures.

**Input:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `integer` | yes | — | Project ID |
| `version_id` | `integer` | yes | — | Version ID |
| `language` | `string` | no | config default | Language |
| `include_sql` | `boolean` | no | `false` | Include SQL code for measures |
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
