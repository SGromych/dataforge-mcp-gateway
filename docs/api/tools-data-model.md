# Data Model Tools Reference

Read-only tools for data marts, connections, dimension groups, fact tables and
relationships, plus the consolidated export.

> For tools that **modify** DataForge, see the [Write Tools Reference](tools-write.md).
> Shared structures are documented in [Shared Schemas & Errors](schemas.md).

All of these are scoped to one project version and take `project_id`, `version_id`,
optional `language` and `use_cache` unless stated otherwise.

---

## `df_list_data_marts`

| Parameter | Type | Description |
|---|---|---|
| `mart_type` | string | `with_grouping`, `without_grouping`, `with_grouping_and_pivoting` |
| `merge_type` | string | `union`, `join` |
| `search` | string | Case-insensitive substring of name or description |
| `page`, `page_size` | integer | `page_size` **must be 1–100**; above that the API answers 400 |

```json
{
  "project_id": 392,
  "version_id": 948,
  "data_marts": [
    {
      "id": "9666",
      "name": "DF Fashion retail sales only",
      "description": "Sales without plans",
      "owner": "Алёна Зубакова",
      "created_at": "2026-05-21T13:23:10.621Z",
      "type": "С группировкой",
      "merge_type": null,
      "source_fact_table_count": 1,
      "has_physical_view": false
    }
  ],
  "pagination": { "total": 2, "page": 1, "page_size": 100, "total_pages": 1 }
}
```

| Field | Notes |
|---|---|
| `id` | A **string**, not a number |
| `description` | Always present; `null` when unset (an empty string in storage also reads as `null`) |
| `type` | Localized label |
| `merge_type` | Raw slug `union` / `join`, **never translated** — it is a filter value. `null` for marts that do not merge several fact tables |
| `has_physical_view` | Whether a physical view is materialized for this mart |

Data marts are read-only in the API: v2 offers no create, update or delete for them.

---

## `df_get_data_mart`

Full configuration of one mart.

| Parameter | Type |
|---|---|
| `data_mart_id` | integer, **required** |

```json
{
  "id": "9667",
  "name": "DF Fashion retail sales and plans",
  "owner": "Алёна Зубакова",
  "created_at": "2026-05-21T13:23:10.621Z",
  "type": "С группировкой",
  "merge_type": "join",
  "source_fact_tables": [{ "id": "6784", "name": "Sales and refunds" }],
  "selected_measures": [
    {
      "instance_id": "155341",
      "measure_id": "33540",
      "measure_name": "Items Gross, count",
      "formula": "COUNTDISTINCT({[operation_id]=1} [Receipt position])",
      "data_type": "Number",
      "display_name": "Items Gross, count",
      "aggregation_configuration": { "type": "default", "group_by_fields": [] },
      "source_fact_table_id": "6784"
    }
  ],
  "selected_facts": [ ... ],
  "selected_dimensions": [ ... ],
  "physical_view": { "exists": false, "...": null }
}
```

