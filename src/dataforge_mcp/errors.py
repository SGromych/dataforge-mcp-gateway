"""Error types and DataForge API v2 error mapping.

DF API v2 returns a six-field envelope (product API doc, section 9.9.4)::

    {
      "message": "Invalid merge_type filter value",
      "originalMessage": "DF_API.INVALID_MERGE_TYPE",
      "statusCode": 400,
      "error": "BadRequestException",
      "code": "invalid_merge_type",
      "details": [{"field": "merge_type", "code": "invalid_value"}]
    }

``code`` is the machine-readable key (the ``DF_API.`` catalogue entry lowercased) and
``details[]`` names the offending fields. Both are surfaced to the agent so it can
repair a rejected request without guessing.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    # --- authentication / authorization ------------------------------------
    DATAFORGE_API_KEY_MISSING = "DATAFORGE_API_KEY_MISSING"
    DATAFORGE_API_KEY_INVALID = "DATAFORGE_API_KEY_INVALID"
    DATAFORGE_UNAUTHORIZED = "DATAFORGE_UNAUTHORIZED"
    DATAFORGE_AUTH_FAILED = "DATAFORGE_AUTH_FAILED"
    DATAFORGE_ACCOUNT_LOCKED = "DATAFORGE_ACCOUNT_LOCKED"
    DATAFORGE_IP_BLOCKED = "DATAFORGE_IP_BLOCKED"
    DATAFORGE_LICENSE_INVALID = "DATAFORGE_LICENSE_INVALID"
    DATAFORGE_LICENSE_LIMIT_REACHED = "DATAFORGE_LICENSE_LIMIT_REACHED"
    DATAFORGE_WRITE_ACCESS_DENIED = "DATAFORGE_WRITE_ACCESS_DENIED"

    # --- request validation (400) ------------------------------------------
    DATAFORGE_INVALID_PARAMETER = "DATAFORGE_INVALID_PARAMETER"
    DATAFORGE_PAGE_SIZE_EXCEEDED = "DATAFORGE_PAGE_SIZE_EXCEEDED"
    DATAFORGE_VALIDATION_FAILED = "DATAFORGE_VALIDATION_FAILED"
    DATAFORGE_MISSING_REQUIRED_FIELD = "DATAFORGE_MISSING_REQUIRED_FIELD"
    DATAFORGE_INVALID_ENUM_VALUE = "DATAFORGE_INVALID_ENUM_VALUE"
    DATAFORGE_ID_MISMATCH = "DATAFORGE_ID_MISMATCH"
    DATAFORGE_INVALID_RELATIONSHIP_TYPE = "DATAFORGE_INVALID_RELATIONSHIP_TYPE"
    DATAFORGE_INVALID_TYPE = "DATAFORGE_INVALID_TYPE"
    DATAFORGE_INVALID_MERGE_TYPE = "DATAFORGE_INVALID_MERGE_TYPE"
    DATAFORGE_INVALID_DB_TYPE = "DATAFORGE_INVALID_DB_TYPE"
    DATAFORGE_INVALID_STATUS = "DATAFORGE_INVALID_STATUS"
    DATAFORGE_INVALID_FORMAT = "DATAFORGE_INVALID_FORMAT"
    DATAFORGE_INVALID_IDEMPOTENCY_KEY = "DATAFORGE_INVALID_IDEMPOTENCY_KEY"

    # --- source object validation (400, write) -----------------------------
    DATAFORGE_INVALID_SOURCE_CONNECTION = "DATAFORGE_INVALID_SOURCE_CONNECTION"
    DATAFORGE_INVALID_SOURCE_DB = "DATAFORGE_INVALID_SOURCE_DB"
    DATAFORGE_INVALID_SOURCE_SCHEMA = "DATAFORGE_INVALID_SOURCE_SCHEMA"
    DATAFORGE_INVALID_SOURCE_TABLE = "DATAFORGE_INVALID_SOURCE_TABLE"
    DATAFORGE_INVALID_SOURCE_COLUMN = "DATAFORGE_INVALID_SOURCE_COLUMN"
    DATAFORGE_CONNECTION_MISMATCH = "DATAFORGE_CONNECTION_MISMATCH"

    # --- not found (404) ----------------------------------------------------
    DATAFORGE_RESOURCE_NOT_FOUND = "DATAFORGE_RESOURCE_NOT_FOUND"
    DATAFORGE_PROJECT_NOT_FOUND = "DATAFORGE_PROJECT_NOT_FOUND"
    DATAFORGE_VERSION_NOT_FOUND = "DATAFORGE_VERSION_NOT_FOUND"

    # --- conflict (409) -----------------------------------------------------
    DATAFORGE_DUPLICATE_NAME = "DATAFORGE_DUPLICATE_NAME"
    DATAFORGE_DUPLICATE_RELATIONSHIP = "DATAFORGE_DUPLICATE_RELATIONSHIP"
    DATAFORGE_DUPLICATE_LEVEL = "DATAFORGE_DUPLICATE_LEVEL"
    DATAFORGE_CONSTRAINT_VIOLATION = "DATAFORGE_CONSTRAINT_VIOLATION"
    DATAFORGE_IDEMPOTENCY_IN_PROGRESS = "DATAFORGE_IDEMPOTENCY_IN_PROGRESS"

    # --- semantic validation (422) -----------------------------------------
    DATAFORGE_INVALID_FORMULA_SYNTAX = "DATAFORGE_INVALID_FORMULA_SYNTAX"
    DATAFORGE_FORMULA_REFERENCE_NOT_FOUND = "DATAFORGE_FORMULA_REFERENCE_NOT_FOUND"
    DATAFORGE_CIRCULAR_DEPENDENCY = "DATAFORGE_CIRCULAR_DEPENDENCY"
    DATAFORGE_GLOBAL_VERSION_CONFLICT = "DATAFORGE_GLOBAL_VERSION_CONFLICT"
    DATAFORGE_INVALID_PARAMETER_TYPE = "DATAFORGE_INVALID_PARAMETER_TYPE"
    DATAFORGE_BULK_REJECTED = "DATAFORGE_BULK_REJECTED"
    DATAFORGE_SQL_GENERATION_FAILED = "DATAFORGE_SQL_GENERATION_FAILED"
    DATAFORGE_GIT_CONNECTION_FAILED = "DATAFORGE_GIT_CONNECTION_FAILED"
    DATAFORGE_GIT_PUSH_FAILED = "DATAFORGE_GIT_PUSH_FAILED"
    DATAFORGE_UNPROCESSABLE_ENTITY = "DATAFORGE_UNPROCESSABLE_ENTITY"

    # --- transport / server -------------------------------------------------
    DATAFORGE_TIMEOUT = "DATAFORGE_TIMEOUT"
    DATAFORGE_RATE_LIMIT_EXCEEDED = "DATAFORGE_RATE_LIMIT_EXCEEDED"
    DATAFORGE_SERVER_ERROR = "DATAFORGE_SERVER_ERROR"
    DATAFORGE_INTERNAL_ERROR = "DATAFORGE_INTERNAL_ERROR"
    DATAFORGE_CONNECTION_ERROR = "DATAFORGE_CONNECTION_ERROR"

    # --- local (cache / client side) ---------------------------------------
    CACHE_READ_ERROR = "CACHE_READ_ERROR"
    CACHE_WRITE_ERROR = "CACHE_WRITE_ERROR"

    # --- MCP transport (this server, not DataForge) ------------------------
    MCP_UNAUTHORIZED = "MCP_UNAUTHORIZED"


class DataForgeError(Exception):
    """Normalized DataForge failure, serializable straight into a tool result."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        api_code: str | None = None,
        original_message: str | None = None,
        http_status: int | None = None,
        field_errors: list[dict[str, str]] | None = None,
        retryable: bool = False,
        retry_after_seconds: float | None = None,
        hint: str | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        self.api_code = api_code
        self.original_message = original_message
        self.http_status = (
            http_status if http_status is not None else self.details.get("http_status")
        )
        self.field_errors = field_errors or []
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.hint = hint if hint is not None else _HINTS.get(code)
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }
        if self.api_code:
            error["api_code"] = self.api_code
        if self.original_message:
            error["original_message"] = self.original_message
        if self.http_status is not None:
            error["http_status"] = self.http_status
        if self.field_errors:
            error["fields"] = self.field_errors
        if self.retryable:
            error["retryable"] = True
        if self.retry_after_seconds is not None:
            error["retry_after_seconds"] = self.retry_after_seconds
        if self.hint:
            error["hint"] = self.hint
        return {"error": error}


