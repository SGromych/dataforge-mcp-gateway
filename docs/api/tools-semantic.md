# Semantic Tools Reference

Read-only tools for projects, versions and RMD content (measures, dimensions, facts).

> For tools that **modify** DataForge, see the [Write Tools Reference](tools-write.md).
> For data marts, connections and the physical model, see
> [Data Model Tools](tools-data-model.md).

Shared structures (pagination, source objects, SQL code, errors) are documented in
[Shared Schemas & Errors](schemas.md).

---

## `df_health`

Check that the server is alive, the configuration loaded and the DataForge API reachable.

**Input:** none.

```json
{
  "server_status": "ok",
  "product_api_status": "ok",
  "base_url": "https://api.prod-df.businessqlik.com",
  "cache_status": "ok"
}
```

`product_api_status` is `unavailable` when a probe request fails; this never raises.

---

## `df_list_projects`

List projects visible to the configured API key. Projects the key cannot access are
excluded from both the page and the total.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | `1` | Page number |
| `page_size` | integer | `100` | 1–100 |
| `use_cache` | boolean | `true` | Set `false` to bypass the cache |

```json
{
  "projects": [
    { "id": 12, "name": "Sales Analytics", "description": "Production sales warehouse" }
  ],
  "pagination": { "total": 2, "page": 1, "page_size": 100, "total_pages": 1 }
}
```

---

## `df_list_versions`

| Parameter | Type | Default |
|---|---|---|
| `project_id` | integer | **required** |
| `page`, `page_size`, `use_cache` | | as above |

```json
{
  "project_id": 392,
  "versions": [{ "id": 33, "name": "Q4 2025", "is_global": true }],
  "pagination": { "total": 1, "page": 1, "page_size": 100, "total_pages": 1 }
}
```

`is_global` marks the published version of the project.

---

## `df_get_measures`

All measures of a project version. The tool pages through the API automatically, so a
version with more rows than one page comes back complete.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `project_id`, `version_id` | integer | **required** | |
| `language` | string | server default | `ru` or `en`; affects reference labels only |
| `include_sql` | boolean | `false` | Attach generated SQL to each measure |
| `use_cache` | boolean | `true` | |

```json
{
  "project_id": 392,
  "version_id": 948,
  "measures": [
    {
      "id": "1000",
      "row_number": 1,
      "group": "Revenue",
      "block": "Sales",
      "name": "Total revenue",
      "description": "Gross revenue across all channels",
      "data_type": "Number",
      "measure_type": "Base",
      "formula": null,
      "restrictions": null,
      "original_source_type": "Database",
      "original_source": "ERP",
      "original_object": "sales.amount",
      "report_for_verification": null,
      "comment": null,
      "display_data_type": "Number",
      "status": "Active",
      "relevance": null,
      "required": null,
      "visibility": null,
      "responsible_for_data": null,
      "variation": null,
      "sql_code": null
    }
  ],
  "pagination": { "total": 42, "page": 1, "page_size": 100, "total_pages": 1, "fetched": 42 }
}
```

| Field | Notes |
|---|---|
| `id` | **Stable identifier**, a string. This is what the write tools take — see [Entity IDs](schemas.md#entity-ids) |
| `name` / `description` | Normalized from `measure_name` / `measure_description` |
| `data_type` | Taken from the API's `display_data_type` (a localized label such as `Number`, `Text`, `Date`) |
| `measure_type` | Localized label: `Base` / `Calculated` |
| `required`, `relevance`, `visibility` | **Localized labels (strings), not booleans** |
| `formula` | References are rendered as `[Element name]` |
| `sql_code` | Only with `include_sql=true`, and only when generation succeeded |
| `raw` | Not present unless requested via `df_get_rmd(include_raw=true)` |

Measures have no `connected_source` — only dimensions and facts do.

---

## `df_get_dimensions`

Same parameters as `df_get_measures` minus `include_sql`.

Dimension-specific fields:

| Field | Notes |
|---|---|
| `id` | Stable identifier |
| `dimension_group` | Name of the dimension group this dimension belongs to |
| `dimension_type` | Localized label, e.g. `Primary` |
| `connected_source` | [Source object](schemas.md#source-object), including `connection` |
| `source_data_type` | Derived from `connected_source` via the connection's cached schema; `null` if it could not be resolved |
| `value_options` | Allowed values, where defined |

---

## `df_get_facts`

Same shape. Fact-specific fields: `fact_type` (localized label), `source_data_type`,
`connected_source`, `report_for_verification`.

---

## `df_get_rmd`

The normalized semantic context of a version in one call.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `project_id`, `version_id` | integer | **required** | |
| `language` | string | server default | |
| `include_sql` | boolean | `false` | Attach SQL to each measure |
| `include_raw` | boolean | `false` | Keep the untouched API payload of every row under `raw` |
| `use_cache` | boolean | `true` | |

```json
{
  "project": { "id": "12", "name": "Sales Analytics", "description": "..." },
  "version": { "id": "33", "name": "Q4 2025", "is_global": true },
  "measures": [ ... ],
  "dimensions": [ ... ],
  "facts": [ ... ],
  "stats": { "measure_count": 42, "dimension_count": 18, "fact_count": 6 }
}
```

`project` and `version` are taken from the API response, so they carry real names.

This tool and [`df_get_consolidated_rmd`](tools-data-model.md#df_get_consolidated_rmd)
read the **same endpoint** and share one cache entry: `df_get_rmd` returns the normalized
projection, `df_get_consolidated_rmd` the raw export including the data model. Calling
both costs one HTTP request.

---

## `df_refresh_cache`

Drop the cached state of a version and re-fetch its RMD snapshot.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `project_id`, `version_id` | integer | **required** | |
| `language` | string | server default | |
| `scope` | string | `version` | `version`, `project` or `global` |

```json
{
  "status": "refreshed",
  "scope": "version",
  "entries_removed": 7,
  "cache_key": "rmd:392:948:ru:False",
  "fetched_at": "2026-09-22T08:00:00+00:00"
}
```

`scope=version` clears every cached family of that version (measures, dimensions, facts,
RMD, data marts, connections, dimension groups, fact tables, relationships);
`scope=project` additionally clears the project and version listings and project access.

You rarely need this tool: writes invalidate their own scope automatically.
