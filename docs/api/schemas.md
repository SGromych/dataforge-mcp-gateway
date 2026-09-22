# Shared Schemas & Error Codes

Common structures used across all MCP tools.

> ⚠️ This server exposes tools that **modify and delete** DataForge data.
> See the [Write Tools Reference](tools-write.md).

---

## Entity IDs

Every measure, dimension and fact carries a stable `id` (a **string**) as its first field.
It is unique within the project version, present regardless of `include_sql` or `language`,
and it is exactly what the write tools take as the target id. That makes a read result
directly reusable:

```python
measures = await service.get_measures(project_id=392, version_id=948)
measure_id = int(measures["measures"][0]["id"])
await service.write_measure(project_id=392, version_id=948, mode="update",
                            measure_id=measure_id, comment="reviewed")
```

`row_number` is a separate field, meant for display ordering only.

Ids in URL paths are positive integers up to `2147483647`. A numeric value outside that
range cannot match any record and answers `404`, exactly like a non-existent one.

---

## Pagination Object

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
| `page` | `integer` | Current page number (1-based) |
| `page_size` | `integer` | Items per page |
| `total_pages` | `integer` | Total number of pages |
| `fetched` | `integer` | Only on RMD listings: how many rows this server actually collected |

The API names these `pageSize` and `totalPages` on the wire; this server normalizes them
to snake_case. `pageSize` is the **only** camelCase query parameter in the whole v2
surface — every filter (`merge_type`, `db_type`, `include_sql`, `include_dependencies`,
`include_db_schema`, `fact_table_id`, `dimension_group_id`) is snake_case.

### Page size limits

| Endpoint group | Behaviour above 100 |
|---|---|
| Data marts, connections, Git connections | `400 DF_API.PAGE_SIZE_EXCEEDED` (rejected locally before the request) |
| Projects, versions, RMD content, dimension groups, fact tables, relationships | silently capped at 100 |

`df_get_measures`, `df_get_dimensions` and `df_get_facts` page through automatically and
return the complete set, so a version with 400 measures comes back whole.

---

## Source Object

Every field that points at a physical location in a connected database uses one shape.
Used by `connected_source` (dimensions, facts), `primary_key` (dimension groups,
relationships) and `foreign_key` (fact table details, relationships).