# ---------------------------------------------------------------------------
# Catalogue maps (product API doc, section 9.11)
# ---------------------------------------------------------------------------

# v2 machine-readable `code` (lower snake_case) -> our code.
_V2_CODE_MAP: dict[str, ErrorCode] = {
    "invalid_api_key": ErrorCode.DATAFORGE_API_KEY_INVALID,
    "account_locked": ErrorCode.DATAFORGE_ACCOUNT_LOCKED,
    "ip_not_allowed": ErrorCode.DATAFORGE_IP_BLOCKED,
    "license_invalid": ErrorCode.DATAFORGE_LICENSE_INVALID,
    "license_limit_reached": ErrorCode.DATAFORGE_LICENSE_LIMIT_REACHED,
    "write_access_denied": ErrorCode.DATAFORGE_WRITE_ACCESS_DENIED,
    "invalid_parameter": ErrorCode.DATAFORGE_INVALID_PARAMETER,
    "page_size_exceeded": ErrorCode.DATAFORGE_PAGE_SIZE_EXCEEDED,
    "validation_failed": ErrorCode.DATAFORGE_VALIDATION_FAILED,
    "missing_required_field": ErrorCode.DATAFORGE_MISSING_REQUIRED_FIELD,
    "invalid_enum_value": ErrorCode.DATAFORGE_INVALID_ENUM_VALUE,
    "id_mismatch": ErrorCode.DATAFORGE_ID_MISMATCH,
    "invalid_relationship_type": ErrorCode.DATAFORGE_INVALID_RELATIONSHIP_TYPE,
    "invalid_type": ErrorCode.DATAFORGE_INVALID_TYPE,
    "invalid_merge_type": ErrorCode.DATAFORGE_INVALID_MERGE_TYPE,
    "invalid_db_type": ErrorCode.DATAFORGE_INVALID_DB_TYPE,
    "invalid_status": ErrorCode.DATAFORGE_INVALID_STATUS,
    "invalid_format": ErrorCode.DATAFORGE_INVALID_FORMAT,
    "invalid_idempotency_key": ErrorCode.DATAFORGE_INVALID_IDEMPOTENCY_KEY,
    "invalid_source_connection": ErrorCode.DATAFORGE_INVALID_SOURCE_CONNECTION,
    "invalid_source_db": ErrorCode.DATAFORGE_INVALID_SOURCE_DB,
    "invalid_source_schema": ErrorCode.DATAFORGE_INVALID_SOURCE_SCHEMA,
    "invalid_source_table": ErrorCode.DATAFORGE_INVALID_SOURCE_TABLE,
    "invalid_source_column": ErrorCode.DATAFORGE_INVALID_SOURCE_COLUMN,
    "connection_mismatch": ErrorCode.DATAFORGE_CONNECTION_MISMATCH,
    "project_not_found": ErrorCode.DATAFORGE_PROJECT_NOT_FOUND,
    "version_not_found": ErrorCode.DATAFORGE_VERSION_NOT_FOUND,
    "resource_not_found": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    "data_mart_not_found": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    "connection_not_found": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    "dimension_group_not_found": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    "fact_table_not_found": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    "relationship_not_found": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    "duplicate_name": ErrorCode.DATAFORGE_DUPLICATE_NAME,
    "duplicate_relationship": ErrorCode.DATAFORGE_DUPLICATE_RELATIONSHIP,
    "duplicate_level": ErrorCode.DATAFORGE_DUPLICATE_LEVEL,
    "constraint_violation": ErrorCode.DATAFORGE_CONSTRAINT_VIOLATION,
    "idempotency_in_progress": ErrorCode.DATAFORGE_IDEMPOTENCY_IN_PROGRESS,
    "invalid_formula_syntax": ErrorCode.DATAFORGE_INVALID_FORMULA_SYNTAX,
    "formula_reference_not_found": ErrorCode.DATAFORGE_FORMULA_REFERENCE_NOT_FOUND,
    "circular_dependency": ErrorCode.DATAFORGE_CIRCULAR_DEPENDENCY,
    "global_version_conflict": ErrorCode.DATAFORGE_GLOBAL_VERSION_CONFLICT,
    "invalid_parameter_type": ErrorCode.DATAFORGE_INVALID_PARAMETER_TYPE,
    "bulk_rejected": ErrorCode.DATAFORGE_BULK_REJECTED,
    "sql_generation_failed": ErrorCode.DATAFORGE_SQL_GENERATION_FAILED,
    "git_connection_failed": ErrorCode.DATAFORGE_GIT_CONNECTION_FAILED,
    "git_push_failed": ErrorCode.DATAFORGE_GIT_PUSH_FAILED,
    "unprocessable_entity": ErrorCode.DATAFORGE_UNPROCESSABLE_ENTITY,
    "rate_limit_exceeded": ErrorCode.DATAFORGE_RATE_LIMIT_EXCEEDED,
    "internal_error": ErrorCode.DATAFORGE_INTERNAL_ERROR,
}

