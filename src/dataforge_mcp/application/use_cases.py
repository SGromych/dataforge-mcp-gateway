"""Use-case orchestration: client + cache + normalizer."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from dataforge_mcp.cache.store import (
    CacheStore,
    connection_key,
    connections_key,
    consolidated_rmd_key,
    data_mart_key,
    data_marts_key,
    dimension_group_key,
    dimension_groups_key,
    dimensions_key,
    fact_table_key,
    fact_tables_key,
    facts_key,
    measures_key,
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
from dataforge_mcp.semantic.models import (
    CanonicalProject,
    CanonicalVersion,
)
from dataforge_mcp.semantic.normalizer import (
    build_semantic_context,
    normalize_dimensions,
    normalize_facts,
    normalize_measures,
)

logger = get_logger(__name__)


class SemanticService:
    def __init__(
        self,
        client: DataForgeClient,
        cache: CacheStore,
        settings: Settings,
    ) -> None:
        self.client = client
        self.cache = cache
        self.settings = settings

    async def check_health(self) -> dict[str, Any]:
        cache_ok = await self.cache.is_healthy()
        api_ok = True
        try:
            async with DataForgeClient(
                base_url=self.client.base_url,
                api_key=self.client._api_key,
            ) as c:
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
    # RMD API use cases
    # -----------------------------------------------------------------------

    async def list_projects(
        self,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        key = projects_key(page, page_size)
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_list_projects",
            fetch=lambda: self._fetch_projects(page, page_size),
        )

    async def _fetch_projects(self, page: int, page_size: int) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_projects(page=page, page_size=page_size)
        projects = [
            CanonicalProject(id=p.id, name=p.name, description=p.description).model_dump()
            for p in resp.projects
        ]
        return {
            "projects": projects,
            "pagination": resp.pagination.model_dump(by_alias=False),
        }

    async def list_versions(
        self,
        project_id: int,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        key = versions_key(project_id, page, page_size)
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_list_versions",
            fetch=lambda: self._fetch_versions(project_id, page, page_size),
            project_id=project_id,
        )

    async def _fetch_versions(self, project_id: int, page: int, page_size: int) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_versions(project_id, page=page, page_size=page_size)
        versions = [
            CanonicalVersion(id=v.id, name=v.name, is_global=v.is_global).model_dump()
            for v in resp.versions
        ]
        return {
            "project_id": project_id,
            "versions": versions,
            "pagination": resp.pagination.model_dump(by_alias=False),
        }

    async def get_measures(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        include_sql: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = measures_key(project_id, version_id, lang, include_sql)
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_get_measures",
            fetch=lambda: self._fetch_measures(project_id, version_id, lang, include_sql),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_measures(
        self, project_id: int, version_id: int, language: str, include_sql: bool = False
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_measures(project_id, version_id, language, include_sql)
        measures = normalize_measures(resp.measures)
        return {
            "project_id": project_id,
            "version_id": version_id,
            "measures": [m.model_dump() for m in measures],
        }

    async def get_dimensions(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = dimensions_key(project_id, version_id, lang)
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_get_dimensions",
            fetch=lambda: self._fetch_dimensions(project_id, version_id, lang),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_dimensions(
        self, project_id: int, version_id: int, language: str
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_dimensions(project_id, version_id, language)
        dimensions = normalize_dimensions(resp.dimensions)
        return {
            "project_id": project_id,
            "version_id": version_id,
            "dimensions": [d.model_dump() for d in dimensions],
        }

    async def get_facts(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = facts_key(project_id, version_id, lang)
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_get_facts",
            fetch=lambda: self._fetch_facts(project_id, version_id, lang),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_facts(
        self, project_id: int, version_id: int, language: str
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_facts(project_id, version_id, language)
        facts = normalize_facts(resp.facts)
        return {
            "project_id": project_id,
            "version_id": version_id,
            "facts": [f.model_dump() for f in facts],
        }

    async def get_rmd(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        use_cache: bool = True,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = rmd_key(project_id, version_id, lang)
        result = await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_get_rmd",
            fetch=lambda: self._fetch_rmd(project_id, version_id, lang),
            project_id=project_id,
            version_id=version_id,
        )
        if not include_raw:
            for m in result.get("measures", []):
                m.pop("raw", None)
            for d in result.get("dimensions", []):
                d.pop("raw", None)
            for f in result.get("facts", []):
                f.pop("raw", None)
        return result

    async def _fetch_rmd(self, project_id: int, version_id: int, language: str) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_rmd(project_id, version_id, language)
        measures = normalize_measures(resp.measures)
        dimensions = normalize_dimensions(resp.dimensions)
        facts = normalize_facts(resp.facts)
        context = build_semantic_context(
            project=CanonicalProject(id=project_id, name="", description=None),
            version=CanonicalVersion(id=version_id, name="", is_global=False),
            measures=measures,
            dimensions=dimensions,
            facts=facts,
        )
        return context.model_dump()

    async def refresh_cache(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        keys = [
            rmd_key(project_id, version_id, lang),
            measures_key(project_id, version_id, lang),
            dimensions_key(project_id, version_id, lang),
            facts_key(project_id, version_id, lang),
        ]
        for key in keys:
            await self.cache.invalidate(key)
        await self.get_rmd(project_id, version_id, lang, use_cache=False, include_raw=True)
        return {
            "status": "refreshed",
            "cache_key": keys[0],
            "fetched_at": datetime.now(UTC).isoformat(),
        }

    # -----------------------------------------------------------------------
    # DF API use cases
    # -----------------------------------------------------------------------

    async def list_data_marts(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        page: int = 1,
        page_size: int = 100,
        type: str | None = None,
        merge_type: str | None = None,
        search: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = data_marts_key(
            project_id, version_id, lang, page, page_size, type, merge_type, search
        )
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_list_data_marts",
            fetch=lambda: self._fetch_data_marts(
                project_id, version_id, lang, page, page_size, type, merge_type, search
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
        type: str | None,
        merge_type: str | None,
        search: str | None,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_data_marts(
                project_id, version_id, language, page, page_size, type, merge_type, search
            )
        return {
            "project_id": project_id,
            "version_id": version_id,
            "data_marts": [dm.model_dump(by_alias=False) for dm in resp.data_marts],
            "pagination": resp.pagination.model_dump(by_alias=False) if resp.pagination else None,
        }

    async def get_data_mart(
        self,
        project_id: int,
        version_id: int,
        data_mart_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = data_mart_key(project_id, version_id, data_mart_id, lang)
        return await self._cached_fetch(
            key=key,
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
        return resp.model_dump(by_alias=False)

    async def get_data_mart_view(
        self,
        project_id: int,
        version_id: int,
        data_mart_id: int,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_data_mart_view(project_id, version_id, data_mart_id)
        return resp.model_dump(by_alias=False)

    async def generate_sql(
        self,
        project_id: int,
        version_id: int,
        data_mart_id: int,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.generate_sql(project_id, version_id, data_mart_id, limit, offset)
        return resp.model_dump(by_alias=False)

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
        lang = language or self.settings.default_language
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
                project_id, version_id, language, page, page_size, db_type, status
            )
        return {
            "project_id": project_id,
            "version_id": version_id,
            "connections": [conn.model_dump(by_alias=False) for conn in resp.connections],
            "pagination": resp.pagination.model_dump(by_alias=False) if resp.pagination else None,
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
        lang = language or self.settings.default_language
        key = connection_key(project_id, version_id, connection_id, lang)
        return await self._cached_fetch(
            key=key,
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
        return resp.model_dump(by_alias=False)

    async def get_connection_schema(
        self,
        project_id: int,
        version_id: int,
        connection_id: int,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_connection_schema(project_id, version_id, connection_id)
        return resp.model_dump(by_alias=False)

    async def list_dimension_groups(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = dimension_groups_key(project_id, version_id, lang, page, page_size)
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_list_dimension_groups",
            fetch=lambda: self._fetch_dimension_groups(
                project_id, version_id, lang, page, page_size
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_dimension_groups(
        self,
        project_id: int,
        version_id: int,
        language: str,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_dimension_groups(project_id, version_id, language, page, page_size)
        return {
            "project_id": project_id,
            "version_id": version_id,
            "dimension_groups": [dg.model_dump(by_alias=False) for dg in resp.dimension_groups],
            "pagination": resp.pagination.model_dump(by_alias=False) if resp.pagination else None,
        }

    async def get_dimension_group(
        self,
        project_id: int,
        version_id: int,
        dimension_group_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = dimension_group_key(project_id, version_id, dimension_group_id, lang)
        return await self._cached_fetch(
            key=key,
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
        return resp.model_dump(by_alias=False)

    async def list_fact_tables(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        page: int = 1,
        page_size: int = 100,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = fact_tables_key(project_id, version_id, lang, page, page_size)
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_list_fact_tables",
            fetch=lambda: self._fetch_fact_tables(project_id, version_id, lang, page, page_size),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_fact_tables(
        self,
        project_id: int,
        version_id: int,
        language: str,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_fact_tables(project_id, version_id, language, page, page_size)
        return {
            "project_id": project_id,
            "version_id": version_id,
            "fact_tables": [ft.model_dump(by_alias=False) for ft in resp.fact_tables],
            "pagination": resp.pagination.model_dump(by_alias=False) if resp.pagination else None,
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
        lang = language or self.settings.default_language
        key = fact_table_key(project_id, version_id, fact_table_id, lang, include_dependencies)
        return await self._cached_fetch(
            key=key,
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
        return resp.model_dump(by_alias=False)

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
        lang = language or self.settings.default_language
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
                page,
                page_size,
                fact_table_id,
                dimension_group_id,
            )
        return {
            "project_id": project_id,
            "version_id": version_id,
            "relationships": [r.model_dump(by_alias=False) for r in resp.relationships],
            "pagination": resp.pagination.model_dump(by_alias=False) if resp.pagination else None,
        }

    async def get_relationship(
        self,
        project_id: int,
        version_id: int,
        relationship_id: int,
        language: str | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = relationship_key(project_id, version_id, relationship_id, lang)
        return await self._cached_fetch(
            key=key,
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
        return resp.model_dump(by_alias=False)

    async def get_consolidated_rmd(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
        include_sql: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = consolidated_rmd_key(project_id, version_id, lang, include_sql)
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_get_consolidated_rmd",
            fetch=lambda: self._fetch_consolidated_rmd(project_id, version_id, lang, include_sql),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_consolidated_rmd(
        self,
        project_id: int,
        version_id: int,
        language: str,
        include_sql: bool = False,
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_consolidated_rmd(project_id, version_id, language, include_sql)
        return resp.model_dump(by_alias=False)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _new_client(self) -> DataForgeClient:
        return DataForgeClient(
            base_url=self.client.base_url,
            api_key=self.client._api_key,
        )

    async def _cached_fetch(
        self,
        key: str,
        use_cache: bool,
        tool_name: str,
        fetch: Any,
        **log_ctx: Any,
    ) -> dict[str, Any]:
        start = time.monotonic()
        if use_cache:
            cached = await self.cache.get(key)
            if cached is not None:
                elapsed = (time.monotonic() - start) * 1000
                await logger.ainfo(
                    "cache_hit",
                    tool_name=tool_name,
                    cache_hit=True,
                    response_time_ms=round(elapsed, 2),
                    **log_ctx,
                )
                return cached

        try:
            result = await fetch()
        except DataForgeError:
            lkg = await self.cache.get_last_known_good(key)
            if lkg is not None:
                await logger.awarning(
                    "using_last_known_good",
                    tool_name=tool_name,
                    **log_ctx,
                )
                return lkg
            raise

        await self.cache.set(key, result, self.settings.cache_ttl_seconds)
        elapsed = (time.monotonic() - start) * 1000
        await logger.ainfo(
            "cache_miss",
            tool_name=tool_name,
            cache_hit=False,
            response_time_ms=round(elapsed, 2),
            **log_ctx,
        )
        return result
