"""Error types and HTTP error mapping."""

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    DATAFORGE_API_KEY_MISSING = "DATAFORGE_API_KEY_MISSING"
    DATAFORGE_API_KEY_INVALID = "DATAFORGE_API_KEY_INVALID"
    DATAFORGE_UNAUTHORIZED = "DATAFORGE_UNAUTHORIZED"
    DATAFORGE_AUTH_FAILED = "DATAFORGE_AUTH_FAILED"
    DATAFORGE_RESOURCE_NOT_FOUND = "DATAFORGE_RESOURCE_NOT_FOUND"
    DATAFORGE_TIMEOUT = "DATAFORGE_TIMEOUT"
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
}


def map_http_error(status_code: int, response_body: str) -> DataForgeError:
    details: dict[str, Any] = {"http_status": status_code}

    if status_code == 404:
        return DataForgeError(
            code=ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND,
            message="Resource not found",
            details=details,
        )

    if status_code == 401:
        for api_code, error_code in _ERROR_CODE_MAP.items():
            if api_code in response_body:
                return DataForgeError(
                    code=error_code,
                    message=f"Authentication error: {api_code}",
                    details=details,
                )
        return DataForgeError(
            code=ErrorCode.DATAFORGE_UNAUTHORIZED,
            message="Unauthorized",
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
