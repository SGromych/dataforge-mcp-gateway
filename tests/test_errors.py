"""Error mapping: the v2 envelope, field-level details and status degradation."""

from __future__ import annotations

import json

import pytest

from dataforge_mcp.errors import DataForgeError, ErrorCode, map_http_error
from tests.fixtures import api_v2 as fx


def _map(envelope: dict, status: int | None = None) -> DataForgeError:
    return map_http_error(status or envelope["statusCode"], json.dumps(envelope))


@pytest.mark.parametrize(
    ("envelope", "expected"),
    [
        (fx.ERR_401_INVALID_API_KEY, ErrorCode.DATAFORGE_API_KEY_INVALID),
        (fx.ERR_400_INVALID_MERGE_TYPE, ErrorCode.DATAFORGE_INVALID_MERGE_TYPE),
        (fx.ERR_400_VALIDATION_FAILED, ErrorCode.DATAFORGE_VALIDATION_FAILED),
        (fx.ERR_403_WRITE_ACCESS_DENIED, ErrorCode.DATAFORGE_WRITE_ACCESS_DENIED),
        (fx.ERR_404_PROJECT, ErrorCode.DATAFORGE_PROJECT_NOT_FOUND),
        (fx.ERR_404_DATA_MART, ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND),
        (fx.ERR_409_DUPLICATE_NAME, ErrorCode.DATAFORGE_DUPLICATE_NAME),
        (fx.ERR_409_IDEMPOTENCY_IN_PROGRESS, ErrorCode.DATAFORGE_IDEMPOTENCY_IN_PROGRESS),
        (fx.ERR_422_BULK_REJECTED, ErrorCode.DATAFORGE_BULK_REJECTED),
        (fx.ERR_422_INVALID_FORMULA, ErrorCode.DATAFORGE_INVALID_FORMULA_SYNTAX),
        (fx.ERR_429_RATE_LIMIT, ErrorCode.DATAFORGE_RATE_LIMIT_EXCEEDED),
    ],
)
def test_v2_code_is_mapped(envelope: dict, expected: ErrorCode) -> None:
    assert _map(envelope).code is expected


def test_api_code_and_original_message_are_preserved() -> None:
    error = _map(fx.ERR_404_DATA_MART)
    assert error.api_code == "data_mart_not_found"
    assert error.original_message == "DF_API.DATA_MART_NOT_FOUND"
    assert error.http_status == 404


def test_field_errors_reach_the_agent() -> None:
    """details[] is what lets an agent repair the request instead of guessing."""
    error = _map(fx.ERR_400_VALIDATION_FAILED)
    assert error.field_errors == [{"field": "measures.1.measure_type", "code": "invalid_value"}]
    assert error.to_dict()["error"]["fields"][0]["field"] == "measures.1.measure_type"


def test_bulk_errors_address_rows_by_index() -> None:
    error = _map(fx.ERR_422_BULK_REJECTED)
    assert error.field_errors[0]["field"] == "measures.0"


def test_localized_message_is_kept() -> None:
    error = _map(fx.ERR_400_INVALID_MERGE_TYPE)
    assert error.message == "Некорректное значение фильтра merge_type"


def test_rate_limit_message_mentions_current_quota() -> None:
    error = map_http_error(429, "not json at all")
    assert "100 req/60s" in error.message
    assert "5 req" not in error.message


def test_retry_after_from_headers() -> None:
    error = map_http_error(429, json.dumps(fx.ERR_429_RATE_LIMIT), headers=fx.RATE_LIMIT_HEADERS)
    assert error.retry_after_seconds == 1780000000.0
    assert error.retryable is True


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, ErrorCode.DATAFORGE_INVALID_PARAMETER),
        (401, ErrorCode.DATAFORGE_UNAUTHORIZED),
        (403, ErrorCode.DATAFORGE_WRITE_ACCESS_DENIED),
        (404, ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND),
        (409, ErrorCode.DATAFORGE_CONSTRAINT_VIOLATION),
        (422, ErrorCode.DATAFORGE_UNPROCESSABLE_ENTITY),
        (429, ErrorCode.DATAFORGE_RATE_LIMIT_EXCEEDED),
        (500, ErrorCode.DATAFORGE_SERVER_ERROR),
    ],
)
def test_unknown_code_degrades_by_status(status: int, expected: ErrorCode) -> None:
    """Unknown keys degrade by HTTP status, exactly as the API itself does."""
    envelope = fx.error_envelope("?", "SOMETHING.UNKNOWN", status, "totally_unknown_code")
    assert map_http_error(status, json.dumps(envelope)).code is expected


def test_non_json_body_is_kept_for_diagnosis() -> None:
    error = map_http_error(502, "<html>Bad Gateway</html>")
    assert error.code is ErrorCode.DATAFORGE_SERVER_ERROR
    assert error.details["raw_body"] == "<html>Bad Gateway</html>"


def test_empty_body_does_not_crash() -> None:
    error = map_http_error(404, "")
    assert error.code is ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND
    assert error.message == "Resource not found"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("API_KEY.KEY_MISSING", ErrorCode.DATAFORGE_API_KEY_MISSING),
        ("API_KEY.INVALID_KEY", ErrorCode.DATAFORGE_API_KEY_INVALID),
        ("API_KEY.AUTH_FAILED", ErrorCode.DATAFORGE_AUTH_FAILED),
        ("API_KEY.ACCOUNT_LOCKED", ErrorCode.DATAFORGE_ACCOUNT_LOCKED),
        ("API_KEY.IP_BLOCKED", ErrorCode.DATAFORGE_IP_BLOCKED),
        ("API.NOT_AVAILABLE_WITHOUT_VALID_LICENSE", ErrorCode.DATAFORGE_LICENSE_INVALID),
        ("Unauthorized", ErrorCode.DATAFORGE_UNAUTHORIZED),
    ],
)
def test_guard_level_keys_still_map(key: str, expected: ErrorCode) -> None:
    """Guard errors come from ApiKeyGuard and keep their own key namespace."""
    assert map_http_error(401, json.dumps({"error": key})).code is expected


def test_hints_are_attached_for_fixable_codes() -> None:
    assert (
        "df_get_connection_schema"
        in _map(
            fx.error_envelope("?", "DF_API.INVALID_SOURCE_TABLE", 400, "invalid_source_table")
        ).hint
    )


def test_to_dict_keeps_legacy_http_status_in_details() -> None:
    """Existing consumers read details.http_status; it must survive the new envelope."""
    payload = _map(fx.ERR_404_DATA_MART).to_dict()["error"]
    assert payload["details"]["http_status"] == 404
    assert payload["code"] == ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND


def test_retryable_flag() -> None:
    assert _map(fx.ERR_429_RATE_LIMIT).retryable is True
    assert _map(fx.ERR_409_IDEMPOTENCY_IN_PROGRESS).retryable is True
    assert _map(fx.ERR_404_PROJECT).retryable is False
    assert map_http_error(503, "").retryable is True


def test_path_is_recorded_when_given() -> None:
    error = map_http_error(404, "", path="/df-api/v2/projects/1")
    assert error.details["path"] == "/df-api/v2/projects/1"