```json
{
  "connection": "Production PostgreSQL",
  "db": "analytics_db",
  "schema": "public",
  "table": "dim_customer",
  "column": "customer_name"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `connection` | `string \| null` | **The only field that identifies the source unambiguously.** One version may hold several connections to the same database. `null` if the connection was deleted — then `db` is `null` too. |
| `db` | `string \| null` | Database name of that connection |
| `schema` | `string \| null` | Schema. PostgreSQL only — `""` for MS SQL Server (the schema lives inside `table`, as `dbo.orders`) and for ClickHouse (no schemas) |
| `table` | `string \| null` | Table name |
| `column` | `string \| null` | Column name; `null`/`""` when the reference is to the whole table |

On write, `db` and `table` are mandatory; `schema` and `column` accept an empty string,
`null` or absence — all three mean "not supplied". An object read from the API can be sent
straight back without edits.

---

## SQL Code Object

Returned per measure when `include_sql=true` is passed to `df_get_measures`,
`df_get_rmd` or `df_get_consolidated_rmd`.

```json
{
  "generated_at": "2026-05-29T08:00:00.000Z",
  "sql_scripts": [
    {
      "fact_table_id": "11",
      "fact_table_name": "fact_sales",
      "sql": "SELECT SUM(amount) FROM fact_sales WHERE ..."
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | `string` | ISO 8601 timestamp of generation |
| `sql_scripts` | `array` | One entry per fact table the measure is bound to; a measure with no bindings yields one entry with `null` ids |
| `sql_scripts[].sql` | `string` | Generated SQL. It is built but never executed. |

If SQL could not be built for a measure, `sql_code` is simply absent for that row — the
request itself still succeeds.

---

## SQL Generation Response

Returned by `df_generate_sql`. **The endpoint answers HTTP 200 even when generation
fails** — that is exactly what distinguishes "this data mart cannot produce SQL right now"
from "this data mart does not exist" (404).

```json
{
  "sql_script": "SELECT ... FROM ... GROUP BY ... LIMIT 100 OFFSET 0",
  "target_db_type": "clickhouse",
  "validation_errors": [],
  "succeeded": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `sql_script` | `string` | The generated `SELECT`; empty string on failure |
| `target_db_type` | `string \| null` | `postgres`, `clickhouse` or `sqlserver`; `null` on failure |
| `validation_errors` | `array` | `{code, message}`; empty on success. `code` is always `SQL_GENERATION_FAILED` |
| `succeeded` | `boolean` | Added by this server: `validation_errors` is empty |

`offset` only applies together with `limit`. This response is never cached — the endpoint
regenerates on every call by design.

---

## Physical View Object

Returned by `df_get_data_mart_view`, and embedded (without `connection`) in
`df_get_data_mart`.

```json
{
  "exists": true,
  "type": "Materialized view",
  "database": "clickhouse",
  "schema": "dataforge_test",
  "name": "materialized_view_6839_datamart_...",
  "created_at": "2026-03-17T12:44:45.000Z",
  "status": "active",
  "is_stale": false,
  "last_refresh_at": "2026-08-30T03:00:12.000Z",
  "connection": { "id": "3160", "name": "Click", "db_type": "clickhouse" }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `exists` | `boolean` | Whether the object is materialized. If `false`, every other field is `null` |
| `type` | `string \| null` | Localized label. Raw slugs: `regular_view`, `materialized_view`, `table` |
| `database` | `string \| null` | Raw engine slug: `postgresql`, `clickhouse`, `sqlserver` |
| `status` | `string \| null` | Lifecycle slug: `deploying`, `active`, `updating`, `deleting`, `error` |
| `is_stale` | `boolean \| null` | `true` when the data mart changed after deployment and the object no longer matches it |
| `last_refresh_at` | `string \| null` | Last successful data refresh |
| `connection` | `object \| null` | **Only on `df_get_data_mart_view`.** Never contains credentials |

No connection to the target database is made — this is what the platform knows.

---

## Filter Value Catalogues

Values outside these sets are rejected by the API, so the tools publish them as `enum`.

| Filter | Allowed values |
|---|---|
| Data mart `mart_type` | `with_grouping`, `without_grouping`, `with_grouping_and_pivoting` |
| Data mart `merge_type` | `union`, `join` (`null` when the mart uses one fact table) |
| Connection `db_type` | `postgresql`, `clickhouse`, `sqlserver` |
| Connection `status` | `active`, `inactive`, `never_verified`, `failed` |
| `relationship_type` | `many_to_one` (the only cardinality the model supports) |
| `aggregation_configuration.type` | `default`, `none`, `custom`, `global` |
| Project `access_level` | `developer`, `analyst`, `viewer` |
| Git `platform` | `github`, `gitlab`, `bitbucket`, `azure-devops`, `generic` |
| Import `conflict_strategy` | `smart_merge`, `overwrite`, `skip`, `manual` |

Slugs are never localized — they are filter values. Localization (`language=ru\|en`)
affects only descriptive labels such as `type` or `display_data_type`.

---

## Error Format

The API v2 envelope carries two machine-readable fields (`code` and `details[]`) on top of
the base four. This server surfaces both, because they are what lets an agent repair a
rejected request instead of guessing.

```json
{
  "error": {
    "code": "DATAFORGE_VALIDATION_FAILED",
    "message": "Некорректное значение фильтра merge_type",
    "api_code": "invalid_merge_type",
    "original_message": "DF_API.INVALID_MERGE_TYPE",
    "http_status": 400,
    "fields": [{ "field": "merge_type", "code": "invalid_value" }],
    "retryable": false,
    "hint": "Check fields[]: unknown_field means remove it, ...",
    "details": { "http_status": 400, "path": "/df-api/v2/..." }
  }
}
```

| Field | Description |
|---|---|
| `code` | This server's normalized code (the table below) |
| `message` | Localized, human-readable message from the API |
| `api_code` | The API's own machine-readable code, e.g. `data_mart_not_found` |
| `original_message` | The stable `DF_API.*` key |
| `fields` | Which fields caused it: `field` (dotted path — `measures.1.measure_type` for bulk rows) and `code` ∈ `missing_field`, `unknown_field`, `invalid_value` |
| `retryable` | Whether repeating the request could succeed |
| `retry_after_seconds` | On 429, taken from `Retry-After` / `X-RateLimit-Reset` |
| `hint` | Present where the agent can fix the request itself |

Keys outside the catalogue degrade by HTTP status, exactly as the API does:
400 → `invalid_parameter`, 401 → `invalid_api_key`, 403 → `write_access_denied`,
404 → `resource_not_found`, 409 → `constraint_violation`, 422 → `unprocessable_entity`,
429 → `rate_limit_exceeded`.

### Error codes — reads and transport

| Code | HTTP | Description |
|------|------|-------------|
| `DATAFORGE_API_KEY_MISSING` | 401 | `X-Api-Key` header not provided |
| `DATAFORGE_API_KEY_INVALID` | 401 | Key matched no stored key |
| `DATAFORGE_UNAUTHORIZED` | 401 | Unauthorized |
| `DATAFORGE_AUTH_FAILED` | 401 | Authentication failed |
| `DATAFORGE_ACCOUNT_LOCKED` | 403 | The key owner is not `ENABLED` |
| `DATAFORGE_IP_BLOCKED` | 403 | Client IP blocked or outside the allowlist |
| `DATAFORGE_LICENSE_INVALID` | 403 | The company has no valid licence |
| `DATAFORGE_INVALID_PARAMETER` | 400 | A path or query parameter failed validation |
| `DATAFORGE_PAGE_SIZE_EXCEEDED` | 400 | `page_size` above 100 |
| `DATAFORGE_INVALID_TYPE` / `_MERGE_TYPE` / `_DB_TYPE` / `_STATUS` | 400 | A filter value outside its catalogue |
| `DATAFORGE_INVALID_FORMAT` | 400 | Unsupported `format` |
| `DATAFORGE_PROJECT_NOT_FOUND` | 404 | Project does not exist **or is not accessible** — existence is never disclosed |
| `DATAFORGE_VERSION_NOT_FOUND` | 404 | Version does not exist in the project |
| `DATAFORGE_RESOURCE_NOT_FOUND` | 404 | Data mart, connection, dimension group, fact table or relationship not found |
| `DATAFORGE_RATE_LIMIT_EXCEEDED` | 429 | **100 requests / 60 s per API key** |
| `DATAFORGE_SERVER_ERROR` | 5xx | Server-side error (retried) |
| `DATAFORGE_INTERNAL_ERROR` | 500 | Unexpected server failure; no internal details are returned |
| `DATAFORGE_TIMEOUT` | — | Request timed out |
| `DATAFORGE_CONNECTION_ERROR` | — | Network failure |

Write-specific codes are listed in the [Write Tools Reference](tools-write.md).

### Retry behaviour

| Situation | Retry? | Notes |
|---|---|---|
| 400, 401, 403, 404 | No | Fix the request or the key |
| 429 | No | Rate limited; `retry_after_seconds` says when |
| 409 `idempotency_in_progress` | Yes | Automatic, up to 2 extra attempts |
| 5xx, timeout, connection error — **read or idempotent write** | Yes | Up to 3 attempts, exponential backoff |
| 5xx, timeout — **POST without an `Idempotency-Key`** | **No** | A retry would create a duplicate. The error carries `possibly_applied: true`; verify state with a read tool before resending |

Since every write generated through this server carries an `Idempotency-Key`
automatically, the last row applies only to hand-rolled client calls.
