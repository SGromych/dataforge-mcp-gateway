"""Tests for the file-based cache store."""

from pathlib import Path

import pytest

from dataforge_mcp.cache.file_store import FileCacheStore


@pytest.fixture
def cache(tmp_path: Path) -> FileCacheStore:
    return FileCacheStore(str(tmp_path / "cache"))


@pytest.mark.asyncio
async def test_set_and_get(cache: FileCacheStore) -> None:
    await cache.set("measures:1:2:ru", {"data": "test"}, ttl=3600)
    result = await cache.get("measures:1:2:ru")
    assert result == {"data": "test"}


@pytest.mark.asyncio
async def test_ttl_expired(cache: FileCacheStore) -> None:
    await cache.set("measures:1:2:ru", {"data": "test"}, ttl=0)
    result = await cache.get("measures:1:2:ru")
    assert result is None


@pytest.mark.asyncio
async def test_last_known_good_after_ttl(cache: FileCacheStore) -> None:
    await cache.set("measures:1:2:ru", {"data": "stale"}, ttl=0)
    result = await cache.get_last_known_good("measures:1:2:ru")
    assert result == {"data": "stale"}


@pytest.mark.asyncio
async def test_corrupted_json(cache: FileCacheStore, tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    file_path = cache_dir / "measures" / "1" / "2" / "ru.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("not valid json{{{", encoding="utf-8")
    result = await cache.get("measures:1:2:ru")
    assert result is None


@pytest.mark.asyncio
async def test_invalidate(cache: FileCacheStore) -> None:
    await cache.set("measures:1:2:ru", {"data": "test"}, ttl=3600)
    await cache.invalidate("measures:1:2:ru")
    result = await cache.get("measures:1:2:ru")
    assert result is None


@pytest.mark.asyncio
async def test_nonexistent_key(cache: FileCacheStore) -> None:
    result = await cache.get("measures:999:999:en")
    assert result is None


@pytest.mark.asyncio
async def test_is_healthy(cache: FileCacheStore) -> None:
    assert await cache.is_healthy() is True
