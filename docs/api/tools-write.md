# Write Tools Reference

> # ⚠️ **EVERY TOOL ON THIS PAGE MODIFIES DATAFORGE**
>
> These tools create, replace, update and **permanently delete** data (the two import dry
> runs and the Git connection test are the only ones that do not). There is no
> kill switch in this server — the only limit is the effective project role of the API key
> in `DATAFORGE_API_KEY`. A key resolving to `analyst` or `viewer` makes the server
> effectively read-only; write endpoints answer `403 DF_API.WRITE_ACCESS_DENIED`.
>
> Every write is recorded in the DataForge audit log with before/after snapshots.

---

## Conventions

These rules apply to every tool below and are not repeated per tool.

### Write modes

Tools named `df_write_*` take a `mode` parameter:

| `mode` | HTTP | Meaning |
|---|---|---|
| `create` (default) | `POST` | Adds a new entity. Requires the entity's mandatory fields. |
| `replace` | `PUT` | **Full overwrite.** Requires the mandatory fields, and **resets every optional field you do not pass** to its default/empty value. Requires the target id. |
| `update` | `PATCH` | Changes only the fields you pass. Requires the target id. Nothing else is mandatory. |

Use `update` unless you deliberately want an overwrite.

### Idempotency

Every write generates an `Idempotency-Key` (UUID v4); you may pass your own via
`idempotency_key`. The key is scoped to (API key, method, path, key) and stored for
24 hours:

- repeating a `POST` with the same key replays the original response verbatim;
- a duplicate that is still executing answers `409 idempotency_in_progress` (retried automatically);
- a malformed key is rejected locally before any request is sent.

This is what makes retrying a `POST` after a 5xx safe. A `POST` without a key is **never
retried**; if it times out, the error carries `possibly_applied: true` and a hint to verify
state with a read tool before resending.

Five endpoints ignore the header by design and never receive one: `df_generate_sql`,
`df_export_version_to_file`, `df_check_import_source`, `df_preview_import`,
`df_test_git_connection`.

### Result envelope

```json
{
  "status": "created",
  "http_status": 201,
  "idempotency_key": "0b1d2c3e-4f5a-6789-abcd-ef0123456789",
  "result": { "id": "1000", "measure_name": "Total revenue", "timestamp": "..." },
  "cache_invalidated": ["measures:392:948", "rmd:392:948"]
}
```

| `status` | HTTP | Meaning |
|---|---|---|
| `created` | 201 | Entity created |
| `ok` | 200 | Entity updated, or an operation that answers 200 |
| `deleted` | 204 | Entity deleted; `result` is `null` |
| `partial` | 207 | **Some items were rejected** — see `failed[]` and `succeeded[]` |

`status: "partial"` is never flattened into success: the agent has to see which rows were
rejected and why.

```json
{
  "status": "partial",
  "http_status": 207,
  "succeeded": [{ "id": "501" }],
  "failed": [
    {
      "index": 1,
      "id": "502",
      "error": { "code": "constraint_violation", "message": "Element already assigned", "details": [] }
    }
  ]
}
```

### Strict bodies

The API rejects unknown fields with `400 DF_API.VALIDATION_FAILED` and
`details[].code = unknown_field`. This server enforces the same rule locally, so a typo
comes back as a validation error with the offending field named — in exactly the same
shape the server would have used — without spending a round-trip.

Read-only fields (`id`, `timestamp`, `created_at`, `updated_at`) are accepted and ignored,
which is what lets an object obtained from a read tool be sent straight back. If you pass
`id`, it must match the id in the path, otherwise `DATAFORGE_ID_MISMATCH`.

### Reference columns

`measure_type`, `dimension_type`, `fact_type`, `display_data_type`, `status`, and the flag
columns accept either the English or the Russian label of the option (`Base` / `Базовый`);
matching ignores case and surrounding whitespace. Flag columns (`relevance`, `required`,
`visibility`) take the **strings** `"true"` / `"false"`, not booleans.

