"""Tool-argument preparation: tolerant coercion, then a strict, structured verdict.

Two things made a rejected call hard for an agent to repair.

The MCP SDK used to validate ``arguments`` against ``inputSchema`` itself and answered
with a bare sentence — ``Input validation error: '18' is not of type 'integer'`` — while
this server's documented contract is the ``{code, message, fields[], hint}`` envelope.
A client written against the documentation showed "unknown error". SDK 2.x hands the
arguments over unvalidated, so the check lives here and speaks the documented envelope.

And ids arrive as strings more often than not: many clients keep them that way in a
connection profile, and JSON has no separate integer type on the way in from a form.
``"18"`` is not ambiguous, so it is coerced rather than rejected. The declared schema
stays ``integer`` - this is leniency at the door, not a change of contract.
"""

from __future__ import annotations

from typing import Any

from dataforge_mcp.errors import DataForgeError, ErrorCode

#: Spellings of a boolean that arrive from shells, forms and prompt templates.
_TRUE = frozenset({"true", "yes", "on", "1"})
_FALSE = frozenset({"false", "no", "off", "0"})

#: Reference columns are written as the strings "true"/"false" (see CLAUDE.md), so a
#: boolean handed to a string field is spelled out rather than rejected.
_BOOL_AS_STRING = {True: "true", False: "false"}


class _CoercionError(Exception):
    """A value that cannot be coerced. Carries what the schema expected."""

    def __init__(self, expected: str) -> None:
        self.expected = expected
        super().__init__(expected)


def prepare_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce ``arguments`` against a tool's ``inputSchema``.

    Returns a new dict; raises :class:`DataForgeError` listing every offending field at
    once, so one round trip is enough for the agent to fix the call.
    """
    properties: dict[str, Any] = schema.get("properties") or {}
    required: list[str] = schema.get("required") or []

    fields: list[dict[str, str]] = []
    prepared: dict[str, Any] = {}

    for name in required:
        if arguments.get(name) is None:
            fields.append({"field": name, "code": "missing_field"})

    for name, value in arguments.items():
        prop = properties.get(name)
        if prop is None:
            fields.append({"field": name, "code": "unknown_field"})
            continue
        if value is None:
            prepared[name] = None
            continue
        try:
            prepared[name] = _coerce(prop, value)
        except _CoercionError as invalid:
            fields.append(
                {
                    "field": name,
                    "code": "invalid_value",
                    "expected": invalid.expected,
                    "received": type(value).__name__,
                }
            )

    if fields:
        raise DataForgeError(
            code=ErrorCode.DATAFORGE_VALIDATION_FAILED,
            message="Invalid tool arguments",
            field_errors=fields,
            details={"tool_arguments": True},
        )

    return prepared


def _coerce(prop: dict[str, Any], value: Any) -> Any:
    declared = prop.get("type")
    coerced = _coerce_type(declared, prop, value) if declared else value

    enum = prop.get("enum")
    if enum is not None and coerced not in enum:
        raise _CoercionError(f"one of {', '.join(str(option) for option in enum)}")

    return coerced


def _coerce_type(declared: Any, prop: dict[str, Any], value: Any) -> Any:
    if isinstance(declared, list):
        # A union: accept the value if any member accepts it, keeping the first match.
        for candidate in declared:
            try:
                return _coerce_type(candidate, prop, value)
            except _CoercionError:
                continue
        raise _CoercionError(" or ".join(str(item) for item in declared))

    if declared == "integer":
        return _as_integer(value)
    if declared == "number":
        return _as_number(value)
    if declared == "boolean":
        return _as_boolean(value)
    if declared == "string":
        return _as_string(value)
    if declared == "object":
        return _as_object(prop, value)
    if declared == "array":
        return _as_array(prop, value)
    return value


def _as_integer(value: Any) -> int:
    if isinstance(value, bool):
        raise _CoercionError("integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text)
        except ValueError:
            try:
                number = float(text)
            except ValueError:
                raise _CoercionError("integer") from None
            if number.is_integer():
                return int(number)
    raise _CoercionError("integer")


def _as_number(value: Any) -> float | int:
    if isinstance(value, bool):
        raise _CoercionError("number")
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            raise _CoercionError("number") from None
    raise _CoercionError("number")


def _as_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise _CoercionError("boolean")


def _as_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return _BOOL_AS_STRING[value]
    if isinstance(value, (int, float)):
        return str(value)
    raise _CoercionError("string")


def _as_object(prop: dict[str, Any], value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _CoercionError("object")
    properties: dict[str, Any] = prop.get("properties") or {}
    if not properties:
        return value
    # Nested members are coerced too, but never rejected here: the strict request
    # bodies in write_schemas.py report those with the API's own field codes.
    result = dict(value)
    for name, nested in properties.items():
        if name in result and result[name] is not None:
            try:
                result[name] = _coerce(nested, result[name])
            except _CoercionError:
                pass
    return result


def _as_array(prop: dict[str, Any], value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise _CoercionError("array")
    items = prop.get("items")
    if not isinstance(items, dict):
        return value
    result: list[Any] = []
    for item in value:
        try:
            result.append(_coerce(items, item) if item is not None else item)
        except _CoercionError:
            result.append(item)
    return result
