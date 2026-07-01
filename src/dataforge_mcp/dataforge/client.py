"""Async HTTP client for DataForge Product API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from pydantic import SecretStr

from dataforge_mcp.errors import DataForgeError, ErrorCode, map_http_error
from dataforge_mcp.logging import get_logger

from .schemas import (
    ConnectionDetail,
    ConnectionListResponse,
    ConnectionSchemaResponse,
    ConsolidatedRmdResponse,
    DataMartDetail,
    DataMartListResponse,
    DimensionGroupDetail,
    DimensionGroupListResponse,
    DimensionListResponse,
    FactListResponse,
    FactTableDetail,
    FactTableListResponse,
    MeasureListResponse,
    PhysicalViewResponse,
    ProjectListResponse,
    RelationshipDetail,
    RelationshipListResponse,
    RmdResponse,
    SqlGenerationResponse,
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
                if response.status_code == 429:
                    raise map_http_error(response.status_code, response.text)
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

    # -----------------------------------------------------------------------
    # DF API v2  (/df-api/v2/)
    # -----------------------------------------------------------------------

    def _v2_prefix(self, project_id: int, version_id: int) -> str:
        return f"/df-api/v2/projects/{project_id}/versions/{version_id}"

    async def get_projects(self, page: int = 1, page_size: int = 100) -> ProjectListResponse:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        resp = await self._request("GET", "/df-api/v2/projects", params=params)
        return ProjectListResponse.model_validate(resp.json())

    async def get_versions(
        self, project_id: int, page: int = 1, page_size: int = 100
    ) -> VersionListResponse:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        resp = await self._request(
            "GET", f"/df-api/v2/projects/{project_id}/versions", params=params
        )
        return VersionListResponse.model_validate(resp.json())

    async def get_measures(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
        include_sql: bool = False,
    ) -> MeasureListResponse:
        params: dict[str, Any] = {"language": language}
        if include_sql:
            params["include_sql"] = "true"
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/measures",
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
            f"{self._v2_prefix(project_id, version_id)}/dimensions",
            params=params,
        )
        return DimensionListResponse.model_validate(resp.json())

    async def get_facts(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
    ) -> FactListResponse:
        params: dict[str, Any] = {"language": language}
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/facts",
            params=params,
        )
        return FactListResponse.model_validate(resp.json())

    async def get_rmd(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
    ) -> RmdResponse:
        params: dict[str, Any] = {"language": language}
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/rmd",
            params=params,
        )
        return RmdResponse.model_validate(resp.json())

    async def get_data_marts(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
        type: str | None = None,
        merge_type: str | None = None,
        search: str | None = None,
    ) -> DataMartListResponse:
        params: dict[str, Any] = {
            "language": language,
            "page": page,
            "pageSize": page_size,
        }
        if type is not None:
            params["type"] = type
        if merge_type is not None:
            params["mergeType"] = merge_type
        if search is not None:
            params["search"] = search
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/data-marts", params=params
        )
        return DataMartListResponse.model_validate(resp.json())

    async def get_data_mart(
        self,
        project_id: int,
        version_id: int,
        data_mart_id: int,
        language: str = "ru",
    ) -> DataMartDetail:
        params: dict[str, Any] = {"language": language}
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/data-marts/{data_mart_id}",
            params=params,
        )
        return DataMartDetail.model_validate(resp.json())

    async def get_data_mart_view(
        self,
        project_id: int,
        version_id: int,
        data_mart_id: int,
    ) -> PhysicalViewResponse:
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/data-marts/{data_mart_id}/view",
        )
        return PhysicalViewResponse.model_validate(resp.json())

    async def generate_sql(
        self,
        project_id: int,
        version_id: int,
        data_mart_id: int,
        limit: int | None = None,
        offset: int | None = None,
    ) -> SqlGenerationResponse:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        resp = await self._request(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/data-marts/{data_mart_id}/generate-sql",
            params=params,
        )
        return SqlGenerationResponse.model_validate(resp.json())

    async def get_connections(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
        db_type: str | None = None,
        status: str | None = None,
    ) -> ConnectionListResponse:
        params: dict[str, Any] = {
            "language": language,
            "page": page,
            "pageSize": page_size,
        }
        if db_type is not None:
            params["dbType"] = db_type
        if status is not None:
            params["status"] = status
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/connections", params=params
        )
        return ConnectionListResponse.model_validate(resp.json())

    async def get_connection(
        self,
        project_id: int,
        version_id: int,
        connection_id: int,
        language: str = "ru",
        include_db_schema: bool = False,
    ) -> ConnectionDetail:
        params: dict[str, Any] = {"language": language}
        if include_db_schema:
            params["includeDbSchema"] = "true"
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/connections/{connection_id}",
            params=params,
        )
        return ConnectionDetail.model_validate(resp.json())

    async def get_connection_schema(
        self,
        project_id: int,
        version_id: int,
        connection_id: int,
    ) -> ConnectionSchemaResponse:
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/connections/{connection_id}/schema",
        )
        return ConnectionSchemaResponse.model_validate(resp.json())

    async def get_dimension_groups(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
    ) -> DimensionGroupListResponse:
        params: dict[str, Any] = {
            "language": language,
            "page": page,
            "pageSize": page_size,
        }
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/dimension-groups",
            params=params,
        )
        return DimensionGroupListResponse.model_validate(resp.json())

    async def get_dimension_group(
        self,
        project_id: int,
        version_id: int,
        dimension_group_id: int,
        language: str = "ru",
    ) -> DimensionGroupDetail:
        params: dict[str, Any] = {"language": language}
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/dimension-groups/{dimension_group_id}",
            params=params,
        )
        return DimensionGroupDetail.model_validate(resp.json())

    async def get_fact_tables(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
    ) -> FactTableListResponse:
        params: dict[str, Any] = {
            "language": language,
            "page": page,
            "pageSize": page_size,
        }
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/fact-tables",
            params=params,
        )
        return FactTableListResponse.model_validate(resp.json())

    async def get_fact_table(
        self,
        project_id: int,
        version_id: int,
        fact_table_id: int,
        language: str = "ru",
        include_dependencies: bool = False,
    ) -> FactTableDetail:
        params: dict[str, Any] = {"language": language}
        if include_dependencies:
            params["includeDependencies"] = "true"
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/fact-tables/{fact_table_id}",
            params=params,
        )
        return FactTableDetail.model_validate(resp.json())

    async def get_relationships(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
        fact_table_id: int | None = None,
        dimension_group_id: int | None = None,
    ) -> RelationshipListResponse:
        params: dict[str, Any] = {
            "language": language,
            "page": page,
            "pageSize": page_size,
        }
        if fact_table_id is not None:
            params["factTableId"] = fact_table_id
        if dimension_group_id is not None:
            params["dimensionGroupId"] = dimension_group_id
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/relationships",
            params=params,
        )
        return RelationshipListResponse.model_validate(resp.json())

    async def get_relationship(
        self,
        project_id: int,
        version_id: int,
        relationship_id: int,
        language: str = "ru",
    ) -> RelationshipDetail:
        params: dict[str, Any] = {"language": language}
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/relationships/{relationship_id}",
            params=params,
        )
        return RelationshipDetail.model_validate(resp.json())

    async def get_consolidated_rmd(
        self,
        project_id: int,
        version_id: int,
        language: str = "ru",
        include_sql: bool = False,
    ) -> ConsolidatedRmdResponse:
        params: dict[str, Any] = {"language": language}
        if include_sql:
            params["include_sql"] = "true"
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/rmd",
            params=params,
        )
        return ConsolidatedRmdResponse.model_validate(resp.json())