An unmatched value in a mandatory reference column answers
`400 DF_API.INVALID_ENUM_VALUE`; in an optional one it is silently dropped.

### Source objects

`connected_source`, `primary_key` and `foreign_key` all take the same object:

```json
{ "connection": "Production PostgreSQL", "db": "analytics_db", "schema": "public", "table": "fact_sales", "column": "amount" }
```

`db` and `table` are mandatory. Whether you pass `connection` selects one of two contracts:

| `connection` | Behaviour |
|---|---|
| passed | The connection is located by exact name (names are unique within a version, and `Prod` is not `prod`). `db`, `table`, and `column` are verified against that connection's cached schema. |
| omitted | Legacy behaviour: `db` is resolved loosely and nothing is verified. |

Use `df_get_connection_schema` to list valid tables and columns. Both keys of one
relationship must name the same connection — a join cannot span two databases.

### Cache invalidation

A write drops the whole cache scope it touched (`cache_invalidated` lists the prefixes),
because the exact set of affected entries is not derivable from the write's arguments. A
read immediately after a write always hits the API.

---

## Projects and versions

| Tool | Required | Notes |
|---|---|---|
| `df_create_project` | `name` | Also accepts `description`, `color` (hex). Creates an initial version. The key owner becomes the owner. |
| `df_update_project` | `project_id` | Partial update of `name`, `description`, `color`. |
| **`df_delete_project`** | `project_id` | ⚠️ **Deletes the project with all of its versions and their entire content.** Cannot be undone. |
| `df_create_version` | `project_id`, `name` | `is_global` publishes it; `clone_from_version` picks the source (default: the current global version). Counts against the licence version limit. |
| `df_update_version` | `project_id`, `version_id` | Only `name` and `is_global` — versions have no description. |
| **`df_delete_version`** | `project_id`, `version_id` | ⚠️ Deletes the version and all of its content. The current global version cannot be deleted (`422 global_version_conflict`). |

## RMD content

`df_write_measure`, `df_write_dimension`, `df_write_fact` share one shape: `project_id`,
`version_id`, `mode`, the entity id (`measure_id` / `dimension_id` / `fact_id`) for
replace/update, and the entity's fields.

**Mandatory for create/replace:**

| Tool | Mandatory fields |
|---|---|
| `df_write_measure` | `measure_name`, `measure_type` |
| `df_write_dimension` | `dimension_name`, `dimension_type` |
| `df_write_fact` | `fact_name`, `fact_type` |

Measures have no `connected_source`; dimensions and facts do. Formula references are
written as `[Element name]`; a syntax error yields `422 invalid_formula_syntax`, an unknown
reference `422 formula_reference_not_found`, a cycle `422 circular_dependency`.

| Tool | Notes |
|---|---|
| `df_bulk_write_measures` / `..._dimensions` / `..._facts` | Create and update in one call: an item **with** `id` is updated (as a PATCH), an item without one is created. Items are applied in order, each in its own transaction. Result may be `partial`. |
| **`df_delete_measure`** | ⚠️ Rejected with `409 constraint_violation` if a formula references it. A measure that is only *assigned* to a fact table is deleted together with that assignment. |
| **`df_delete_dimension`** | ⚠️ Rejected if it belongs to a dimension group or is referenced by a formula. |
| **`df_delete_fact`** | ⚠️ Rejected if a formula references it. |

## Dimension groups

| Tool | Required | Notes |
|---|---|---|
| `df_write_dimension_group` | `name` + `primary_key` for create/replace | `dimensions` sets the initial membership as `[{id, level}]`; levels must be unique. |
| **`df_delete_dimension_group`** | `dimension_group_id` | ⚠️ Rejected while the group is assigned to a fact table. |
| `df_set_group_dimensions` | `dimension_group_id`, `dimensions` | Adds members and/or re-levels existing ones. **All-or-nothing**, answers 200 with the group object — unlike fact-table assignment, there is no partial result. |
| **`df_remove_group_dimension`** | `dimension_group_id`, `dimension_id` | ⚠️ Removes membership; the dimension itself stays in the RMD. Removing a non-member is an error, not a no-op. |

