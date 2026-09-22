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


@pytest.mark.asyncio
async def test_invalidate_prefix_drops_a_key_family(cache: FileCacheStore) -> None:
    """Writes cannot enumerate the keys they affect, so they drop a whole prefix."""
    await cache.set("measures:392:948:ru:False", {"a": 1}, 60)
    await cache.set("measures:392:948:en:True", {"a": 2}, 60)
    await cache.set("measures:392:999:ru:False", {"a": 3}, 60)

    removed = await cache.invalidate_prefix("measures:392:948")

    assert removed == 2
    assert await cache.get("measures:392:948:ru:False") is None
    assert await cache.get("measures:392:948:en:True") is None
    # A different version is untouched.
    assert await cache.get("measures:392:999:ru:False") == {"a": 3}


@pytest.mark.asyncio
async def test_invalidate_prefix_also_removes_an_exact_key(cache: FileCacheStore) -> None:
    await cache.set("projects:1:100", {"a": 1}, 60)
    assert await cache.invalidate_prefix("projects") == 1
    assert await cache.get("projects:1:100") is None


@pytest.mark.asyncio
async def test_invalidate_prefix_on_empty_cache(cache: FileCacheStore) -> None:
    assert await cache.invalidate_prefix("measures:1:2") == 0
