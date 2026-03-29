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


def projects_key(page: int = 1, page_size: int = 100) -> str:
    return f"projects:{page}:{page_size}"


def versions_key(project_id: int, page: int = 1, page_size: int = 100) -> str:
    return f"versions:{project_id}:{page}:{page_size}"


def measures_key(project_id: int, version_id: int, language: str) -> str:
    return f"measures:{project_id}:{version_id}:{language}"


def dimensions_key(project_id: int, version_id: int, language: str) -> str:
    return f"dimensions:{project_id}:{version_id}:{language}"


def rmd_key(project_id: int, version_id: int, language: str) -> str:
    return f"rmd:{project_id}:{version_id}:{language}"