## Fact tables

| Tool | Required | Notes |
|---|---|---|
| `df_write_fact_table` | `name` for create/replace | A fact table created through the API has no base physical table; attach elements separately. `owner` is accepted and ignored. |
| **`df_delete_fact_table`** | `fact_table_id` | ⚠️ Rejected while it has active relationships. |
| `df_assign_to_fact_table` | `fact_table_id`, `element_type`, `element_ids` | `element_type` ∈ `measure` \| `dimension` \| `fact` \| `dimension_group`. Ids are applied in order; an already-assigned id lands in `failed[]` with `constraint_violation`, an unknown one with `resource_not_found`. Result may be `partial`. |
| **`df_unassign_from_fact_table`** | `fact_table_id`, `element_type`, `element_id` | ⚠️ Removes the assignment only; the element stays in the RMD. |

## Verification filters

One pair of tools covers both levels. Passing `fact_table_id` targets a fact-table filter;
omitting it targets a version-level (global) filter.

| Tool | Required | Notes |
|---|---|---|
| `df_write_verification_filter` | `name`, `conditions` for create/replace | Element references in `conditions` are resolved on write and read back as `[Name]`. An unresolved name is kept as-is and reported via `is_valid: false` in the fact table detail. |
| **`df_delete_verification_filter`** | `filter_id` | ⚠️ Pass `fact_table_id` for a fact-table filter. |

## Relationships

| Tool | Required | Notes |
|---|---|---|
| `df_write_relationship` | `source_fact_table_id`, `target_dimension_group_id`, `foreign_key`, `primary_key`, `relationship_type` | `relationship_type` is always `many_to_one`. Both keys must name the same connection, otherwise `400 connection_mismatch`. A second relationship for the same pair yields `409 duplicate_relationship`. |
| **`df_delete_relationship`** | `relationship_id` | ⚠️ |

## Project access

These require the caller to be the **project owner or a company administrator** — a
stricter rule than the `developer` role used for content writes.

| Tool | Required | Notes |
|---|---|---|
| `df_get_project_access` | `project_id` | Read-only. Returns the owner plus every user with explicit access. |
| `df_set_project_access` | `project_id`, `user_id`, `access_level` | `access_level` ∈ `developer` \| `analyst` \| `viewer`. Downgrade-only: a level above the user's global role is rejected. |
| **`df_revoke_project_access`** | `project_id`, `user_id` | ⚠️ Removes explicit access. Answers 200, not 204. |
| `df_transfer_project_ownership` | `project_id`, `new_owner_id` | The new owner must belong to the project's company and hold an ownership-capable role. |

## Version transfer

For CI/CD: move a version's configuration between environments without a browser.
Export and dry runs need `analyst` or above; import needs `developer` or above.

Git credentials are supplied either inline (`authentication`) or by reference to a saved
Git connection (`connection_id`). They are sent over TLS, never logged and never returned;
credentials embedded in `repository_url` are stripped from the response and the audit log.

| Tool | Notes |
|---|---|
| `df_export_version_to_git` | Deterministic: re-exporting an unchanged version creates no commit and answers `commit_hash: null`. The branch is never force-written. |
| `df_export_version_to_file` | Produces a `.dfexport.zip` in object storage and returns a signed URL. `encryption_password` or `use_system_key` seals the archive. |
| `df_check_import_source` | Dry run. Validates the source and returns `valid`, `errors[]`, `warnings[]` and element counts. Writes nothing. |
| `df_preview_import` | Dry run. Compares the source with the target version and reports per-field conflicts. Writes nothing. |
| **`df_import_version_from_git`** | ⚠️ `target.method=create` makes a new version; **`replace` overwrites the version in the path entirely.** `conflict_strategy=overwrite` also applies deletions. Run `df_preview_import` first. |
| **`df_import_version_from_file`** | ⚠️ Same, from a local archive. **On-premises installations only** — the cloud gateway does not forward binary bodies. |

