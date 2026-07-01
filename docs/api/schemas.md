# Shared Schemas & Error Codes

Common response structures used across all MCP tools.

---

## Pagination Object

All paginated endpoints return a `pagination` object:

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

---

## Connected Source Object

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

## SQL Code Object

Returned for measures when `include_sql=true` is passed to `df_get_measures` or `df_get_consolidated_rmd`.

```json
{
  "generated_at": "2026-06-01T10:00:00Z",
  "sql_scripts": [
    {
      "fact_table_id": "1",
      "fact_table_name": "orders",
      "sql": "SELECT SUM(amount) FROM orders"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | `string` | ISO 8601 timestamp of SQL generation |
| `sql_scripts` | `array` | List of SQL scripts per fact table |
| `sql_scripts[].fact_table_id` | `string \| null` | Fact table ID |
| `sql_scripts[].fact_table_name` | `string \| null` | Fact table name |
| `sql_scripts[].sql` | `string` | Generated SQL query |

---

## Error Format

All errors follow a consistent JSON format:

```json
{
  "error": {
    "code": "DATAFORGE_API_KEY_INVALID",
    "message": "API error: API_KEY.INVALID_KEY",
    "details": { "http_status": 401 }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `DATAFORGE_API_KEY_MISSING` | 401 | `X-Api-Key` header not provided |
| `DATAFORGE_API_KEY_INVALID` | 401 | Invalid API key |
| `DATAFORGE_UNAUTHORIZED` | 401 | Unauthorized |
| `DATAFORGE_AUTH_FAILED` | 401 | Authentication failed |
| `DATAFORGE_ACCOUNT_LOCKED` | 403 | Account locked |
| `DATAFORGE_IP_BLOCKED` | 403 | IP address blocked |
| `DATAFORGE_LICENSE_INVALID` | 403 | No valid license |
| `DATAFORGE_INVALID_PARAMETER` | 400 | Invalid request parameter |
| `DATAFORGE_PAGE_SIZE_EXCEEDED` | 400 | Page size too large |
| `DATAFORGE_RESOURCE_NOT_FOUND` | 404 | Project, version, or entity not found |
| `DATAFORGE_RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded (5 req/60s per key) |
| `DATAFORGE_SERVER_ERROR` | 5xx | Server-side error (retried automatically) |
| `DATAFORGE_TIMEOUT` | — | Request timed out (retried automatically) |
| `DATAFORGE_CONNECTION_ERROR` | — | Network connection error (retried automatically) |

### Retry Behavior

| HTTP Status | Retry? | Notes |
|-------------|--------|-------|
| 400 | No | Client error, fix the request |
| 401, 403 | No | Auth issue, check API key |
| 404 | No | Resource doesn't exist |
| 429 | No | Rate limited, wait and retry manually |
| 5xx | Yes | Up to 3 retries with exponential backoff |
| Timeout | Yes | Up to 3 retries with exponential backoff |
| Connection error | Yes | Up to 3 retries with exponential backoff |
