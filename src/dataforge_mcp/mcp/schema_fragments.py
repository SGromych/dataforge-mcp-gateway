"""Reusable JSON Schema fragments shared by the tool definitions.

Filter value catalogues live here too: the API rejects anything outside them, so
publishing them as ``enum`` lets the agent get it right on the first try.
"""

from __future__ import annotations

from typing import Any

PV_REQUIRED = ["project_id", "version_id"]

DATA_MART_TYPES = ["with_grouping", "without_grouping", "with_grouping_and_pivoting"]
MERGE_TYPES = ["union", "join"]
DB_TYPES = ["postgresql", "clickhouse", "sqlserver"]
CONNECTION_STATUSES = ["active", "inactive", "never_verified", "failed"]
ACCESS_LEVELS = ["developer", "analyst", "viewer"]
ELEMENT_TYPES = ["measure", "dimension", "fact", "dimension_group"]
GIT_PLATFORMS = ["github", "gitlab", "bitbucket", "azure-devops", "generic"]
CONFLICT_STRATEGIES = ["smart_merge", "overwrite", "skip", "manual"]
WRITE_MODES = ["create", "replace", "update"]
FLAG_VALUES = ["true", "false"]

WARN = "WRITES TO DATAFORGE."
WARN_DESTRUCTIVE = "PERMANENTLY DELETES DATA IN DATAFORGE."


def pv_props(language_default: str | None = None) -> dict[str, Any]:
    props: dict[str, Any] = {
        "project_id": {"type": "integer", "description": "DataForge project id"},
        "version_id": {"type": "integer", "description": "Project version id"},
    }
    if language_default is not None:
        props["language"] = {"type": "string", "default": language_default}
    return props


def paging_props() -> dict[str, Any]:
    return {
        "page": {"type": "integer", "default": 1, "minimum": 1},
        "page_size": {"type": "integer", "default": 100, "minimum": 1, "maximum": 100},
    }


IDEMPOTENCY_PROP: dict[str, Any] = {
    "idempotency_key": {
        "type": "string",
        "description": (
            "Optional UUID v4. Reusing a key within 24 hours replays the original"
            " response instead of applying the change twice. One is generated"
            " automatically when omitted."
        ),
    }
}

MODE_PROP: dict[str, Any] = {
    "mode": {
        "type": "string",
        "enum": WRITE_MODES,
        "default": "create",
        "description": (
            "create = POST a new entity; replace = PUT, which resets every optional"
            " field not supplied; update = PATCH, which changes only supplied fields."
        ),
    }
}

SOURCE_OBJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": (
        "Physical location of the data. Supplying `connection` switches the API to strict"
        " validation of db/schema/table/column against that connection's cached schema."
    ),
    "properties": {
        "connection": {
            "type": "string",
            "description": "Connection name, exact match, unique within the version",
        },
        "db": {"type": "string", "description": "Database name of that connection"},
        "schema": {
            "type": "string",
            "description": "PostgreSQL only; empty for MS SQL Server and ClickHouse",
        },
        "table": {"type": "string"},
        "column": {"type": "string", "description": "Omit to reference the whole table"},
    },
    "required": ["db", "table"],
}

_FLAG = {"type": "string", "enum": FLAG_VALUES}

_COMMON_RMD_FIELDS: dict[str, Any] = {
    "id": {"type": "string", "description": "Entity id; must match the path id if supplied"},
    "group": {"type": "string"},
    "block": {"type": "string"},
    "original_source_type": {"type": "string"},
    "original_source": {"type": "string"},
    "original_object": {"type": "string"},
    "comment": {"type": "string"},
    "status": {"type": "string"},
    "relevance": _FLAG,
    "required": _FLAG,
    "visibility": _FLAG,
    "responsible_for_data": {"type": "string"},
}

MEASURE_FIELDS: dict[str, Any] = {
    **_COMMON_RMD_FIELDS,
    "measure_name": {"type": "string", "description": "Unique among measures of the version"},
    "measure_type": {
        "type": "string",
        "description": "Reference label, English or Russian: Base / Calculated",
    },
    "measure_description": {"type": "string", "maxLength": 255},
    "display_data_type": {"type": "string", "description": "Number, Text, Date, ..."},
    "restrictions": {"type": "string"},
    "formula": {"type": "string", "description": "References are written as [Element name]"},
    "report_for_verification": {"type": "string"},
    "variation": {"type": "string"},
}

DIMENSION_FIELDS: dict[str, Any] = {
    **_COMMON_RMD_FIELDS,
    "dimension_name": {"type": "string"},
    "dimension_type": {"type": "string", "description": "Reference label, e.g. Primary"},
    "dimension_description": {"type": "string", "maxLength": 255},
    "dimension_group": {"type": "string"},
    "display_data_type": {"type": "string"},
    "connected_source": SOURCE_OBJECT_SCHEMA,
    "formula": {"type": "string"},
    "value_options": {"type": "string"},
}

FACT_FIELDS: dict[str, Any] = {
    **_COMMON_RMD_FIELDS,
    "fact_name": {"type": "string"},
    "fact_type": {"type": "string", "description": "Reference label, e.g. Primary"},
    "fact_description": {"type": "string", "maxLength": 255},
    "connected_source": SOURCE_OBJECT_SCHEMA,
    "formula": {"type": "string"},
    "report_for_verification": {"type": "string"},
}

GIT_AUTH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "Git credentials, sent over TLS. Never logged, never returned.",
    "properties": {
        "method": {"type": "string", "enum": ["pat", "ssh", "password"]},
        "token": {"type": "string", "description": "Personal access token (method=pat)"},
        "private_key": {"type": "string", "description": "SSH private key (method=ssh)"},
        "passphrase": {"type": "string"},
        "username": {"type": "string"},
        "password": {"type": "string"},
    },
    "required": ["method"],
}

EXPORT_OPTIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "include_rmd": {"type": "boolean", "default": True},
        "include_fact_tables": {"type": "boolean", "default": True},
        "include_data_marts": {"type": "boolean", "default": True},
        "include_connections": {"type": "boolean", "default": True},
        "include_history": {"type": "boolean", "default": False},
        "encrypt_sensitive": {"type": "boolean", "default": True},
        "add_gitattributes": {"type": "boolean", "default": True},
        "save_connection": {"type": "boolean"},
        "connection_name": {"type": "string"},
        "encryption_password": {"type": "string"},
        "use_system_key": {"type": "boolean"},
    },
}

IMPORT_OPTIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "import_rmd": {"type": "boolean", "default": True},
        "import_fact_tables": {"type": "boolean", "default": True},
        "import_data_marts": {"type": "boolean", "default": True},
        "import_connections": {"type": "boolean", "default": True},
        "import_history": {"type": "boolean", "default": False},
        "detect_merges": {"type": "boolean", "default": True},
        "decrypt_sensitive": {"type": "boolean", "default": True},
        "encryption_password": {"type": "string"},
    },
}


def obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}