# Guard-level and legacy keys, as they appear in `originalMessage`.
_ERROR_CODE_MAP: dict[str, ErrorCode] = {
    "API_KEY.KEY_MISSING": ErrorCode.DATAFORGE_API_KEY_MISSING,
    "API_KEY.INVALID_KEY": ErrorCode.DATAFORGE_API_KEY_INVALID,
    "API_KEY.INVALID_ENCRYPTED_API_KEY": ErrorCode.DATAFORGE_INVALID_PARAMETER,
    "API_KEY.AUTH_FAILED": ErrorCode.DATAFORGE_AUTH_FAILED,
    "API_KEY.ACCOUNT_LOCKED": ErrorCode.DATAFORGE_ACCOUNT_LOCKED,
    "API_KEY.IP_BLOCKED": ErrorCode.DATAFORGE_IP_BLOCKED,
    "API.NOT_AVAILABLE_WITHOUT_VALID_LICENSE": ErrorCode.DATAFORGE_LICENSE_INVALID,
    "Unauthorized": ErrorCode.DATAFORGE_UNAUTHORIZED,
}

# `DF_API.<KEY>` -> our code, derived from the v2 catalogue above.
_DF_API_KEY_MAP: dict[str, ErrorCode] = {
    f"DF_API.{api_code.upper()}": error_code for api_code, error_code in _V2_CODE_MAP.items()
}