Conflict strategies: `smart_merge` (default — additions and changes applied, local-only
elements kept), `overwrite` (source applied verbatim, including deletions), `skip`
(conflicting elements keep their current values), `manual` (nothing is written if there are
conflicts; the response lists them with `success: false`).

## Git connections

The company-wide registry of saved Git credentials. **All of these require a company
administrator API key.** Paths are company-scoped and carry no project or version.

| Tool | Notes |
|---|---|
| `df_list_git_connections`, `df_get_git_connection` | Read-only. Credentials are never returned. |
| `df_create_git_connection` | `name`, `platform`, `repository_url`, `branch`, `authentication`. `settings` controls branch/path override, default status and sharing. |
| `df_update_git_connection` | Full replacement of the connection's configuration. |
| **`df_delete_git_connection`** | ⚠️ |
| `df_test_git_connection` | Runs five repository checks and refreshes the stored status. A failed check is **not** an error: the response is 200 with `status: "failed"`. |

## Error codes specific to writes

| Code | HTTP | Meaning |
|---|---|---|
| `DATAFORGE_WRITE_ACCESS_DENIED` | 403 | The key's effective project role is below `developer` |
| `DATAFORGE_MISSING_REQUIRED_FIELD` | 400 | A mandatory field is absent (typically on `mode=replace`) |
| `DATAFORGE_VALIDATION_FAILED` | 400 | Body does not match the schema; `fields[]` names the offenders |
| `DATAFORGE_INVALID_ENUM_VALUE` | 400 | A reference column value matched no option |
| `DATAFORGE_ID_MISMATCH` | 400 | `id` in the body differs from the id in the path |
| `DATAFORGE_INVALID_SOURCE_*` | 400 | The source object names an unknown connection, database, schema, table or column |
| `DATAFORGE_CONNECTION_MISMATCH` | 400 | The two keys of a relationship point at different connections |
| `DATAFORGE_INVALID_IDEMPOTENCY_KEY` | 400 | Not a UUID v4 |
| `DATAFORGE_DUPLICATE_NAME` | 409 | Name already taken within its scope |
| `DATAFORGE_DUPLICATE_RELATIONSHIP` | 409 | This fact table → dimension group pair already has a relationship |
| `DATAFORGE_DUPLICATE_LEVEL` | 409 | Two dimensions share a hierarchy level in one group |
| `DATAFORGE_CONSTRAINT_VIOLATION` | 409 | The element is still referenced and cannot be removed |
| `DATAFORGE_IDEMPOTENCY_IN_PROGRESS` | 409 | An identical request is still running |
| `DATAFORGE_INVALID_FORMULA_SYNTAX` | 422 | The formula could not be parsed |
| `DATAFORGE_FORMULA_REFERENCE_NOT_FOUND` | 422 | The formula references a non-existent element |
| `DATAFORGE_CIRCULAR_DEPENDENCY` | 422 | The formula forms a cycle |
| `DATAFORGE_GLOBAL_VERSION_CONFLICT` | 422 | Global-version rule violated |
| `DATAFORGE_BULK_REJECTED` | 422 | No row of a bulk operation was applied |
| `DATAFORGE_LICENSE_LIMIT_REACHED` | 403 | The licence's version limit is reached |
| `DATAFORGE_GIT_CONNECTION_FAILED` | 422 | The repository is unreachable or rejected the credentials |
| `DATAFORGE_GIT_PUSH_FAILED` | 422 | Push rejected: the branch moved or is protected |

Errors carry `api_code`, `fields[]` (which field and why) and, where the agent can fix the
request itself, a `hint`. See [Shared Schemas & Errors](schemas.md).
