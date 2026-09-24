# Changelog

Notable changes per release. Dates are the release date; the detail behind a decision is
in [docs/api/transport-decisions.md](docs/api/transport-decisions.md).

## 0.3.1 — 2026-09-23

The first release after the gateway was run against a live DataForge instance, which is
where every fix below comes from. **Three separate defects each made the server impossible
to start**, and none of them was visible to the test suite.

### Breaking

- **Requires the MCP SDK 2.x** (`mcp>=2.2,<3`). 1.x cannot run this version: 2.x replaced
  the `@server.list_tools()` / `@server.call_tool()` decorators with `on_list_tools` /
  `on_call_tool` constructor handlers. Upgrade with `pip install -e ".[dev]"`.
  The unbounded `mcp>=1.26` of 0.3.0 is what let a fresh install resolve to 2.x and die at
  startup with `AttributeError: 'Server' object has no attribute 'list_tools'`.

### Fixed

- **`dataforge_mcp.cache` was missing from every distribution.** A `cache/` line in
  `.gitignore`, meant for the runtime cache directory, also matched
  `src/dataforge_mcp/cache/`; two modules were never committed and hatchling, which honours
  VCS ignore files, shipped a wheel without the package. `pip install` succeeded and every
  entry point died with `ModuleNotFoundError`. The rule is now `/cache/`, the modules are
  committed, and the build no longer consults `.gitignore` at all (`ignore-vcs = true`).
- **The Docker build failed on metadata generation** — `pyproject.toml` declares
  `readme = "README.md"` and the builder stage never copied it.
- **A base URL pointing at the site root produced `JSONDecodeError`.** Installations that
  serve the API under `/api` answer `/df-api/v2/…` with the HTML of the web app and
  HTTP 200. Reads now raise `DATAFORGE_INVALID_RESPONSE` carrying the content type, a body
  preview and the hint that names the setting, and `df_health` reports the same as
  `product_api_error` instead of a bare `product_api_status: unavailable`.
- **An empty `MCP_AUTH_TOKEN` locked everyone out silently** — the bearer middleware was
  installed around an empty secret while the log said `auth=bearer`. Empty now means "no
  authentication".

### Changed

- **Tool arguments are validated by this server**, in the documented
  `{code, message, fields[], hint}` envelope, listing every offending argument at once.
  The SDK's bare `Input validation error: '18' is not of type 'integer'` is gone.
  Unambiguous values are coerced: `"18"` → `18` for an integer id, `"true"` → `true`,
  and `true` → `"true"` for the reference columns that travel as strings. Declared schemas
  still say `integer`.
- A tool result carrying an `error` object is now flagged with `isError`.
- `docker-compose.yml` passes `MCP_AUTH_TOKEN` through, and the token-generating one-liner
  is in `.env.example`, `docker-compose.yml` and the README.
- A `.dockerignore` keeps the vendored API documentation, the cache and `.git` out of the
  build context (~40 MB → ~100 KB).
- The server reports its own version on `initialize`.

### Documentation

- Troubleshooting tables in the README, `configuration.md` and `transports.md`, including
  Git Bash rewriting `-e MCP_HTTP_PATH=/mcp` into `C:/Program Files/Git/mcp` — the server
  starts cleanly and serves the endpoint on a path nobody will request
  (`MSYS_NO_PATHCONV=1`).
- `schemas.md` documents `DATAFORGE_INVALID_RESPONSE` and the tool-argument contract.
- **Known API limitation**, in `schemas.md` and `tools-data-model.md`: the data-mart view
  response does not say which database physically holds the mart's table — `database` is
  the engine slug, `schema` is usually `null`, and `connection` names the source rather
  than the target. `target_connection_id` / `target_database` / `target_schema` have been
  requested from the DataForge API team.

### Tests

478 → 502. New: `test_packaging.py` (a source module that is untracked, ignored or absent
from the wheel fails the build) and `test_mcp_arguments.py` (coercion and the rejection
envelope). Verified additionally by hand: a clean-venv install from a built wheel, a real
MCP client over a socket, and the Docker image running healthy.

## 0.3.0 — 2026-09-22

- Streamable HTTP transport for Open WebUI and other HTTP clients, with bearer auth,
  Origin validation and `/health`; the deprecated SSE transport kept for existing
  deployments.
- The full DF API v2 write surface: 41 state-changing tools (38 of which write to
  DataForge), version export/import over Git and file, the Git connection registry and
  project access management.
- README reworked for GitHub, with the tool tables pinned to the code by a contract test.

## 0.2.0

- Migration of every call from `rmd-api/v1` + `df-api/v1` to `df-api/v2`, and the v2 read
  surface: facts, data marts, connections, dimension groups, fact tables, relationships.

## 0.1.0

- Initial MCP server: the semantic layer (projects, versions, measures, dimensions, RMD)
  over stdio, with a file cache and the normalizer.