# Unknown keys degrade by HTTP status exactly as the API itself does (9.11).
_STATUS_FALLBACK: dict[int, ErrorCode] = {
    400: ErrorCode.DATAFORGE_INVALID_PARAMETER,
    401: ErrorCode.DATAFORGE_UNAUTHORIZED,
    403: ErrorCode.DATAFORGE_WRITE_ACCESS_DENIED,
    404: ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    409: ErrorCode.DATAFORGE_CONSTRAINT_VIOLATION,
    422: ErrorCode.DATAFORGE_UNPROCESSABLE_ENTITY,
    429: ErrorCode.DATAFORGE_RATE_LIMIT_EXCEEDED,
}

# Actionable guidance for codes an agent can fix on its own.
_HINTS: dict[ErrorCode, str] = {
    ErrorCode.MCP_UNAUTHORIZED: (
        "Send Authorization: Bearer <token> matching MCP_AUTH_TOKEN on the server."
    ),
    ErrorCode.DATAFORGE_VALIDATION_FAILED: (
        "Check fields[]: unknown_field means remove it, missing_field means add it,"
        " invalid_value means the type or value is wrong."
    ),
    ErrorCode.DATAFORGE_MISSING_REQUIRED_FIELD: (
        "mode=replace (PUT) requires every mandatory field. Use mode=update for a partial change."
    ),
    ErrorCode.DATAFORGE_ID_MISMATCH: "The id in the body must equal the id in the path.",
    ErrorCode.DATAFORGE_INVALID_ENUM_VALUE: (
        "Reference-column values accept the English or Russian label of the option,"
        " for example Base or its Russian equivalent."
    ),
    ErrorCode.DATAFORGE_INVALID_SOURCE_TABLE: (
        "Call df_get_connection_schema to list the tables cached for this connection."
    ),
    ErrorCode.DATAFORGE_INVALID_SOURCE_COLUMN: (
        "Call df_get_connection_schema to list the columns of this table."
    ),
    ErrorCode.DATAFORGE_INVALID_SOURCE_CONNECTION: (
        "connection must name a connection of this project version; call"
        " df_list_connections for the exact names (matching is case-sensitive)."
    ),
    ErrorCode.DATAFORGE_INVALID_SOURCE_DB: (
        "db must be the database name of that connection, not the connection name."
    ),
    ErrorCode.DATAFORGE_CONNECTION_MISMATCH: (
        "foreign_key.connection and primary_key.connection must name the same"
        " connection - a join cannot span two databases."
    ),
    ErrorCode.DATAFORGE_DUPLICATE_NAME: "Names must be unique within their scope.",
    ErrorCode.DATAFORGE_DUPLICATE_LEVEL: (
        "Hierarchy levels must be unique across all members of the dimension group."
    ),
    ErrorCode.DATAFORGE_CONSTRAINT_VIOLATION: (
        "The element is still referenced (by a formula, a dimension group or a fact"
        " table). Remove the reference first."
    ),
    ErrorCode.DATAFORGE_IDEMPOTENCY_IN_PROGRESS: (
        "An identical request is still executing. Retry the same call with the same"
        " Idempotency-Key in a few seconds to replay the original response."
    ),
    ErrorCode.DATAFORGE_INVALID_IDEMPOTENCY_KEY: "Idempotency-Key must be a UUID v4.",
    ErrorCode.DATAFORGE_CIRCULAR_DEPENDENCY: "The formula references itself through a cycle.",
    ErrorCode.DATAFORGE_FORMULA_REFERENCE_NOT_FOUND: (
        "The formula references an element that does not exist in this version."
        " References are written as [Element name]."
    ),
    ErrorCode.DATAFORGE_GLOBAL_VERSION_CONFLICT: (
        "A project can have only one global version, and the current global version"
        " cannot be deleted."
    ),
    ErrorCode.DATAFORGE_BULK_REJECTED: (
        "No row was applied. fields[] addresses each rejected row by index."
    ),
    ErrorCode.DATAFORGE_WRITE_ACCESS_DENIED: (
        "The API key's effective project role is below developer."
        " Write endpoints require developer or above."
    ),
    ErrorCode.DATAFORGE_PAGE_SIZE_EXCEEDED: "page_size must be between 1 and 100.",
    ErrorCode.DATAFORGE_RATE_LIMIT_EXCEEDED: (
        "The API allows 100 requests per 60 seconds per API key. Wait and retry."
    ),
}


