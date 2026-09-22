"""Cache invalidation scopes for write operations.

A write touches more cache entries than its arguments suggest: creating one measure
changes ``measures`` for every language and every ``include_sql`` value, the RMD
snapshot, and the fact table detail if that measure is assigned. Enumerating the exact
set is not possible, so a write drops its whole scope. Writes are rare relative to
reads, and serving a stale RMD right after a write breaks the agent's core loop
(write, read back, verify).
"""

from __future__ import annotations

from enum import StrEnum

# Every cache-key family scoped to a single project version.
_VERSION_PREFIXES: tuple[str, ...] = (
    "measures",
    "dimensions",
    "facts",
    "rmd",
    "consolidated_rmd",
    "data_marts",
    "data_mart",
    "data_mart_view",
    "connections",
    "connection",
    "connection_schema",
    "dimension_groups",
    "dimension_group",
    "fact_tables",
    "fact_table",
    "relationships",
    "relationship",
)


class WriteScope(StrEnum):
    GLOBAL = "global"
    """Project listing (project created or deleted)."""

    PROJECT = "project"
    """A project, its versions and all of their content."""

    VERSION = "version"
    """Everything inside one project version."""

    GIT = "git"
    """Company-wide Git connection registry."""


def prefixes_for(
    scope: WriteScope, project_id: int | None = None, version_id: int | None = None
) -> list[str]:
    """Cache-key prefixes a write of this scope invalidates."""
    if scope is WriteScope.GIT:
        return ["git_connections", "git_connection"]

    if scope is WriteScope.GLOBAL:
        return ["projects"]

    if scope is WriteScope.PROJECT:
        if project_id is None:
            return ["projects"]
        prefixes = [f"{prefix}:{project_id}" for prefix in _VERSION_PREFIXES]
        prefixes += ["projects", f"versions:{project_id}", f"project_access:{project_id}"]
        return prefixes

    if project_id is None or version_id is None:
        return []
    return [f"{prefix}:{project_id}:{version_id}" for prefix in _VERSION_PREFIXES]
