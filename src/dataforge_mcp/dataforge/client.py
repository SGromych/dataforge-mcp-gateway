"""Async HTTP client for DataForge Product API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from pydantic import SecretStr

from dataforge_mcp.errors import DataForgeError, ErrorCode, map_http_error
from dataforge_mcp.logging import get_logger

from .schemas import (
    DimensionListResponse,
    MeasureListResponse,
    ProjectListResponse,
    RmdResponse,
    VersionListResponse,
)

logger = get_logger(__name__)


class DataForgeClient:
    def __init__(
        self,
        base_url: str,
        api_key: SecretStr | str,
        timeout: httpx.Timeout | None = None,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key if isinstance(api_key, SecretStr) else SecretStr(api_key)
        self._max_retries = max_retries
        self._timeout = timeout or httpx.Timeout(5.0, connect=5.0, read=30.0, write=5.0, pool=5.0)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> DataForgeClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-Api-Key": self._api_key.get_secret_value()},
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

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                response = await self.client.request(method, path, **kwargs)
                if response.status_code >= 500:
                    last_exc = map_http_error(response.status_code, response.text)
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise last_exc
                if response.status_code >= 400:
                    raise map_http_error(response.status_code, response.text)
                return response
            except httpx.TimeoutException as exc:
                last_exc = DataForgeError(
                    code=ErrorCode.DATAFORGE_TIMEOUT,
                    message=f"Request timed out: {exc}",
                    details={"path": path},
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise last_exc from exc
            except httpx.TransportError as exc:
                last_exc = DataForgeError(
                    code=ErrorCode.DATAFORGE_CONNECTION_ERROR,
                    message=f"Connection error: {exc}",
                    details={"path": path},
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise last_exc from exc
            except DataForgeError:
                raise
        raise last_exc  # type: ignore[misc]

    async def get_projects(
        self, page: int = 1, page_size: int = 100
    ) -> ProjectListResponse:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        resp = await self._request("GET", "/rmd-api/v1/projects", params=params)
        return ProjectListResponse.model_validate(resp.json())

    async def get_versions(
        self, project_id: int, page: int = 1, page_size: int = 100
    ) -> VersionListResponse:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        resp = await self._request(
            "GET", f"/rmd-api/v1/projects/{project_id}/versions", params=params
        )
        return VersionListResponse.model_validate(resp.json())

    async def get_measures(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
    ) -> MeasureListResponse:
        params: dict[str, Any] = {"language": language}
        resp = await self._request(
            "GET",
            f"/rmd-api/v1/projects/{project_id}/versions/{version_id}/measures",
            params=params,
        )
        return MeasureListResponse.model_validate(resp.json())

    async def get_dimensions(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
    ) -> DimensionListResponse:
        params: dict[str, Any] = {"language": language}
        resp = await self._request(
            "GET",
            f"/rmd-api/v1/projects/{project_id}/versions/{version_id}/dimensions",
            params=params,
        )
        return DimensionListResponse.model_validate(resp.json())

    async def get_rmd(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
    ) -> RmdResponse:
        params: dict[str, Any] = {"language": language}
        resp = await self._request(
            "GET",
            f"/rmd-api/v1/projects/{project_id}/versions/{version_id}/rmd",
            params=params,
        )
        return RmdResponse.model_validate(resp.json())