def _parse_envelope(response_body: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(response_body)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _resolve_code(
    envelope: dict[str, Any] | None, body: str, status_code: int
) -> tuple[ErrorCode, str | None, str | None]:
    """Resolve (our code, api_code, original_message) using the v2 precedence chain."""
    api_code: str | None = None
    original_message: str | None = None

    if envelope is not None:
        raw_api_code = envelope.get("code")
        if isinstance(raw_api_code, str):
            api_code = raw_api_code
            if raw_api_code in _V2_CODE_MAP:
                raw_original = envelope.get("originalMessage")
                return (
                    _V2_CODE_MAP[raw_api_code],
                    api_code,
                    raw_original if isinstance(raw_original, str) else None,
                )

        raw_original = envelope.get("originalMessage")
        if isinstance(raw_original, str):
            original_message = raw_original
            if raw_original in _ERROR_CODE_MAP:
                return _ERROR_CODE_MAP[raw_original], api_code, original_message
            if raw_original in _DF_API_KEY_MAP:
                return _DF_API_KEY_MAP[raw_original], api_code, original_message

        # Compat payloads carry the key in `error` instead of `originalMessage`.
        raw_error = envelope.get("error")
        if isinstance(raw_error, str):
            if raw_error in _ERROR_CODE_MAP:
                return _ERROR_CODE_MAP[raw_error], api_code, original_message or raw_error
            if raw_error in _DF_API_KEY_MAP:
                return _DF_API_KEY_MAP[raw_error], api_code, original_message or raw_error

    # Last resort: substring scan, then degrade by HTTP status.
    for key, error_code in (*_ERROR_CODE_MAP.items(), *_DF_API_KEY_MAP.items()):
        if key in body:
            return error_code, api_code, original_message or key

    if status_code >= 500:
        return ErrorCode.DATAFORGE_SERVER_ERROR, api_code, original_message
    return (
        _STATUS_FALLBACK.get(status_code, ErrorCode.DATAFORGE_SERVER_ERROR),
        api_code,
        original_message,
    )


def _field_errors(envelope: dict[str, Any] | None) -> list[dict[str, str]]:
    if not envelope:
        return []
    raw = envelope.get("details")
    if not isinstance(raw, list):
        return []
    fields: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            entry = {k: str(v) for k, v in item.items() if isinstance(k, str)}
            if entry:
                fields.append(entry)
    return fields


def _retry_after(headers: dict[str, str] | None) -> float | None:
    if not headers:
        return None
    lowered = {k.lower(): v for k, v in headers.items()}
    raw = lowered.get("retry-after") or lowered.get("x-ratelimit-reset")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _default_message(code: ErrorCode, status_code: int, original_message: str | None) -> str:
    if code is ErrorCode.DATAFORGE_RATE_LIMIT_EXCEEDED:
        return "Rate limit exceeded (100 req/60s per API key)"
    if code is ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND and not original_message:
        return "Resource not found"
    if original_message:
        return f"API error: {original_message}"
    if status_code >= 500:
        return f"DataForge server error (HTTP {status_code})"
    return f"DataForge API error (HTTP {status_code})"


def map_http_error(
    status_code: int,
    response_body: str,
    *,
    path: str | None = None,
    headers: dict[str, str] | None = None,
) -> DataForgeError:
    """Translate a DataForge HTTP error response into a :class:`DataForgeError`."""
    details: dict[str, Any] = {"http_status": status_code}
    if path:
        details["path"] = path

    envelope = _parse_envelope(response_body)
    if envelope is None and response_body:
        details["raw_body"] = response_body[:500]

    code, api_code, original_message = _resolve_code(envelope, response_body, status_code)

    message: str | None = None
    if envelope:
        raw_message = envelope.get("message")
        if isinstance(raw_message, str) and raw_message:
            message = raw_message
    if message is None:
        message = _default_message(code, status_code, original_message)

    return DataForgeError(
        code=code,
        message=message,
        details=details,
        api_code=api_code,
        original_message=original_message,
        http_status=status_code,
        field_errors=_field_errors(envelope),
        retryable=(
            status_code == 429
            or status_code >= 500
            or code is ErrorCode.DATAFORGE_IDEMPOTENCY_IN_PROGRESS
        ),
        retry_after_seconds=_retry_after(headers) if status_code == 429 else None,
    )
