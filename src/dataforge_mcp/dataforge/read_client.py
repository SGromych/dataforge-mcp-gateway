"""Read endpoints of the DataForge Public API v2 (doc sections 9.9.2, 9.9.8, 9.9.9).

Query-parameter casing is a contract, not a style choice: v2 names every filter in
snake_case and only ``page``/``pageSize`` in camelCase. Sending ``mergeType`` instead of
``merge_type`` silently drops the filter.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from dataforge_mcp.errors import DataForgeError, ErrorCode

from .schemas import (
    ConnectionDetail,
    ConnectionListResponse,
    ConnectionSchemaResponse,
    DataMartDetail,
    DataMartListResponse,
    DimensionGroupDetail,
    DimensionGroupListResponse,
    DimensionListResponse,
    FactListResponse,
    FactTableDetail,
    FactTableListResponse,
    GitConnectionItem,
    GitConnectionListResponse,
    MeasureListResponse,
    PhysicalViewResponse,
    ProjectAccessEntry,
    ProjectListResponse,
    RelationshipDetail,
    RelationshipListResponse,
    RmdExportResponse,
    SqlGenerationResponse,
    VersionListResponse,
)

# Data marts, connections and Git connections reject pageSize > 100 with HTTP 400;
# every other listing silently caps it instead.
MAX_PAGE_SIZE = 100


class _Transport(Protocol):
    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response: ...

    @staticmethod
    def parse_json(response: httpx.Response) -> Any: ...

    @staticmethod
    def _v2_prefix(project_id: int, version_id: int) -> str: ...

    @staticmethod
    def _project_prefix(project_id: int) -> str: ...


def _check_page_size(page_size: int) -> None:
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise DataForgeError(
            code=ErrorCode.DATAFORGE_PAGE_SIZE_EXCEEDED,
            message=f"page_size must be between 1 and {MAX_PAGE_SIZE}, got {page_size}",
            field_errors=[{"field": "page_size", "code": "invalid_value"}],
        )


def _paged(page: int, page_size: int) -> dict[str, Any]:
    return {"page": page, "pageSize": page_size}


def _flag(params: dict[str, Any], name: str, value: bool) -> None:
    if value:
        params[name] = "true"


class ReadMixin:
    """Read half of :class:`~dataforge_mcp.dataforge.client.DataForgeClient`."""

    # -- projects and versions ---------------------------------------------

    async def get_projects(
        self: _Transport, page: int = 1, page_size: int = 100
    ) -> ProjectListResponse:
        resp = await self._request("GET", "/df-api/v2/projects", params=_paged(page, page_size))
        return ProjectListResponse.model_validate(self.parse_json(resp))

    async def get_versions(
        self: _Transport, project_id: int, page: int = 1, page_size: int = 100
    ) -> VersionListResponse:
        resp = await self._request(
            "GET",
            f"/df-api/v2/projects/{project_id}/versions",
            params=_paged(page, page_size),
        )
        return VersionListResponse.model_validate(self.parse_json(resp))

    # -- RMD content --------------------------------------------------------

    async def get_measures(
        self: _Transport,
        project_id: int,
        version_id: int,
        language: str = "ru",
        include_sql: bool = False,
        page: int = 1,
        page_size: int = 100,
    ) -> MeasureListResponse:
        params: dict[str, Any] = {"language": language, **_paged(page, page_size)}
        _flag(params, "include_sql", include_sql)
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/measures", params=params
        )
        return MeasureListResponse.model_validate(self.parse_json(resp))

    async def get_dimensions(
        self: _Transport,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
    ) -> DimensionListResponse:
        params: dict[str, Any] = {"language": language, **_paged(page, page_size)}
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/dimensions", params=params
        )
        return DimensionListResponse.model_validate(self.parse_json(resp))

    async def get_facts(
        self: _Transport,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
    ) -> FactListResponse:
        params: dict[str, Any] = {"language": language, **_paged(page, page_size)}
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/facts", params=params
        )
        return FactListResponse.model_validate(self.parse_json(resp))

    async def get_rmd(
        self: _Transport,
        project_id: int,
        version_id: int,
        language: str = "ru",
        include_sql: bool = False,
    ) -> RmdExportResponse:
        """Full RMD snapshot — serves both df_get_rmd and df_get_consolidated_rmd."""
        params: dict[str, Any] = {"language": language}
        _flag(params, "include_sql", include_sql)
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/rmd", params=params
        )
        return RmdExportResponse.model_validate(self.parse_json(resp))

    # -- data marts ---------------------------------------------------------

    async def get_data_marts(
        self: _Transport,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
        mart_type: str | None = None,
        merge_type: str | None = None,
        search: str | None = None,
    ) -> DataMartListResponse:
        _check_page_size(page_size)
        params: dict[str, Any] = {"language": language, **_paged(page, page_size)}
        if mart_type:
            params["type"] = mart_type
        if merge_type:
            params["merge_type"] = merge_type
        if search:
            params["search"] = search
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/data-marts", params=params
        )
        return DataMartListResponse.model_validate(self.parse_json(resp))

    async def get_data_mart(
        self: _Transport,
        project_id: int,
        version_id: int,
        data_mart_id: int,
        language: str = "ru",
    ) -> DataMartDetail:
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/data-marts/{data_mart_id}",
            params={"language": language},
        )
        return DataMartDetail.model_validate(self.parse_json(resp))

    async def get_data_mart_view(
        self: _Transport,
        project_id: int,
        version_id: int,
        data_mart_id: int,
        language: str = "ru",
    ) -> PhysicalViewResponse:
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/data-marts/{data_mart_id}/view",
            params={"language": language},
        )
        return PhysicalViewResponse.model_validate(self.parse_json(resp))

    async def generate_sql(
        self: _Transport,
        project_id: int,
        version_id: int,
        data_mart_id: int,
        limit: int | None = None,
        offset: int | None = None,
        language: str = "ru",
    ) -> SqlGenerationResponse:
        """Generate the data mart query. Nothing is executed and nothing is stored.

        Answers HTTP 200 even when generation fails — the failure lives in
        ``validation_errors``, which is what separates "cannot generate right now"
        from "data mart does not exist" (404).
        """
        params: dict[str, Any] = {"language": language}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        resp = await self._request(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/data-marts/{data_mart_id}/generate-sql",
            params=params,
        )
        return SqlGenerationResponse.model_validate(self.parse_json(resp))

    # -- connections --------------------------------------------------------

    async def get_connections(
        self: _Transport,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
        db_type: str | None = None,
        status: str | None = None,
    ) -> ConnectionListResponse:
        _check_page_size(page_size)
        params: dict[str, Any] = {"language": language, **_paged(page, page_size)}
        if db_type:
            params["db_type"] = db_type
        if status:
            params["status"] = status
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/connections", params=params
        )
        return ConnectionListResponse.model_validate(self.parse_json(resp))

    async def get_connection(
        self: _Transport,
        project_id: int,
        version_id: int,
        connection_id: int,
        language: str = "ru",
        include_db_schema: bool = False,
    ) -> ConnectionDetail:
        params: dict[str, Any] = {"language": language}
        _flag(params, "include_db_schema", include_db_schema)
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/connections/{connection_id}",
            params=params,
        )
        return ConnectionDetail.model_validate(self.parse_json(resp))

    async def get_connection_schema(
        self: _Transport,
        project_id: int,
        version_id: int,
        connection_id: int,
        language: str = "ru",
    ) -> ConnectionSchemaResponse:
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/connections/{connection_id}/schema",
            params={"language": language},
        )
        return ConnectionSchemaResponse.model_validate(self.parse_json(resp))

    # -- dimension groups ---------------------------------------------------

    async def get_dimension_groups(
        self: _Transport,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
    ) -> DimensionGroupListResponse:
        params: dict[str, Any] = {"language": language, **_paged(page, page_size)}
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/dimension-groups", params=params
        )
        return DimensionGroupListResponse.model_validate(self.parse_json(resp))

    async def get_dimension_group(
        self: _Transport,
        project_id: int,
        version_id: int,
        dimension_group_id: int,
        language: str = "ru",
    ) -> DimensionGroupDetail:
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/dimension-groups/{dimension_group_id}",
            params={"language": language},
        )
        return DimensionGroupDetail.model_validate(self.parse_json(resp))

    # -- fact tables --------------------------------------------------------

    async def get_fact_tables(
        self: _Transport,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
    ) -> FactTableListResponse:
        params: dict[str, Any] = {"language": language, **_paged(page, page_size)}
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/fact-tables", params=params
        )
        return FactTableListResponse.model_validate(self.parse_json(resp))

    async def get_fact_table(
        self: _Transport,
        project_id: int,
        version_id: int,
        fact_table_id: int,
        language: str = "ru",
        include_dependencies: bool = False,
    ) -> FactTableDetail:
        params: dict[str, Any] = {"language": language}
        _flag(params, "include_dependencies", include_dependencies)
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/fact-tables/{fact_table_id}",
            params=params,
        )
        return FactTableDetail.model_validate(self.parse_json(resp))

    # -- relationships ------------------------------------------------------

    async def get_relationships(
        self: _Transport,
        project_id: int,
        version_id: int,
        language: str = "ru",
        page: int = 1,
        page_size: int = 100,
        fact_table_id: int | None = None,
        dimension_group_id: int | None = None,
    ) -> RelationshipListResponse:
        params: dict[str, Any] = {"language": language, **_paged(page, page_size)}
        if fact_table_id is not None:
            params["fact_table_id"] = fact_table_id
        if dimension_group_id is not None:
            params["dimension_group_id"] = dimension_group_id
        resp = await self._request(
            "GET", f"{self._v2_prefix(project_id, version_id)}/relationships", params=params
        )
        return RelationshipListResponse.model_validate(self.parse_json(resp))

    async def get_relationship(
        self: _Transport,
        project_id: int,
        version_id: int,
        relationship_id: int,
        language: str = "ru",
    ) -> RelationshipDetail:
        resp = await self._request(
            "GET",
            f"{self._v2_prefix(project_id, version_id)}/relationships/{relationship_id}",
            params={"language": language},
        )
        return RelationshipDetail.model_validate(self.parse_json(resp))

    # -- project access (doc section 9.9.7) ---------------------------------

    async def get_project_access(
        self: _Transport, project_id: int, language: str = "ru"
    ) -> list[ProjectAccessEntry]:
        resp = await self._request(
            "GET", f"{self._project_prefix(project_id)}/access", params={"language": language}
        )
        payload = self.parse_json(resp)
        return [ProjectAccessEntry.model_validate(entry) for entry in payload]

    # -- Git connections (doc section 9.9.11) -------------------------------

    async def list_git_connections(
        self: _Transport, page: int = 1, page_size: int = 100
    ) -> GitConnectionListResponse:
        _check_page_size(page_size)
        resp = await self._request(
            "GET", "/df-api/v2/git-connections", params=_paged(page, page_size)
        )
        return GitConnectionListResponse.model_validate(self.parse_json(resp))

    async def get_git_connection(self: _Transport, connection_id: int) -> GitConnectionItem:
        resp = await self._request("GET", f"/df-api/v2/git-connections/{connection_id}")
        return GitConnectionItem.model_validate(self.parse_json(resp))
