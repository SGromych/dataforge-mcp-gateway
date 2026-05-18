"""Abstract cache store and cache entry model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CacheEntry(BaseModel):
    fetched_at: datetime
    ttl_seconds: int
    payload: Any


class CacheStore(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any | None: ...

    @abstractmethod
    async def get_last_known_good(self, key: str) -> Any | None: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> None: ...

    @abstractmethod
    async def invalidate(self, key: str) -> None: ...

    @abstractmethod
    async def is_healthy(self) -> bool: ...


# ---------------------------------------------------------------------------
# RMD API cache keys
# ---------------------------------------------------------------------------


def projects_key(page: int = 1, page_size: int = 100) -> str:
    return f"projects:{page}:{page_size}"


def versions_key(project_id: int, page: int = 1, page_size: int = 100) -> str:
    return f"versions:{project_id}:{page}:{page_size}"


def measures_key(project_id: int, version_id: int, language: str) -> str:
    return f"measures:{project_id}:{version_id}:{language}"


def dimensions_key(project_id: int, version_id: int, language: str) -> str:
    return f"dimensions:{project_id}:{version_id}:{language}"


def facts_key(project_id: int, version_id: int, language: str) -> str:
    return f"facts:{project_id}:{version_id}:{language}"


def rmd_key(project_id: int, version_id: int, language: str) -> str:
    return f"rmd:{project_id}:{version_id}:{language}"


# ---------------------------------------------------------------------------
# DF API cache keys
# ---------------------------------------------------------------------------


def data_marts_key(
    project_id: int,
    version_id: int,
    language: str,
    page: int = 1,
    page_size: int = 100,
    type: str | None = None,
    merge_type: str | None = None,
    search: str | None = None,
) -> str:
    return f"data_marts:{project_id}:{version_id}:{language}:{page}:{page_size}:{type}:{merge_type}:{search}"


def data_mart_key(project_id: int, version_id: int, data_mart_id: int, language: str) -> str:
    return f"data_mart:{project_id}:{version_id}:{data_mart_id}:{language}"


def connections_key(
    project_id: int,
    version_id: int,
    language: str,
    page: int = 1,
    page_size: int = 100,
    db_type: str | None = None,
    status: str | None = None,
) -> str:
    return f"connections:{project_id}:{version_id}:{language}:{page}:{page_size}:{db_type}:{status}"


def connection_key(project_id: int, version_id: int, connection_id: int, language: str) -> str:
    return f"connection:{project_id}:{version_id}:{connection_id}:{language}"


def dimension_groups_key(
    project_id: int, version_id: int, language: str, page: int = 1, page_size: int = 100
) -> str:
    return f"dimension_groups:{project_id}:{version_id}:{language}:{page}:{page_size}"


def dimension_group_key(
    project_id: int, version_id: int, dimension_group_id: int, language: str
) -> str:
    return f"dimension_group:{project_id}:{version_id}:{dimension_group_id}:{language}"


def fact_tables_key(
    project_id: int, version_id: int, language: str, page: int = 1, page_size: int = 100
) -> str:
    return f"fact_tables:{project_id}:{version_id}:{language}:{page}:{page_size}"


def fact_table_key(project_id: int, version_id: int, fact_table_id: int, language: str) -> str:
    return f"fact_table:{project_id}:{version_id}:{fact_table_id}:{language}"


def relationships_key(
    project_id: int,
    version_id: int,
    language: str,
    page: int = 1,
    page_size: int = 100,
    fact_table_id: int | None = None,
    dimension_group_id: int | None = None,
) -> str:
    return f"relationships:{project_id}:{version_id}:{language}:{page}:{page_size}:{fact_table_id}:{dimension_group_id}"


def relationship_key(project_id: int, version_id: int, relationship_id: int, language: str) -> str:
    return f"relationship:{project_id}:{version_id}:{relationship_id}:{language}"


def consolidated_rmd_key(project_id: int, version_id: int, language: str) -> str:
    return f"consolidated_rmd:{project_id}:{version_id}:{language}"
