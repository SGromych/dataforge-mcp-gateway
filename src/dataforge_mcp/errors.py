"""Error types and HTTP error mapping."""

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    DATAFORGE_API_KEY_MISSING = "DATAFORGE_API_KEY_MISSING"
    DATAFORGE_API_KEY_INVALID = "DATAFORGE_API_KEY_INVALID"
    DATAFORGE_UNAUTHORIZED = "DATAFORGE_UNAUTHORIZED"
    DATAFORGE_AUTH_FAILED = "DATAFORGE_AUTH_FAILED"
    DATAFORGE_ACCOUNT_LOCKED = "DATAFORGE_ACCOUNT_LOCKED"
    DATAFORGE_IP_BLOCKED = "DATAFORGE_IP_BLOCKED"
    DATAFORGE_LICENSE_INVALID = "DATAFORGE_LICENSE_INVALID"
    DATAFORGE_INVALID_PARAMETER = "DATAFORGE_INVALID_PARAMETER"
    DATAFORGE_PAGE_SIZE_EXCEEDED = "DATAFORGE_PAGE_SIZE_EXCEEDED"
    DATAFORGE_RESOURCE_NOT_FOUND = "DATAFORGE_RESOURCE_NOT_FOUND"
    DATAFORGE_TIMEOUT = "DATAFORGE_TIMEOUT"
    DATAFORGE_RATE_LIMIT_EXCEEDED = "DATAFORGE_RATE_LIMIT_EXCEEDED"
    DATAFORGE_SERVER_ERROR = "DATAFORGE_SERVER_ERROR"
    DATAFORGE_CONNECTION_ERROR = "DATAFORGE_CONNECTION_ERROR"
    CACHE_READ_ERROR = "CACHE_READ_ERROR"
    CACHE_WRITE_ERROR = "CACHE_WRITE_ERROR"


class DataForgeError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


_ERROR_CODE_MAP: dict[str, ErrorCode] = {
    "API_KEY.KEY_MISSING": ErrorCode.DATAFORGE_API_KEY_MISSING,
    "API_KEY.INVALID_KEY": ErrorCode.DATAFORGE_API_KEY_INVALID,
    "Unauthorized": ErrorCode.DATAFORGE_UNAUTHORIZED,
    "API_KEY.AUTH_FAILED": ErrorCode.DATAFORGE_AUTH_FAILED,
    "API_KEY.ACCOUNT_LOCKED": ErrorCode.DATAFORGE_ACCOUNT_LOCKED,
    "API_KEY.IP_BLOCKED": ErrorCode.DATAFORGE_IP_BLOCKED,
    "API.NOT_AVAILABLE_WITHOUT_VALID_LICENSE": ErrorCode.DATAFORGE_LICENSE_INVALID,
    "DF_API.INVALID_PARAMETER": ErrorCode.DATAFORGE_INVALID_PARAMETER,
    "DF_API.PAGE_SIZE_EXCEEDED": ErrorCode.DATAFORGE_PAGE_SIZE_EXCEEDED,
    "DF_API.DATA_MART_NOT_FOUND": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    "DF_API.CONNECTION_NOT_FOUND": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    "DF_API.DIMENSION_GROUP_NOT_FOUND": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    "DF_API.FACT_TABLE_NOT_FOUND": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
    "DF_API.RELATIONSHIP_NOT_FOUND": ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
}


def map_http_error(status_code: int, response_body: str) -> DataForgeError:
    details: dict[str, Any] = {"http_status": status_code}

    if status_code == 404:
        return DataForgeError(
            code=ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
            message="Resource not found",
            details=details,
        )

    if status_code == 429:
        return DataForgeError(
            code=ErrorCode.DATAFORGE_RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded (5 req/60s per key)",
            details=details,
        )

    if status_code in (400, 401, 403):
        for api_code, error_code in _ERROR_CODE_MAP.items():
            if api_code in response_body:
                return DataForgeError(
                    code=error_code,
                    message=f"API error: {api_code}",
                    details=details,
                )
        if status_code == 401:
            return DataForgeError(
                code=ErrorCode.DATAFORGE_UNAUTHORIZED,
                message="Unauthorized",
                details=details,
            )
        if status_code == 403:
            return DataForgeError(
                code=ErrorCode.DATAFORGE_UNAUTHORIZED,
                message="Forbidden",
                details=details,
            )
        return DataForgeError(
            code=ErrorCode.DATAFORGE_INVALID_PARAMETER,
            message=f"Bad request (HTTP {status_code})",
            details=details,
        )

    if status_code >= 500:
        return DataForgeError(
            code=ErrorCode.DATAFORGE_SERVER_ERROR,
            message=f"DataForge server error (HTTP {status_code})",
            details=details,
        )

    return DataForgeError(
        code=ErrorCode.DATAFORGE_SERVER_ERROR,
        message=f"Unexpected HTTP error {status_code}",
        details=details,
    )
