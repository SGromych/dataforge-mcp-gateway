"""MCP tools that modify DataForge.

Every tool here changes server-side state. There is no kill switch in this server: the
only thing limiting what an agent can do is the effective project role of the configured
API key (write endpoints require `developer` or above). The MCP annotations below are
what a client uses to warn a human before the call goes out, so they must stay accurate:
``readOnlyHint=False`` everywhere, ``destructiveHint=True`` for anything that removes or
overwrites data.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.types import Tool, ToolAnnotations

from dataforge_mcp.application.use_cases import SemanticService

from .schema_fragments import (
    ACCESS_LEVELS,
    CONFLICT_STRATEGIES,
    DIMENSION_FIELDS,
    ELEMENT_TYPES,
    EXPORT_OPTIONS_SCHEMA,
    FACT_FIELDS,
    GIT_AUTH_SCHEMA,
    GIT_PLATFORMS,
    IDEMPOTENCY_PROP,
    IMPORT_OPTIONS_SCHEMA,
    MEASURE_FIELDS,
    MODE_PROP,
    PV_REQUIRED,
    SOURCE_OBJECT_SCHEMA,
    WARN,
    WARN_DESTRUCTIVE,
    obj,
    pv_props,
)

Handler = Callable[[dict[str, Any], SemanticService], Awaitable[dict[str, Any]]]

_MUTATES = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
_UPDATES = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True)
_DELETES = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True)


def _rmd_write_tool(
    name: str, entity: str, fields: dict[str, Any], id_field: str, pv: dict[str, Any]
) -> Tool:
    return Tool(
        name=name,
        description=(
            f"{WARN} Create, replace or update a {entity} in a project version."
            " mode=create adds a new one; mode=replace (PUT) overwrites it and RESETS"
            " every optional field you do not pass; mode=update (PATCH) changes only the"
            f" fields you pass. replace and update require {id_field}."
        ),
        inputSchema=obj(
            {
                **pv,
                **MODE_PROP,
                id_field: {"type": "integer", "description": "Required for replace/update"},
                **IDEMPOTENCY_PROP,
                **fields,
            },
            PV_REQUIRED,
        ),
        annotations=_UPDATES,
    )


def build_write_tools(default_language: str) -> list[Tool]:
    pv = pv_props()
    project_only = {"project_id": {"type": "integer"}}

    return [
        # -- projects and versions ------------------------------------------
        Tool(
            name="df_create_project",
            description=f"{WARN} Create a project. An initial version is created with it.",
            inputSchema=obj(
                {
                    "name": {"type": "string", "maxLength": 128},
                    "description": {"type": "string", "maxLength": 255},
                    "color": {"type": "string", "description": "Hex colour, e.g. #2479BC"},
                    **IDEMPOTENCY_PROP,
                },
                ["name"],
            ),
            annotations=_MUTATES,
        ),
        Tool(
            name="df_update_project",
            description=f"{WARN} Update a project's name, description or colour.",
            inputSchema=obj(
                {
                    **project_only,
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "color": {"type": "string"},
                },
                ["project_id"],
            ),
            annotations=_UPDATES,
        ),
        Tool(
            name="df_delete_project",
            description=(
                f"{WARN_DESTRUCTIVE} Delete a project WITH ALL OF ITS VERSIONS and their"
                " entire content. This cannot be undone."
            ),
            inputSchema=obj(project_only, ["project_id"]),
            annotations=_DELETES,
        ),
        Tool(
            name="df_create_version",
            description=(
                f"{WARN} Create a project version. Content is cloned from"
                " clone_from_version, or from the current global version when omitted."
                " Counts against the licence version limit."
            ),
            inputSchema=obj(
                {
                    **project_only,
                    "name": {"type": "string", "maxLength": 64},
                    "is_global": {"type": "boolean"},
                    "clone_from_version": {"type": "string"},
                    **IDEMPOTENCY_PROP,
                },
                ["project_id", "name"],
            ),
            annotations=_MUTATES,
        ),
        Tool(
            name="df_update_version",
            description=(
                f"{WARN} Rename a version or make it the global (published) one."
                " Versions have no description field."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "name": {"type": "string"},
                    "is_global": {"type": "boolean"},
                },
                PV_REQUIRED,
            ),
            annotations=_UPDATES,
        ),
        Tool(
            name="df_delete_version",
            description=(
                f"{WARN_DESTRUCTIVE} Delete a version and all of its content."
                " The current global version cannot be deleted."
            ),
            inputSchema=obj(pv, PV_REQUIRED),
            annotations=_DELETES,
        ),
        # -- RMD content -----------------------------------------------------
        _rmd_write_tool("df_write_measure", "measure", MEASURE_FIELDS, "measure_id", pv),
        _rmd_write_tool("df_write_dimension", "dimension", DIMENSION_FIELDS, "dimension_id", pv),
        _rmd_write_tool("df_write_fact", "fact", FACT_FIELDS, "fact_id", pv),
        Tool(
            name="df_delete_measure",
            description=(
                f"{WARN_DESTRUCTIVE} Delete a measure. Rejected with a conflict if another"
                " element's formula references it."
            ),
            inputSchema=obj(
                {**pv, "measure_id": {"type": "integer"}}, [*PV_REQUIRED, "measure_id"]
            ),
            annotations=_DELETES,
        ),
        Tool(
            name="df_delete_dimension",
            description=(
                f"{WARN_DESTRUCTIVE} Delete a dimension. Rejected if it belongs to a"
                " dimension group or is referenced by a formula."
            ),
            inputSchema=obj(
                {**pv, "dimension_id": {"type": "integer"}}, [*PV_REQUIRED, "dimension_id"]
            ),
            annotations=_DELETES,
        ),
        Tool(
            name="df_delete_fact",
            description=f"{WARN_DESTRUCTIVE} Delete a fact.",
            inputSchema=obj({**pv, "fact_id": {"type": "integer"}}, [*PV_REQUIRED, "fact_id"]),
            annotations=_DELETES,
        ),
        Tool(
            name="df_bulk_write_measures",
            description=(
                f"{WARN} Create and/or update many measures in one call. An item with `id`"
                " is updated, an item without one is created. Items are applied in order,"
                " each in its own transaction: a partial result comes back with"
                " status=partial and a failed[] array addressing rows by index."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "measures": {
                        "type": "array",
                        "minItems": 1,
                        "items": obj(MEASURE_FIELDS),
                    },
                    **IDEMPOTENCY_PROP,
                },
                [*PV_REQUIRED, "measures"],
            ),
            annotations=_MUTATES,
        ),
        Tool(
            name="df_bulk_write_dimensions",
            description=f"{WARN} Create and/or update many dimensions in one call.",
            inputSchema=obj(
                {
                    **pv,
                    "dimensions": {
                        "type": "array",
                        "minItems": 1,
                        "items": obj(DIMENSION_FIELDS),
                    },
                    **IDEMPOTENCY_PROP,
                },
                [*PV_REQUIRED, "dimensions"],
            ),
            annotations=_MUTATES,
        ),
        Tool(
            name="df_bulk_write_facts",
            description=f"{WARN} Create and/or update many facts in one call.",
            inputSchema=obj(
                {
                    **pv,
                    "facts": {"type": "array", "minItems": 1, "items": obj(FACT_FIELDS)},
                    **IDEMPOTENCY_PROP,
                },
                [*PV_REQUIRED, "facts"],
            ),
            annotations=_MUTATES,
        ),
        # -- dimension groups ------------------------------------------------
        Tool(
            name="df_write_dimension_group",
            description=(
                f"{WARN} Create, replace or update a dimension group. primary_key is the"
                " source object of the group's key column."
            ),
            inputSchema=obj(
                {
                    **pv,
                    **MODE_PROP,
                    "dimension_group_id": {"type": "integer"},
                    "name": {"type": "string", "maxLength": 64},
                    "description": {"type": "string", "maxLength": 255},
                    "primary_key": SOURCE_OBJECT_SCHEMA,
                    "dimensions": {
                        "type": "array",
                        "description": "Initial membership",
                        "items": obj(
                            {
                                "id": {"type": "string"},
                                "level": {"type": "integer", "minimum": 1},
                            },
                            ["id", "level"],
                        ),
                    },
                    **IDEMPOTENCY_PROP,
                },
                PV_REQUIRED,
            ),
            annotations=_UPDATES,
        ),
        Tool(
            name="df_delete_dimension_group",
            description=(
                f"{WARN_DESTRUCTIVE} Delete a dimension group. Rejected while it is"
                " assigned to a fact table."
            ),
            inputSchema=obj(
                {**pv, "dimension_group_id": {"type": "integer"}},
                [*PV_REQUIRED, "dimension_group_id"],
            ),
            annotations=_DELETES,
        ),
        Tool(
            name="df_set_group_dimensions",
            description=(
                f"{WARN} Add dimensions to a group, or change the hierarchy level of"
                " existing members. Applied all-or-nothing; levels must stay unique."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "dimension_group_id": {"type": "integer"},
                    "dimensions": {
                        "type": "array",
                        "minItems": 1,
                        "items": obj(
                            {
                                "id": {"type": "string"},
                                "level": {"type": "integer", "minimum": 1},
                            },
                            ["id", "level"],
                        ),
                    },
                    **IDEMPOTENCY_PROP,
                },
                [*PV_REQUIRED, "dimension_group_id", "dimensions"],
            ),
            annotations=_UPDATES,
        ),
        Tool(
            name="df_remove_group_dimension",
            description=(
                f"{WARN_DESTRUCTIVE} Remove one dimension from a group."
                " The dimension itself stays in the RMD."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "dimension_group_id": {"type": "integer"},
                    "dimension_id": {"type": "integer"},
                },
                [*PV_REQUIRED, "dimension_group_id", "dimension_id"],
            ),
            annotations=_DELETES,
        ),
        # -- fact tables -----------------------------------------------------
        Tool(
            name="df_write_fact_table",
            description=(
                f"{WARN} Create, replace or update a fact table. A fact table created via"
                " the API has no base physical table; attach elements with"
                " df_assign_to_fact_table."
            ),
            inputSchema=obj(
                {
                    **pv,
                    **MODE_PROP,
                    "fact_table_id": {"type": "integer"},
                    "name": {"type": "string", "maxLength": 64},
                    "description": {"type": "string", "maxLength": 255},
                    **IDEMPOTENCY_PROP,
                },
                PV_REQUIRED,
            ),
            annotations=_UPDATES,
        ),
        Tool(
            name="df_delete_fact_table",
            description=(
                f"{WARN_DESTRUCTIVE} Delete a fact table. Rejected while it has active"
                " relationships."
            ),
            inputSchema=obj(
                {**pv, "fact_table_id": {"type": "integer"}}, [*PV_REQUIRED, "fact_table_id"]
            ),
            annotations=_DELETES,
        ),
        Tool(
            name="df_assign_to_fact_table",
            description=(
                f"{WARN} Attach existing measures, dimensions, facts or dimension groups"
                " to a fact table. Ids are applied in order; already-assigned or unknown"
                " ids come back in failed[] with status=partial rather than failing the"
                " whole call."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "fact_table_id": {"type": "integer"},
                    "element_type": {"type": "string", "enum": ELEMENT_TYPES},
                    "element_ids": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                    },
                    **IDEMPOTENCY_PROP,
                },
                [*PV_REQUIRED, "fact_table_id", "element_type", "element_ids"],
            ),
            annotations=_MUTATES,
        ),
        Tool(
            name="df_unassign_from_fact_table",
            description=(
                f"{WARN_DESTRUCTIVE} Detach one element from a fact table."
                " The element itself stays in the RMD."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "fact_table_id": {"type": "integer"},
                    "element_type": {"type": "string", "enum": ELEMENT_TYPES},
                    "element_id": {"type": "integer"},
                },
                [*PV_REQUIRED, "fact_table_id", "element_type", "element_id"],
            ),
            annotations=_DELETES,
        ),
        # -- verification filters -------------------------------------------
        Tool(
            name="df_write_verification_filter",
            description=(
                f"{WARN} Create, replace or update a verification filter. Pass"
                " fact_table_id to target a fact-table filter; omit it for a version-level"
                " (global) filter. Element references in conditions are written as"
                " [Element name]."
            ),
            inputSchema=obj(
                {
                    **pv,
                    **MODE_PROP,
                    "filter_id": {"type": "integer"},
                    "fact_table_id": {
                        "type": "integer",
                        "description": "Omit for a version-level filter",
                    },
                    "name": {"type": "string", "maxLength": 64},
                    "description": {"type": "string", "maxLength": 255},
                    "conditions": {"type": "string"},
                    **IDEMPOTENCY_PROP,
                },
                PV_REQUIRED,
            ),
            annotations=_UPDATES,
        ),
        Tool(
            name="df_delete_verification_filter",
            description=f"{WARN_DESTRUCTIVE} Delete a verification filter.",
            inputSchema=obj(
                {
                    **pv,
                    "filter_id": {"type": "integer"},
                    "fact_table_id": {"type": "integer"},
                },
                [*PV_REQUIRED, "filter_id"],
            ),
            annotations=_DELETES,
        ),
        # -- relationships ---------------------------------------------------
        Tool(
            name="df_write_relationship",
            description=(
                f"{WARN} Create, replace or update a star-schema relationship."
                " foreign_key (fact table side) and primary_key (dimension group side)"
                " must name the same connection - a join cannot span two databases."
            ),
            inputSchema=obj(
                {
                    **pv,
                    **MODE_PROP,
                    "relationship_id": {"type": "integer"},
                    "source_fact_table_id": {"type": "string"},
                    "target_dimension_group_id": {"type": "string"},
                    "foreign_key": SOURCE_OBJECT_SCHEMA,
                    "primary_key": SOURCE_OBJECT_SCHEMA,
                    "relationship_type": {"type": "string", "enum": ["many_to_one"]},
                    **IDEMPOTENCY_PROP,
                },
                PV_REQUIRED,
            ),
            annotations=_UPDATES,
        ),
        Tool(
            name="df_delete_relationship",
            description=f"{WARN_DESTRUCTIVE} Delete a relationship.",
            inputSchema=obj(
                {**pv, "relationship_id": {"type": "integer"}},
                [*PV_REQUIRED, "relationship_id"],
            ),
            annotations=_DELETES,
        ),
        # -- project access --------------------------------------------------
        Tool(
            name="df_set_project_access",
            description=(
                f"{WARN} Grant or change a user's access level on a project. Downgrade-only:"
                " a level above the user's global role is rejected. Requires the caller to"
                " be the project owner or a company administrator."
            ),
            inputSchema=obj(
                {
                    **project_only,
                    "user_id": {"type": "integer"},
                    "access_level": {"type": "string", "enum": ACCESS_LEVELS},
                    **IDEMPOTENCY_PROP,
                },
                ["project_id", "user_id", "access_level"],
            ),
            annotations=_UPDATES,
        ),
        Tool(
            name="df_revoke_project_access",
            description=f"{WARN_DESTRUCTIVE} Remove a user's explicit access to a project.",
            inputSchema=obj(
                {**project_only, "user_id": {"type": "integer"}}, ["project_id", "user_id"]
            ),
            annotations=_DELETES,
        ),
        Tool(
            name="df_transfer_project_ownership",
            description=(
                f"{WARN} Transfer project ownership. The new owner must belong to the"
                " project's company and hold an ownership-capable role."
            ),
            inputSchema=obj(
                {**project_only, "new_owner_id": {"type": "integer"}},
                ["project_id", "new_owner_id"],
            ),
            annotations=_UPDATES,
        ),
        # -- version transfer ------------------------------------------------
        Tool(
            name="df_export_version_to_git",
            description=(
                f"{WARN} Export a version's configuration to a Git repository. Pass either"
                " connection_id (a saved Git connection) or authentication. Exporting an"
                " unchanged version creates no commit and returns commit_hash=null."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "repository_url": {"type": "string", "maxLength": 2000},
                    "branch": {"type": "string"},
                    "commit_message": {"type": "string", "minLength": 1, "maxLength": 500},
                    "path": {"type": "string"},
                    "connection_id": {"type": "string"},
                    "authentication": GIT_AUTH_SCHEMA,
                    "options": EXPORT_OPTIONS_SCHEMA,
                    **IDEMPOTENCY_PROP,
                },
                [*PV_REQUIRED, "repository_url", "branch", "commit_message"],
            ),
            annotations=_MUTATES,
        ),
        Tool(
            name="df_export_version_to_file",
            description=(
                f"{WARN} Export a version to a .dfexport.zip archive and return a signed"
                " download link. Nothing in DataForge changes, but the archive is stored."
            ),
            inputSchema=obj({**pv, "options": EXPORT_OPTIONS_SCHEMA}, PV_REQUIRED),
            annotations=_MUTATES,
        ),
        Tool(
            name="df_check_import_source",
            description=(
                "Dry run: validate an import source without writing anything. Returns"
                " valid, errors[], warnings[] and element counts."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "source_type": {"type": "string", "enum": ["git", "file"]},
                    "repository_url": {"type": "string"},
                    "branch": {"type": "string"},
                    "path": {"type": "string"},
                    "commit_hash": {"type": "string"},
                    "connection_id": {"type": "string"},
                    "authentication": GIT_AUTH_SCHEMA,
                    "encryption_password": {"type": "string"},
                    "file_path": {
                        "type": "string",
                        "description": "Local .dfexport.zip path (on-premises only)",
                    },
                },
                PV_REQUIRED,
            ),
            annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=False, idempotentHint=True
            ),
        ),
        Tool(
            name="df_preview_import",
            description=(
                "Dry run: compare an import source with the target version and report what"
                " would change, including per-field conflicts. Nothing is written."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "source_type": {"type": "string", "enum": ["git", "file"]},
                    "repository_url": {"type": "string"},
                    "branch": {"type": "string"},
                    "path": {"type": "string"},
                    "commit_hash": {"type": "string"},
                    "connection_id": {"type": "string"},
                    "authentication": GIT_AUTH_SCHEMA,
                    "conflict_strategy": {"type": "string", "enum": CONFLICT_STRATEGIES},
                    "encryption_password": {"type": "string"},
                    "options": IMPORT_OPTIONS_SCHEMA,
                    "file_path": {"type": "string"},
                },
                PV_REQUIRED,
            ),
            annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=False, idempotentHint=True
            ),
        ),
        Tool(
            name="df_import_version_from_git",
            description=(
                f"{WARN_DESTRUCTIVE} Import a version from Git. target.method=create makes"
                " a new version; target.method=replace OVERWRITES THE VERSION IN THE PATH"
                " entirely. Run df_preview_import first. conflict_strategy=overwrite also"
                " applies deletions."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "repository_url": {"type": "string"},
                    "branch": {"type": "string"},
                    "path": {"type": "string"},
                    "commit_hash": {"type": "string"},
                    "connection_id": {"type": "string"},
                    "authentication": GIT_AUTH_SCHEMA,
                    "target": obj(
                        {
                            "method": {
                                "type": "string",
                                "enum": ["create", "replace"],
                                "default": "create",
                            },
                            "version_name": {"type": "string", "maxLength": 64},
                        },
                        ["version_name"],
                    ),
                    "conflict_strategy": {
                        "type": "string",
                        "enum": CONFLICT_STRATEGIES,
                        "default": "smart_merge",
                    },
                    "options": IMPORT_OPTIONS_SCHEMA,
                    **IDEMPOTENCY_PROP,
                },
                [*PV_REQUIRED, "repository_url", "branch", "target"],
            ),
            annotations=_DELETES,
        ),
        Tool(
            name="df_import_version_from_file",
            description=(
                f"{WARN_DESTRUCTIVE} Import a version from a local .dfexport.zip archive."
                " On-premises installations only. target_method=replace OVERWRITES the"
                " version in the path."
            ),
            inputSchema=obj(
                {
                    **pv,
                    "file_path": {"type": "string"},
                    "target_version_name": {"type": "string", "maxLength": 64},
                    "target_method": {
                        "type": "string",
                        "enum": ["create", "replace"],
                        "default": "create",
                    },
                    "conflict_strategy": {"type": "string", "enum": CONFLICT_STRATEGIES},
                    "encryption_password": {"type": "string"},
                    "options": IMPORT_OPTIONS_SCHEMA,
                    **IDEMPOTENCY_PROP,
                },
                [*PV_REQUIRED, "file_path", "target_version_name"],
            ),
            annotations=_DELETES,
        ),
        # -- Git connections -------------------------------------------------
        Tool(
            name="df_create_git_connection",
            description=(
                f"{WARN} Register a Git connection for the company. Requires a company"
                " administrator API key. Credentials are stored encrypted and never"
                " returned."
            ),
            inputSchema=obj(
                {
                    "name": {"type": "string", "maxLength": 255},
                    "platform": {"type": "string", "enum": GIT_PLATFORMS},
                    "repository_url": {"type": "string"},
                    "branch": {"type": "string"},
                    "path": {"type": "string"},
                    "authentication": GIT_AUTH_SCHEMA,
                    "settings": obj(
                        {
                            "allow_branch_override": {"type": "boolean"},
                            "allow_path_override": {"type": "boolean"},
                            "set_as_default": {"type": "boolean"},
                            "share_with_all": {"type": "boolean"},
                        }
                    ),
                    **IDEMPOTENCY_PROP,
                },
                ["name", "platform", "repository_url", "branch", "authentication"],
            ),
            annotations=_MUTATES,
        ),
        Tool(
            name="df_update_git_connection",
            description=f"{WARN} Replace a saved Git connection's configuration.",
            inputSchema=obj(
                {
                    "connection_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "platform": {"type": "string", "enum": GIT_PLATFORMS},
                    "repository_url": {"type": "string"},
                    "branch": {"type": "string"},
                    "path": {"type": "string"},
                    "authentication": GIT_AUTH_SCHEMA,
                    "settings": obj(
                        {
                            "allow_branch_override": {"type": "boolean"},
                            "allow_path_override": {"type": "boolean"},
                            "set_as_default": {"type": "boolean"},
                            "share_with_all": {"type": "boolean"},
                        }
                    ),
                },
                ["connection_id"],
            ),
            annotations=_UPDATES,
        ),
        Tool(
            name="df_delete_git_connection",
            description=f"{WARN_DESTRUCTIVE} Delete a saved Git connection.",
            inputSchema=obj({"connection_id": {"type": "integer"}}, ["connection_id"]),
            annotations=_DELETES,
        ),
        Tool(
            name="df_test_git_connection",
            description=(
                f"{WARN} Run the five repository checks for a saved Git connection and"
                " refresh its stored status. A failed check is reported as"
                " status=failed, not as an error."
            ),
            inputSchema=obj({"connection_id": {"type": "integer"}}, ["connection_id"]),
            annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=False, idempotentHint=True
            ),
        ),
    ]


# Fields that are tool plumbing rather than entity data.
_CONTROL_KEYS = {
    "project_id",
    "version_id",
    "mode",
    "idempotency_key",
    "measure_id",
    "dimension_id",
    "fact_id",
    "dimension_group_id",
    "fact_table_id",
    "relationship_id",
    "filter_id",
    "connection_id",
    "language",
}


def _entity_fields(args: dict[str, Any], *extra_control: str) -> dict[str, Any]:
    drop = _CONTROL_KEYS | set(extra_control)
    return {k: v for k, v in args.items() if k not in drop}


WRITE_HANDLERS: dict[str, Handler] = {
    # projects and versions
    "df_create_project": lambda a, s: s.create_project(
        idempotency_key=a.get("idempotency_key"), **_entity_fields(a)
    ),
    "df_update_project": lambda a, s: s.update_project(
        project_id=a["project_id"], **_entity_fields(a)
    ),
    "df_delete_project": lambda a, s: s.delete_project(project_id=a["project_id"]),
    "df_create_version": lambda a, s: s.create_version(
        project_id=a["project_id"],
        idempotency_key=a.get("idempotency_key"),
        **_entity_fields(a),
    ),
    "df_update_version": lambda a, s: s.update_version(
        project_id=a["project_id"], version_id=a["version_id"], **_entity_fields(a)
    ),
    "df_delete_version": lambda a, s: s.delete_version(
        project_id=a["project_id"], version_id=a["version_id"]
    ),
    # RMD content
    "df_write_measure": lambda a, s: s.write_measure(
        project_id=a["project_id"],
        version_id=a["version_id"],
        mode=a.get("mode", "create"),
        measure_id=a.get("measure_id"),
        idempotency_key=a.get("idempotency_key"),
        **_entity_fields(a),
    ),
    "df_write_dimension": lambda a, s: s.write_dimension(
        project_id=a["project_id"],
        version_id=a["version_id"],
        mode=a.get("mode", "create"),
        dimension_id=a.get("dimension_id"),
        idempotency_key=a.get("idempotency_key"),
        **_entity_fields(a),
    ),
    "df_write_fact": lambda a, s: s.write_fact(
        project_id=a["project_id"],
        version_id=a["version_id"],
        mode=a.get("mode", "create"),
        fact_id=a.get("fact_id"),
        idempotency_key=a.get("idempotency_key"),
        **_entity_fields(a),
    ),
    "df_delete_measure": lambda a, s: s.delete_measure(
        project_id=a["project_id"], version_id=a["version_id"], measure_id=a["measure_id"]
    ),
    "df_delete_dimension": lambda a, s: s.delete_dimension(
        project_id=a["project_id"], version_id=a["version_id"], dimension_id=a["dimension_id"]
    ),
    "df_delete_fact": lambda a, s: s.delete_fact(
        project_id=a["project_id"], version_id=a["version_id"], fact_id=a["fact_id"]
    ),
    "df_bulk_write_measures": lambda a, s: s.bulk_write_measures(
        project_id=a["project_id"],
        version_id=a["version_id"],
        measures=a["measures"],
        idempotency_key=a.get("idempotency_key"),
    ),
    "df_bulk_write_dimensions": lambda a, s: s.bulk_write_dimensions(
        project_id=a["project_id"],
        version_id=a["version_id"],
        dimensions=a["dimensions"],
        idempotency_key=a.get("idempotency_key"),
    ),
    "df_bulk_write_facts": lambda a, s: s.bulk_write_facts(
        project_id=a["project_id"],
        version_id=a["version_id"],
        facts=a["facts"],
        idempotency_key=a.get("idempotency_key"),
    ),
    # dimension groups
    "df_write_dimension_group": lambda a, s: s.write_dimension_group(
        project_id=a["project_id"],
        version_id=a["version_id"],
        mode=a.get("mode", "create"),
        dimension_group_id=a.get("dimension_group_id"),
        idempotency_key=a.get("idempotency_key"),
        **_entity_fields(a),
    ),
    "df_delete_dimension_group": lambda a, s: s.delete_dimension_group(
        project_id=a["project_id"],
        version_id=a["version_id"],
        dimension_group_id=a["dimension_group_id"],
    ),
    "df_set_group_dimensions": lambda a, s: s.set_group_dimensions(
        project_id=a["project_id"],
        version_id=a["version_id"],
        dimension_group_id=a["dimension_group_id"],
        dimensions=a["dimensions"],
        idempotency_key=a.get("idempotency_key"),
    ),
    "df_remove_group_dimension": lambda a, s: s.remove_group_dimension(
        project_id=a["project_id"],
        version_id=a["version_id"],
        dimension_group_id=a["dimension_group_id"],
        dimension_id=a["dimension_id"],
    ),
    # fact tables
    "df_write_fact_table": lambda a, s: s.write_fact_table(
        project_id=a["project_id"],
        version_id=a["version_id"],
        mode=a.get("mode", "create"),
        fact_table_id=a.get("fact_table_id"),
        idempotency_key=a.get("idempotency_key"),
        **_entity_fields(a),
    ),
    "df_delete_fact_table": lambda a, s: s.delete_fact_table(
        project_id=a["project_id"],
        version_id=a["version_id"],
        fact_table_id=a["fact_table_id"],
    ),
    "df_assign_to_fact_table": lambda a, s: s.assign_to_fact_table(
        project_id=a["project_id"],
        version_id=a["version_id"],
        fact_table_id=a["fact_table_id"],
        element_type=a["element_type"],
        element_ids=a["element_ids"],
        idempotency_key=a.get("idempotency_key"),
    ),
    "df_unassign_from_fact_table": lambda a, s: s.unassign_from_fact_table(
        project_id=a["project_id"],
        version_id=a["version_id"],
        fact_table_id=a["fact_table_id"],
        element_type=a["element_type"],
        element_id=a["element_id"],
    ),
    # verification filters
    "df_write_verification_filter": lambda a, s: s.write_verification_filter(
        project_id=a["project_id"],
        version_id=a["version_id"],
        mode=a.get("mode", "create"),
        filter_id=a.get("filter_id"),
        fact_table_id=a.get("fact_table_id"),
        idempotency_key=a.get("idempotency_key"),
        **_entity_fields(a),
    ),
    "df_delete_verification_filter": lambda a, s: s.delete_verification_filter(
        project_id=a["project_id"],
        version_id=a["version_id"],
        filter_id=a["filter_id"],
        fact_table_id=a.get("fact_table_id"),
    ),
    # relationships
    "df_write_relationship": lambda a, s: s.write_relationship(
        project_id=a["project_id"],
        version_id=a["version_id"],
        mode=a.get("mode", "create"),
        relationship_id=a.get("relationship_id"),
        idempotency_key=a.get("idempotency_key"),
        **_entity_fields(a),
    ),
    "df_delete_relationship": lambda a, s: s.delete_relationship(
        project_id=a["project_id"],
        version_id=a["version_id"],
        relationship_id=a["relationship_id"],
    ),
    # project access
    "df_set_project_access": lambda a, s: s.set_project_access(
        project_id=a["project_id"],
        user_id=a["user_id"],
        access_level=a["access_level"],
        idempotency_key=a.get("idempotency_key"),
    ),
    "df_revoke_project_access": lambda a, s: s.revoke_project_access(
        project_id=a["project_id"], user_id=a["user_id"]
    ),
    "df_transfer_project_ownership": lambda a, s: s.transfer_project_ownership(
        project_id=a["project_id"], new_owner_id=a["new_owner_id"]
    ),
    # version transfer
    "df_export_version_to_git": lambda a, s: s.export_version_to_git(
        project_id=a["project_id"],
        version_id=a["version_id"],
        idempotency_key=a.get("idempotency_key"),
        **_entity_fields(a),
    ),
    "df_export_version_to_file": lambda a, s: s.export_version_to_file(
        project_id=a["project_id"], version_id=a["version_id"], **_entity_fields(a)
    ),
    "df_check_import_source": lambda a, s: s.check_import_source(
        project_id=a["project_id"],
        version_id=a["version_id"],
        file_path=a.get("file_path"),
        **_entity_fields(a, "file_path"),
    ),
    "df_preview_import": lambda a, s: s.preview_import(
        project_id=a["project_id"],
        version_id=a["version_id"],
        file_path=a.get("file_path"),
        **_entity_fields(a, "file_path"),
    ),
    "df_import_version_from_git": lambda a, s: s.import_version_from_git(
        project_id=a["project_id"],
        version_id=a["version_id"],
        idempotency_key=a.get("idempotency_key"),
        **_entity_fields(a),
    ),
    "df_import_version_from_file": lambda a, s: s.import_version_from_file(
        project_id=a["project_id"],
        version_id=a["version_id"],
        file_path=a["file_path"],
        target_version_name=a["target_version_name"],
        target_method=a.get("target_method", "create"),
        conflict_strategy=a.get("conflict_strategy"),
        encryption_password=a.get("encryption_password"),
        options=a.get("options"),
        idempotency_key=a.get("idempotency_key"),
    ),
    # Git connections
    "df_create_git_connection": lambda a, s: s.create_git_connection(
        idempotency_key=a.get("idempotency_key"), **_entity_fields(a)
    ),
    "df_update_git_connection": lambda a, s: s.update_git_connection(
        connection_id=a["connection_id"], **_entity_fields(a)
    ),
    "df_delete_git_connection": lambda a, s: s.delete_git_connection(
        connection_id=a["connection_id"]
    ),
    "df_test_git_connection": lambda a, s: s.test_git_connection(connection_id=a["connection_id"]),
}
