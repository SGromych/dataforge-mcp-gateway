"""Use-case orchestration: client + cache + normalizer."""

from __future__ import annotations

import time
from typing import Any

from dataforge_mcp.cache.store import (
    CacheStore,
    connection_key,
    connection_schema_key,
    connections_key,
    data_mart_key,
    data_mart_view_key,
    data_marts_key,
    dimension_group_key,
    dimension_groups_key,
    dimensions_key,
    fact_table_key,
    fact_tables_key,
    facts_key,
    git_connection_key,
    git_connections_key,
    measures_key,
    project_access_key,
    projects_key,
    relationship_key,
    relationships_key,
    rmd_key,
    versions_key,
)
from dataforge_mcp.config import Settings
from dataforge_mcp.dataforge.client import DataForgeClient
from dataforge_mcp.errors import DataForgeError
from dataforge_mcp.logging import get_logger
from dataforge_mcp.semantic.models import CanonicalProject, CanonicalVersion
from dataforge_mcp.semantic.normalizer import (
    build_semantic_context,
    normalize_dimensions,
    normalize_facts,
    normalize_measures,
)

from .write_use_cases import WriteUseCasesMixin

logger = get_logger(__name__)

# RMD listings cap pageSize at 100 silently, so paging through them is safe.
_PAGE_SIZE = 100
_MAX_PAGES = 100