| Field | Notes |
|---|---|
| `selected_measures[].instance_id` vs `measure_id` | The **same measure can appear several times** in one mart with different aggregation settings. `instance_id` identifies the occurrence, `measure_id` the RMD measure |
| `aggregation_configuration.type` | `default`, `none`, `custom` or `global` |
| `…include_in_result` | `false` means the element only participates in filtering and does not reach the result |
| `…filter_condition` | Filter expression with element references rendered as names; `null` when unset |
| `selected_dimensions[].source_dimension_group_id` / `_name` | The dimension group resolved from the data model, even when the mart does not name it explicitly |
| `selected_measure_attributes` | Present **only** for pivot marts (`with_grouping_and_pivoting`) |
| `physical_view` | The [physical view object](schemas.md#physical-view-object) **without** `connection` — only `df_get_data_mart_view` returns that |

---

## `df_get_data_mart_view`

Metadata of the object DataForge materialized for the mart. No connection to the target
database is made; this is what the platform knows.

Returns the full [physical view object](schemas.md#physical-view-object), including
`status`, `is_stale`, `last_refresh_at` and `connection`. When nothing is materialized,
`exists` is `false` and every other field is `null`.

`is_stale: true` means the mart's configuration changed after deployment and the object no
longer matches it — it needs to be rebuilt.

**Known limitation — the response does not locate the table.** `database` carries the
engine slug rather than a database name, `schema` is frequently `null`, and `connection`
is the mart's *source* connection. Where marts are materialized into a separate store,
none of those three is the address of the table, and there is no field that is. This is an
API gap, not a gateway one: `target_connection_id` / `target_database` / `target_schema`
have been requested from the DataForge API team. Until then, a client that wants to read a
mart's table directly has to be told where marts live.

---

## `df_generate_sql`

Generate the mart's SQL query. **Nothing is executed, no data is read and nothing is
stored.**

| Parameter | Type | Description |
|---|---|---|
| `data_mart_id` | integer | **required** |
| `limit` | integer ≥ 1 | Adds a row limit in the target dialect's syntax |
| `offset` | integer ≥ 0 | Only applies together with `limit`; ignored on its own |

Returns the [SQL generation response](schemas.md#sql-generation-response). **A generation
failure is HTTP 200** with a non-empty `validation_errors` — check `succeeded`:

```python
result = await service.generate_sql(project_id=392, version_id=948, data_mart_id=9666)
if result["succeeded"]:
    print(result["sql_script"])
else:
    print(result["validation_errors"][0]["message"])
```

For MS SQL Server, an `ORDER BY (SELECT NULL)` is added when the query has none —
otherwise `OFFSET … FETCH NEXT` would be syntactically invalid.

This response is never cached: the endpoint regenerates on every call by design.

---

## `df_list_connections`

Database connections of the version.

| Parameter | Type | Description |
|---|---|---|
| `db_type` | string | `postgresql`, `clickhouse`, `sqlserver` |
| `status` | string | `active`, `inactive`, `never_verified`, `failed` |
| `page_size` | integer | 1–100; above that the API answers 400 |

Two properties matter for integrations:

- **Credentials are never returned.** Passwords, certificates, private keys and connection
  strings are absent from every response — only the network coordinates and the database
  username needed to build SQL.
- Connections to engines the public API does not support (MySQL, for example) are excluded
  entirely: they appear neither in the list nor in `total`, and addressing one by id
  answers 404.

`never_verified` takes precedence over other statuses: without a successful schema refresh,
the platform cannot assert anything about the connection.

---

## `df_get_connection`

| Parameter | Type | Description |
|---|---|---|
| `connection_id` | integer | **required** |
| `include_db_schema` | boolean | `true` replaces the short `db_tables` array with the full `db_schema` object |

```json
{
  "id": "3821",
  "name": "Production PostgreSQL",
  "db_type": "postgresql",
  "host": "db.production.company.com",
  "port": 5432,
  "database": "analytics_db",
  "schema": "public",
  "username": "analytics_user",
  "status": "active",
  "last_updated_at": "2026-05-21T13:23:07.188Z",
  "db_tables": [{ "name": "fact_sales" }]
}
```

Exactly one of `db_tables` or `db_schema` is present. If the schema cache is empty the
result is an empty list, not an error.

The two variants are cached separately, so asking for the schema after a plain read really
does fetch it.

---

## `df_get_connection_schema`

The connection's cached table/column schema. **This is a snapshot** taken when the
connection was configured or last refreshed (`last_updated_at`), not a live query against
the database.

```json
{
  "id": "3821",
  "name": "Production PostgreSQL",
  "db_type": "postgresql",
  "last_updated_at": "2026-05-21T13:23:07.188Z",
  "schema": {
    "connection": "Production PostgreSQL",
    "tables": [
      {
        "table_name": "fact_sales",
        "schema": "public",
        "columns": [{ "column_name": "amount", "data_type": "numeric" }]
      }
    ]
  }
}
```

This is the list the API validates write-time source objects against, so use it to pick
valid `table` and `column` values before calling a write tool. `tables[].schema` is `null`
for ClickHouse, which has no schemas.

---

## `df_list_dimension_groups` / `df_get_dimension_group`

Shared reference hierarchies.

```json
{
  "id": "1204",
  "name": "Calendar",
  "description": "Date hierarchy",
  "primary_key": { "connection": "...", "db": "...", "table": "...", "column": "..." },
  "dimensions": [
    { "id": "33929", "name": "Year", "level": 1, "display_data_type": "Number", "physical_column": "year" }
  ],
  "related_fact_tables": [
    { "fact_table_id": "6784", "fact_table_name": "Sales and refunds", "foreign_key_column": "date_id" }
  ]
}
```

| Field | Notes |
|---|---|
| `primary_key` | A [source object](schemas.md#source-object), not a string. `null` if the group has no key yet (a group gets one from its first relationship) |
| `dimensions[]` | Only in the detail response. `level` is the hierarchy position; levels are unique within the group |
| `related_fact_tables` | Ids in the listing, objects in the detail response |

Neither response carries `created_at` / `updated_at` — v2 dropped them.

---

## `df_list_fact_tables` / `df_get_fact_table`

| Parameter | Type | Description |
|---|---|---|
| `fact_table_id` | integer | **required** for the detail tool |
| `include_dependencies` | boolean | Fill `measures[].dependencies` with the recursive formula dependency tree |

The listing carries counts (`measures_count`, `dimensions_count`, `facts_count`,
`verification_filters_count`, `related_dimension_groups_count`). The detail response
carries the elements themselves:

| Field | Notes |
|---|---|
| `measures[].measure_type` | **Raw slug** (`base` / `calculated`) — unlike the RMD listings, which return localized labels. The same holds for `dimension_type` and `fact_type` |
| `dimensions[].is_from_dimension_group` | `true` when inherited from a linked group rather than defined on the table |
| `dimensions[].dimension_group_id` | Which group it was inherited from |
| `…physical_column` | The source table column bound to the element |
| `dimension_groups[].primary_key` / `foreign_key` | The join's source objects |
| `verification_filters[].is_valid` | `false` when the filter expression does not resolve |
| `measures[].dependencies` | Only with `include_dependencies=true`; each node has `id`, `name`, `type`, `formula` and its own `dependencies` |

---

## `df_list_relationships` / `df_get_relationship`

Star-schema joins between fact tables and dimension groups.

| Parameter | Type | Description |
|---|---|---|
| `fact_table_id` | integer | Filter by source fact table |
| `dimension_group_id` | integer | Filter by target dimension group |
| `relationship_id` | integer | **required** for the detail tool |

```json
{
  "id": "501",
  "source_fact_table": { "id": "6784", "name": "Sales and refunds" },
  "target_dimension_group": { "id": "1204", "name": "Calendar" },
  "foreign_key": { "connection": "...", "table": "fact_order_line", "column": "date_id" },
  "primary_key": { "connection": "...", "table": "dim_customer", "column": "customer_id" },
  "relationship_type": "many_to_one"
}
```

`relationship_type` is the raw slug `many_to_one` — the only cardinality the model
supports. (v1 returned a localized label here.) Both keys always name the same connection:
a join cannot span two databases.

---

## `df_get_consolidated_rmd`

The whole version in one payload, without pagination: project, version, all RMD rows and
the entire data model.

| Parameter | Type | Default |
|---|---|---|
| `include_sql` | boolean | `false` |

```json
{
  "project": { "id": "12", "name": "Sales Analytics" },
  "version": { "id": "33", "name": "Q4 2025", "is_global": true },
  "measures": [ ... ],
  "dimensions": [ ... ],
  "facts": [ ... ],
  "dimension_groups": [ ... ],
  "fact_tables": [ ... ],
  "relationships": [ ... ],
  "exported_at": "2026-05-29T08:00:00.000Z"
}
```

Every RMD row starts with its `id`, and every source object carries `connection`. The
`dimension_groups`, `fact_tables` and `relationships` entries are the same objects the
listing tools return.

This tool and [`df_get_rmd`](tools-semantic.md#df_get_rmd) read the same endpoint and
share one cache entry — calling both costs one HTTP request.

---

## `df_get_project_access`

Read-only listing of a project's owner and every user with explicit access. Takes
`project_id` and optional `language` — there is no version and no pagination.

```json
{
  "project_id": 392,
  "access": [
    {
      "id": 7,
      "first_name": "Pavel",
      "last_name": "Shalavin",
      "email": "pavel@example.com",
      "isOwner": true,
      "globalRole": "Администратор",
      "projectRole": "Разработчик"
    }
  ]
}
```

Role labels are localized. The camelCase keys are the API's own wire format here.
To change access, see the [Write Tools Reference](tools-write.md#project-access).

---

## `df_list_git_connections` / `df_get_git_connection`

The company's registry of saved Git connections, used by version export and import.
These are company-scoped (no project, no version) and require a **company administrator**
API key; a lower role answers `403`.

Credentials are never returned — only `platform`, `repository_url`, `branch`, `path`,
`status`, `shared`, `default` and audit fields.
