"""Async HTTP client for the DataForge Public API v2.

The read surface lives in :mod:`.read_client`, the write surface in :mod:`.write_client`;
this module owns the transport: connection lifecycle, retries, idempotency and the
translation of HTTP failures into :class:`~dataforge_mcp.errors.DataForgeError`.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import httpx
from pydantic import BaseModel, SecretStr

from dataforge_mcp.errors import DataForgeError, ErrorCode, map_http_error
from dataforge_mcp.logging import get_logger

from .read_client import ReadMixin
from .write_client import WriteMixin
from .write_results import WriteResult

logger = get_logger(__name__)

# Version transfer clones and pushes whole repositories; 30s is not enough.
TRANSFER_TIMEOUT = httpx.Timeout(5.0, connect=5.0, read=180.0, write=60.0, pool=5.0)

# Request bodies for these paths carry Git credentials (PATs, SSH keys, passwords)
# and must never reach the logs (doc section 9.6).
_SENSITIVE_PATH_MARKERS = ("/export/", "/import/", "/git-connections")

# Endpoints that explicitly ignore Idempotency-Key (doc sections 9.9.5, 9.9.8.4,
# 9.9.10, 9.9.11.6): they either create nothing or would replay a stale answer.
_NO_IDEMPOTENCY_MARKERS = (
    "/generate-sql",
    "/export/file",
    "/import/validate",
    "/import/preview",
    "/test",
)


def is_sensitive_path(path: str) -> bool:
    return any(marker in path for marker in _SENSITIVE_PATH_MARKERS)


def accepts_idempotency_key(path: str) -> bool:
    return not any(marker in path for marker in _NO_IDEMPOTENCY_MARKERS)


class DataForgeClient(ReadMixin, WriteMixin):
    def __init__(
        self,
        base_url: str,
        api_key: SecretStr | str,
        timeout: httpx.Timeout | None = None,
        max_retries: int = 3,
        default_language: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key if isinstance(api_key, SecretStr) else SecretStr(api_key)
        self._max_retries = max_retries
        self._timeout = timeout or httpx.Timeout(5.0, connect=5.0, read=30.0, write=5.0, pool=5.0)
        self._default_language = default_language
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> DataForgeClient:
        headers = {"X-Api-Key": self._api_key.get_secret_value()}
        if self._default_language:
            headers["Accept-Language"] = self._default_language
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    # -----------------------------------------------------------------------
    # Transport
    # -----------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        idempotency_key: str | None = None,
        retry_safe: bool | None = None,
        timeout: httpx.Timeout | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform one API call, retrying only where a retry cannot duplicate work.

        GET/PUT/PATCH/DELETE are idempotent by definition. A POST is only safe to repeat
        when it carries an ``Idempotency-Key`` — otherwise a retry after a 5xx or a
        timeout would create a second entity, so we surface the failure instead.
        """
        if idempotency_key is not None:
            _validate_idempotency_key(idempotency_key)
            headers = dict(kwargs.pop("headers", None) or {})
            headers["Idempotency-Key"] = idempotency_key
            kwargs["headers"] = headers

        if retry_safe is None:
            retry_safe = method.upper() != "POST" or idempotency_key is not None
        if timeout is not None:
            kwargs["timeout"] = timeout

        attempts = self._max_retries if retry_safe else 1
        last_exc: Exception | None = None
        in_progress_retries = 0

        for attempt in range(attempts):
            try:
                response = await self.client.request(method, path, **kwargs)

                if response.status_code == 429:
                    raise map_http_error(
                        response.status_code,
                        response.text,
                        path=path,
                        headers=dict(response.headers),
                    )

                if response.status_code >= 500:
                    last_exc = map_http_error(response.status_code, response.text, path=path)
                    if attempt < attempts - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise last_exc

                if response.status_code >= 400:
                    error = map_http_error(
                        response.status_code,
                        response.text,
                        path=path,
                        headers=dict(response.headers),
                    )
                    # A duplicate Idempotency-Key still running is almost always our own
                    # retry catching up with the original call; wait for it to settle.
                    if (
                        error.code is ErrorCode.DATAFORGE_IDEMPOTENCY_IN_PROGRESS
                        and in_progress_retries < 2
                    ):
                        await asyncio.sleep(2**in_progress_retries)
                        in_progress_retries += 1
                        continue
                    raise error

                return response

            except httpx.TimeoutException as exc:
                last_exc = self._transport_error(
                    ErrorCode.DATAFORGE_TIMEOUT,
                    f"Request timed out: {exc}",
                    path,
                    method,
                    retry_safe,
                )
                if attempt < attempts - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise last_exc from exc

            except httpx.TransportError as exc:
                last_exc = self._transport_error(
                    ErrorCode.DATAFORGE_CONNECTION_ERROR,
                    f"Connection error: {exc}",
                    path,
                    method,
                    retry_safe,
                )
                if attempt < attempts - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise last_exc from exc

            except DataForgeError:
                raise

        raise last_exc  # type: ignore[misc]

    def _transport_error(
        self,
        code: ErrorCode,
        message: str,
        path: str,
        method: str,
        retry_safe: bool,
    ) -> DataForgeError:
        details: dict[str, Any] = {"path": path}
        hint = None
        if not retry_safe and method.upper() == "POST":
            details["possibly_applied"] = True
            hint = (
                "This POST carried no Idempotency-Key, so it was not retried and may have"
                " been applied server-side. Verify the current state with a read tool"
                " before resending."
            )
        return DataForgeError(code=code, message=message, details=details, hint=hint)

    # -----------------------------------------------------------------------
    # Write helper
    # -----------------------------------------------------------------------

    async def _write(
        self,
        method: str,
        path: str,
        body: BaseModel | dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
        params: dict[str, Any] | None = None,
        timeout: httpx.Timeout | None = None,
        files: Any = None,
        data: dict[str, Any] | None = None,
    ) -> WriteResult:
        kwargs: dict[str, Any] = {}
        if params:
            kwargs["params"] = params
        if body is not None:
            kwargs["json"] = serialize_body(body)
        if files is not None:
            kwargs["files"] = files
        if data is not None:
            kwargs["data"] = data

        key = idempotency_key if accepts_idempotency_key(path) else None

        response = await self._request(
            method,
            path,
            idempotency_key=key,
            timeout=timeout,
            **kwargs,
        )

        logger.info(
            "write_request",
            method=method,
            path=path,
            http_status=response.status_code,
            # Bodies are deliberately omitted: they may carry Git credentials.
            body_logged=not is_sensitive_path(path),
        )

        if response.status_code == 204 or not response.content:
            return WriteResult(status_code=response.status_code, payload=None)

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        return WriteResult(
            status_code=response.status_code,
            payload=payload if isinstance(payload, dict) else {"result": payload},
            partial=response.status_code == 207,
        )

    # -----------------------------------------------------------------------
    # Path helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _v2_prefix(project_id: int, version_id: int) -> str:
        return f"/df-api/v2/projects/{project_id}/versions/{version_id}"

    @staticmethod
    def _project_prefix(project_id: int) -> str:
        return f"/df-api/v2/projects/{project_id}"


def serialize_body(body: BaseModel | dict[str, Any]) -> dict[str, Any]:
    """Serialize a write body.

    ``exclude_unset`` rather than ``exclude_none``: v2 rejects unknown fields, but an
    explicit ``null`` is meaningful (a filter description reads back as ``null``, and the
    docs guarantee a read object can be sent back unchanged). Only fields the caller
    actually set are transmitted.
    """
    if isinstance(body, BaseModel):
        return body.model_dump(mode="json", by_alias=True, exclude_unset=True)
    return body


def _validate_idempotency_key(key: str) -> None:
    try:
        parsed = uuid.UUID(key)
    except (ValueError, AttributeError, TypeError) as exc:
        raise DataForgeError(
            code=ErrorCode.DATAFORGE_INVALID_IDEMPOTENCY_KEY,
            message=f"Idempotency-Key is not a valid UUID: {key!r}",
        ) from exc
    if parsed.version != 4:
        raise DataForgeError(
            code=ErrorCode.DATAFORGE_INVALID_IDEMPOTENCY_KEY,
            message=f"Idempotency-Key must be a UUID v4, got v{parsed.version}",
        )


def new_idempotency_key() -> str:
    return str(uuid.uuid4())