class SemanticService(WriteUseCasesMixin):
    def __init__(
        self,
        client: DataForgeClient,
        cache: CacheStore,
        settings: Settings,
    ) -> None:
        self.client = client
        self.cache = cache
        self.settings = settings

    def _new_client(self) -> DataForgeClient:
        """Fresh connection per call, carrying the configured retry and timeout policy."""
        return DataForgeClient(
            base_url=self.client.base_url,
            api_key=self.client._api_key,
            timeout=self.client._timeout,
            max_retries=self.client._max_retries,
            default_language=self.client._default_language,
        )

    def _lang(self, language: str | None) -> str:
        return language or self.settings.default_language

    async def check_health(self) -> dict[str, Any]:
        cache_ok = await self.cache.is_healthy()
        api_ok = True
        try:
            async with self._new_client() as c:
                await c.get_projects(page=1, page_size=1)
        except Exception:
            api_ok = False

        return {
            "server_status": "ok",
            "product_api_status": "ok" if api_ok else "unavailable",
            "base_url": self.client.base_url,
            "cache_status": "ok" if cache_ok else "unavailable",
        }

    # -----------------------------------------------------------------------
    # Cache plumbing
    # -----------------------------------------------------------------------

    async def _cached_fetch(
        self,
        key: str,
        use_cache: bool,
        tool_name: str,
        fetch: Any,
        **log_ctx: Any,
    ) -> dict[str, Any]:
        started = time.perf_counter()

        if use_cache:
            cached = await self.cache.get(key)
            if cached is not None:
                logger.info(
                    "cache_hit",
                    tool_name=tool_name,
                    cache_key=key,
                    response_time_ms=round((time.perf_counter() - started) * 1000, 2),
                    **log_ctx,
                )
                return cached

        try:
            result = await fetch()
        except DataForgeError:
            stale = await self.cache.get_last_known_good(key)
            if stale is not None:
                logger.warning("using_last_known_good", tool_name=tool_name, cache_key=key)
                return stale
            raise

        await self.cache.set(key, result, self.settings.cache_ttl_seconds)
        logger.info(
            "cache_miss",
            tool_name=tool_name,
            cache_key=key,
            response_time_ms=round((time.perf_counter() - started) * 1000, 2),
            **log_ctx,
        )
        return result

    # -----------------------------------------------------------------------
    # Projects and versions
    # -----------------------------------------------------------------------

    async def list_projects(
        self, page: int = 1, page_size: int = 100, use_cache: bool = True
    ) -> dict[str, Any]:
        return await self._cached_fetch(
            key=projects_key(page, page_size),
            use_cache=use_cache,
            tool_name="df_list_projects",
            fetch=lambda: self._fetch_projects(page, page_size),
        )

    async def _fetch_projects(self, page: int, page_size: int) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_projects(page=page, page_size=page_size)
        return {
            "projects": [
                CanonicalProject(id=p.id, name=p.name, description=p.description).model_dump()
                for p in resp.projects
            ],
            "pagination": _pagination(resp.pagination),
        }

    async def list_versions(
        self,
        project_id: int,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        return await self._cached_fetch(
            key=versions_key(project_id, page, page_size),
            use_cache=use_cache,
            tool_name="df_list_versions",
            fetch=lambda: self._fetch_versions(project_id, page, page_size),
            project_id=project_id,
        )

    async def _fetch_versions(self, project_id: int, page: int, page_size: int) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_versions(project_id, page=page, page_size=page_size)
        return {
            "project_id": project_id,
            "versions": [
                CanonicalVersion(id=v.id, name=v.name, is_global=v.is_global).model_dump()
                for v in resp.versions
            ],
            "pagination": _pagination(resp.pagination),
        }

    # -----------------------------------------------------------------------
    # RMD content
    # -----------------------------------------------------------------------

    async def get_measures(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        include_sql: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=measures_key(project_id, version_id, lang, include_sql),
            use_cache=use_cache,
            tool_name="df_get_measures",
            fetch=lambda: self._fetch_measures(project_id, version_id, lang, include_sql),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_measures(
        self, project_id: int, version_id: int, language: str, include_sql: bool
    ) -> dict[str, Any]:
        rows: list[Any] = []
        pagination = None
        async with self._new_client() as c:
            for page in range(1, _MAX_PAGES + 1):
                resp = await c.get_measures(
                    project_id,
                    version_id,
                    language,
                    include_sql,
                    page=page,
                    page_size=_PAGE_SIZE,
                )
                rows.extend(resp.measures)
                pagination = resp.pagination
                if _is_last_page(resp.pagination, page, len(resp.measures)):
                    break
        return {
            "project_id": project_id,
            "version_id": version_id,
            "measures": [m.model_dump() for m in normalize_measures(rows)],
            "pagination": _pagination(pagination, fetched=len(rows)),
        }

    async def get_dimensions(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=dimensions_key(project_id, version_id, lang),
            use_cache=use_cache,
            tool_name="df_get_dimensions",
            fetch=lambda: self._fetch_dimensions(project_id, version_id, lang),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_dimensions(
        self, project_id: int, version_id: int, language: str
    ) -> dict[str, Any]:
        rows: list[Any] = []
        pagination = None
        async with self._new_client() as c:
            for page in range(1, _MAX_PAGES + 1):
                resp = await c.get_dimensions(
                    project_id, version_id, language, page=page, page_size=_PAGE_SIZE
                )
                rows.extend(resp.dimensions)
                pagination = resp.pagination
                if _is_last_page(resp.pagination, page, len(resp.dimensions)):
                    break
        return {
            "project_id": project_id,
            "version_id": version_id,
            "dimensions": [d.model_dump() for d in normalize_dimensions(rows)],
            "pagination": _pagination(pagination, fetched=len(rows)),
        }

    async def get_facts(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=facts_key(project_id, version_id, lang),
            use_cache=use_cache,
            tool_name="df_get_facts",
            fetch=lambda: self._fetch_facts(project_id, version_id, lang),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_facts(
        self, project_id: int, version_id: int, language: str
    ) -> dict[str, Any]:
        rows: list[Any] = []
        pagination = None
        async with self._new_client() as c:
            for page in range(1, _MAX_PAGES + 1):
                resp = await c.get_facts(
                    project_id, version_id, language, page=page, page_size=_PAGE_SIZE
                )
                rows.extend(resp.facts)
                pagination = resp.pagination
                if _is_last_page(resp.pagination, page, len(resp.facts)):
                    break
        return {
            "project_id": project_id,
            "version_id": version_id,
            "facts": [f.model_dump() for f in normalize_facts(rows)],
            "pagination": _pagination(pagination, fetched=len(rows)),
        }

    # -----------------------------------------------------------------------
    # RMD snapshot
    #
    # df_get_rmd and df_get_consolidated_rmd hit the same endpoint. One fetch, one
    # cache entry; the semantic tool is a projection of the raw export.
    # -----------------------------------------------------------------------

    async def _rmd_snapshot(
        self,
        project_id: int,
        version_id: int,
        language: str,
        include_sql: bool,
        use_cache: bool,
        tool_name: str,
    ) -> dict[str, Any]:
        return await self._cached_fetch(
            key=rmd_key(project_id, version_id, language, include_sql),
            use_cache=use_cache,
            tool_name=tool_name,
            fetch=lambda: self._fetch_rmd(project_id, version_id, language, include_sql),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_rmd(
        self, project_id: int, version_id: int, language: str, include_sql: bool
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_rmd(project_id, version_id, language, include_sql)
        return resp.model_dump(by_alias=False)

    async def get_rmd(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        include_sql: bool = False,
        use_cache: bool = True,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        """Normalized semantic context: project, version, measures, dimensions, facts."""
        lang = self._lang(language)
        snapshot = await self._rmd_snapshot(
            project_id, version_id, lang, include_sql, use_cache, "df_get_rmd"
        )

        project_raw = snapshot.get("project") or {}
        version_raw = snapshot.get("version") or {}
        context = build_semantic_context(
            project=CanonicalProject(
                id=project_raw.get("id", project_id),
                name=project_raw.get("name"),
                description=project_raw.get("description"),
            ),
            version=CanonicalVersion(
                id=version_raw.get("id", version_id),
                name=version_raw.get("name"),
                is_global=version_raw.get("is_global"),
            ),
            measures=normalize_measures(_as_raw("measure", snapshot.get("measures", []))),
            dimensions=normalize_dimensions(_as_raw("dimension", snapshot.get("dimensions", []))),
            facts=normalize_facts(_as_raw("fact", snapshot.get("facts", []))),
        )

        result = context.model_dump()
        if not include_raw:
            for bucket in ("measures", "dimensions", "facts"):
                for row in result.get(bucket, []):
                    row.pop("raw", None)
        return result

    async def get_consolidated_rmd(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        include_sql: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Raw full export: RMD content plus the whole data model in one payload."""
        lang = self._lang(language)
        return await self._rmd_snapshot(
            project_id, version_id, lang, include_sql, use_cache, "df_get_consolidated_rmd"
        )

    async def refresh_cache(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        scope: str = "version",
    ) -> dict[str, Any]:
        """Drop the cached state of a version (or project) and re-fetch the RMD."""
        from .invalidation import WriteScope, prefixes_for

        write_scope = WriteScope(scope)
        removed = 0
        for prefix in prefixes_for(write_scope, project_id, version_id):
            removed += await self.cache.invalidate_prefix(prefix)

        lang = self._lang(language)
        await self._rmd_snapshot(
            project_id, version_id, lang, False, use_cache=False, tool_name="df_refresh_cache"
        )
        return {
            "status": "refreshed",
            "scope": write_scope.value,
            "entries_removed": removed,
            "cache_key": rmd_key(project_id, version_id, lang),
            "fetched_at": _now(),
        }

    # -----------------------------------------------------------------------
    # Data marts
    # -----------------------------------------------------------------------

    async def list_data_marts(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        page: int = 1,
        page_size: int = 100,
        mart_type: str | None = None,
        merge_type: str | None = None,
        search: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        key = data_marts_key(
            project_id, version_id, lang, page, page_size, mart_type, merge_type, search
        )
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_list_data_marts",
            fetch=lambda: self._fetch_data_marts(
                project_id, version_id, lang, page, page_size, mart_type, merge_type, search
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_data_marts(
        self,
        project_id: int,
        version_id: int,
        language: str,
        page: int,
        page_size: int,
        mart_type: str | None,
        merge_type: str | None,
        search: str | None,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_data_marts(
                project_id,
                version_id,
                language,
                page=page,
                page_size=page_size,
                mart_type=mart_type,
                merge_type=merge_type,
                search=search,
            )
        return {
            "project_id": project_id,
            "version_id": version_id,
            "data_marts": [m.model_dump(by_alias=False) for m in resp.data_marts],
            "pagination": _pagination(resp.pagination),
        }

    async def get_data_mart(
        self,
        project_id: int,
        version_id: int,
        data_mart_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=data_mart_key(project_id, version_id, data_mart_id, lang),
            use_cache=use_cache,
            tool_name="df_get_data_mart",
            fetch=lambda: self._fetch_data_mart(project_id, version_id, data_mart_id, lang),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_data_mart(
        self, project_id: int, version_id: int, data_mart_id: int, language: str
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_data_mart(project_id, version_id, data_mart_id, language)
        return resp.model_dump(by_alias=True)

    async def get_data_mart_view(
        self,
        project_id: int,
        version_id: int,
        data_mart_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=data_mart_view_key(project_id, version_id, data_mart_id, lang),
            use_cache=use_cache,
            tool_name="df_get_data_mart_view",
            fetch=lambda: self._fetch_data_mart_view(project_id, version_id, data_mart_id, lang),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_data_mart_view(
        self, project_id: int, version_id: int, data_mart_id: int, language: str
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_data_mart_view(project_id, version_id, data_mart_id, language)
        return resp.model_dump(by_alias=True)

    async def generate_sql(
        self,
        project_id: int,
        version_id: int,
        data_mart_id: int,
        limit: int | None = None,
        offset: int | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Generate the data mart SQL.

        Never cached: the endpoint regenerates on every call by design, and the result
        depends on limit/offset. A failure to generate is HTTP 200 with a non-empty
        ``validation_errors`` list, not an error — ``succeeded`` makes that explicit.
        """
        lang = self._lang(language)
        async with self._new_client() as c:
            resp = await c.generate_sql(project_id, version_id, data_mart_id, limit, offset, lang)
        result = resp.model_dump(by_alias=False)
        result["succeeded"] = not resp.validation_errors
        result["project_id"] = project_id
        result["version_id"] = version_id
        result["data_mart_id"] = data_mart_id
        return result

    # -----------------------------------------------------------------------
    # Connections
    # -----------------------------------------------------------------------

    async def list_connections(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        page: int = 1,
        page_size: int = 100,
        db_type: str | None = None,
        status: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        key = connections_key(project_id, version_id, lang, page, page_size, db_type, status)
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_list_connections",
            fetch=lambda: self._fetch_connections(
                project_id, version_id, lang, page, page_size, db_type, status
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_connections(
        self,
        project_id: int,
        version_id: int,
        language: str,
        page: int,
        page_size: int,
        db_type: str | None,
        status: str | None,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_connections(
                project_id,
                version_id,
                language,
                page=page,
                page_size=page_size,
                db_type=db_type,
                status=status,
            )
        return {
            "project_id": project_id,
            "version_id": version_id,
            "connections": [c.model_dump(by_alias=True) for c in resp.connections],
            "pagination": _pagination(resp.pagination),
        }

    async def get_connection(
        self,
        project_id: int,
        version_id: int,
        connection_id: int,
        language: str | None = None,
        include_db_schema: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=connection_key(project_id, version_id, connection_id, lang, include_db_schema),
            use_cache=use_cache,
            tool_name="df_get_connection",
            fetch=lambda: self._fetch_connection(
                project_id, version_id, connection_id, lang, include_db_schema
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_connection(
        self,
        project_id: int,
        version_id: int,
        connection_id: int,
        language: str,
        include_db_schema: bool,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_connection(
                project_id, version_id, connection_id, language, include_db_schema
            )
        return resp.model_dump(by_alias=True)

    async def get_connection_schema(
        self,
        project_id: int,
        version_id: int,
        connection_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=connection_schema_key(project_id, version_id, connection_id, lang),
            use_cache=use_cache,
            tool_name="df_get_connection_schema",
            fetch=lambda: self._fetch_connection_schema(
                project_id, version_id, connection_id, lang
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_connection_schema(
        self, project_id: int, version_id: int, connection_id: int, language: str
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_connection_schema(project_id, version_id, connection_id, language)
        return resp.model_dump(by_alias=True)

    # -----------------------------------------------------------------------
    # Dimension groups
    # -----------------------------------------------------------------------

    async def list_dimension_groups(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=dimension_groups_key(project_id, version_id, lang, page, page_size),
            use_cache=use_cache,
            tool_name="df_list_dimension_groups",
            fetch=lambda: self._fetch_dimension_groups(
                project_id, version_id, lang, page, page_size
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_dimension_groups(
        self, project_id: int, version_id: int, language: str, page: int, page_size: int
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_dimension_groups(
                project_id, version_id, language, page=page, page_size=page_size
            )
        return {
            "project_id": project_id,
            "version_id": version_id,
            "dimension_groups": [g.model_dump(by_alias=True) for g in resp.dimension_groups],
            "pagination": _pagination(resp.pagination),
        }

    async def get_dimension_group(
        self,
        project_id: int,
        version_id: int,
        dimension_group_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=dimension_group_key(project_id, version_id, dimension_group_id, lang),
            use_cache=use_cache,
            tool_name="df_get_dimension_group",
            fetch=lambda: self._fetch_dimension_group(
                project_id, version_id, dimension_group_id, lang
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_dimension_group(
        self, project_id: int, version_id: int, dimension_group_id: int, language: str
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_dimension_group(
                project_id, version_id, dimension_group_id, language
            )
        return resp.model_dump(by_alias=True)

    # -----------------------------------------------------------------------
    # Fact tables
    # -----------------------------------------------------------------------

    async def list_fact_tables(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=fact_tables_key(project_id, version_id, lang, page, page_size),
            use_cache=use_cache,
            tool_name="df_list_fact_tables",
            fetch=lambda: self._fetch_fact_tables(project_id, version_id, lang, page, page_size),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_fact_tables(
        self, project_id: int, version_id: int, language: str, page: int, page_size: int
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_fact_tables(
                project_id, version_id, language, page=page, page_size=page_size
            )
        return {
            "project_id": project_id,
            "version_id": version_id,
            "fact_tables": [t.model_dump(by_alias=True) for t in resp.fact_tables],
            "pagination": _pagination(resp.pagination),
        }

    async def get_fact_table(
        self,
        project_id: int,
        version_id: int,
        fact_table_id: int,
        language: str | None = None,
        include_dependencies: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=fact_table_key(project_id, version_id, fact_table_id, lang, include_dependencies),
            use_cache=use_cache,
            tool_name="df_get_fact_table",
            fetch=lambda: self._fetch_fact_table(
                project_id, version_id, fact_table_id, lang, include_dependencies
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_fact_table(
        self,
        project_id: int,
        version_id: int,
        fact_table_id: int,
        language: str,
        include_dependencies: bool,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_fact_table(
                project_id, version_id, fact_table_id, language, include_dependencies
            )
        return resp.model_dump(by_alias=True)

    # -----------------------------------------------------------------------
    # Relationships
    # -----------------------------------------------------------------------

    async def list_relationships(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        page: int = 1,
        page_size: int = 100,
        fact_table_id: int | None = None,
        dimension_group_id: int | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        key = relationships_key(
            project_id, version_id, lang, page, page_size, fact_table_id, dimension_group_id
        )
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_list_relationships",
            fetch=lambda: self._fetch_relationships(
                project_id, version_id, lang, page, page_size, fact_table_id, dimension_group_id
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_relationships(
        self,
        project_id: int,
        version_id: int,
        language: str,
        page: int,
        page_size: int,
        fact_table_id: int | None,
        dimension_group_id: int | None,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_relationships(
                project_id,
                version_id,
                language,
                page=page,
                page_size=page_size,
                fact_table_id=fact_table_id,
                dimension_group_id=dimension_group_id,
            )
        return {
            "project_id": project_id,
            "version_id": version_id,
            "relationships": [r.model_dump(by_alias=True) for r in resp.relationships],
            "pagination": _pagination(resp.pagination),
        }

    async def get_relationship(
        self,
        project_id: int,
        version_id: int,
        relationship_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=relationship_key(project_id, version_id, relationship_id, lang),
            use_cache=use_cache,
            tool_name="df_get_relationship",
            fetch=lambda: self._fetch_relationship(project_id, version_id, relationship_id, lang),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_relationship(
        self, project_id: int, version_id: int, relationship_id: int, language: str
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_relationship(project_id, version_id, relationship_id, language)
        return resp.model_dump(by_alias=True)

    # -----------------------------------------------------------------------
    # Project access and Git connections (read side)
    # -----------------------------------------------------------------------

    async def get_project_access(
        self, project_id: int, language: str | None = None, use_cache: bool = True
    ) -> dict[str, Any]:
        lang = self._lang(language)
        return await self._cached_fetch(
            key=project_access_key(project_id, lang),
            use_cache=use_cache,
            tool_name="df_get_project_access",
            fetch=lambda: self._fetch_project_access(project_id, lang),
            project_id=project_id,
        )

    async def _fetch_project_access(self, project_id: int, language: str) -> dict[str, Any]:
        async with self._new_client() as c:
            entries = await c.get_project_access(project_id, language)
        return {
            "project_id": project_id,
            "access": [e.model_dump(by_alias=True) for e in entries],
        }

    async def list_git_connections(
        self, page: int = 1, page_size: int = 100, use_cache: bool = True
    ) -> dict[str, Any]:
        return await self._cached_fetch(
            key=git_connections_key(page, page_size),
            use_cache=use_cache,
            tool_name="df_list_git_connections",
            fetch=lambda: self._fetch_git_connections(page, page_size),
        )

    async def _fetch_git_connections(self, page: int, page_size: int) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.list_git_connections(page=page, page_size=page_size)
        return {
            "git_connections": [g.model_dump(by_alias=False) for g in resp.git_connections],
            "pagination": _pagination(resp.pagination),
        }

    async def get_git_connection(
        self, connection_id: int, use_cache: bool = True
    ) -> dict[str, Any]:
        return await self._cached_fetch(
            key=git_connection_key(connection_id),
            use_cache=use_cache,
            tool_name="df_get_git_connection",
            fetch=lambda: self._fetch_git_connection(connection_id),
        )

    async def _fetch_git_connection(self, connection_id: int) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_git_connection(connection_id)
        return resp.model_dump(by_alias=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pagination(pagination: Any, fetched: int | None = None) -> dict[str, Any] | None:
    if pagination is None:
        return {"fetched": fetched} if fetched is not None else None
    data = pagination.model_dump(by_alias=False)
    if fetched is not None:
        data["fetched"] = fetched
    return data


def _is_last_page(pagination: Any, page: int, batch_size: int) -> bool:
    """Stop paging once the API says so, or when a short/empty page comes back."""
    if batch_size == 0:
        return True
    if pagination is None:
        return True
    total_pages = pagination.total_pages
    if total_pages is not None:
        return page >= total_pages
    return batch_size < _PAGE_SIZE


def _as_raw(kind: str, rows: list[Any]) -> list[Any]:
    """Re-hydrate raw entity models out of a cached (plain dict) snapshot."""
    from dataforge_mcp.dataforge.schemas import DimensionRaw, FactRaw, MeasureRaw

    model = {"measure": MeasureRaw, "dimension": DimensionRaw, "fact": FactRaw}[kind]
    return [row if not isinstance(row, dict) else model.model_validate(row) for row in rows]


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
