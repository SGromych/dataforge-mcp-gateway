"""Use-case orchestration: client + cache + normalizer."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from dataforge_mcp.cache.store import (
    CacheStore,
    dimensions_key,
    measures_key,
    projects_key,
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

    async def _fetch_versions(
        self, project_id: int, page: int, page_size: int
    ) -> dict[str, Any]:
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
        use_cache: bool = True,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = measures_key(project_id, version_id, lang)
        return await self._cached_fetch(
            key=key,
            use_cache=use_cache,
            tool_name="df_get_measures",
            fetch=lambda: self._fetch_measures(project_id, version_id, lang),
            project_id=project_id,
            version_id=version_id,
        )

    async def _fetch_measures(
        self, project_id: int, version_id: int, language: str
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_measures(project_id, version_id, language)
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
        return result

    async def _fetch_rmd(
        self, project_id: int, version_id: int, language: str
    ) -> dict[str, Any]:
        async with self._new_client() as c:
            resp = await c.get_rmd(project_id, version_id, language)
        measures = normalize_measures(resp.measures)
        dimensions = normalize_dimensions(resp.dimensions)
        context = build_semantic_context(
            project=CanonicalProject(id=project_id, name="", description=None),
            version=CanonicalVersion(id=version_id, name="", is_global=False),
            measures=measures,
            dimensions=dimensions,
        )
        return context.model_dump()

    async def refresh_cache(
        self,
        project_id: int,
        version_id: int,
        language: str | None = None,
    ) -> dict[str, Any]:
        lang = language or self.settings.default_language
        key = rmd_key(project_id, version_id, lang)
        await self.cache.invalidate(key)
        await self.get_rmd(
            project_id, version_id, lang, use_cache=False, include_raw=True
        )
        return {
            "status": "refreshed",
            "cache_key": key,
            "fetched_at": datetime.now(UTC).isoformat(),
        }

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
