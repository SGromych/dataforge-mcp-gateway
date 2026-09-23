"""File-based cache store implementation."""

from __future__ import annotations

import asyncio
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dataforge_mcp.logging import get_logger

from .store import CacheEntry, CacheStore

logger = get_logger(__name__)


class FileCacheStore(CacheStore):
    def __init__(self, cache_dir: str) -> None:
        self._cache_dir = Path(cache_dir)

    def _key_to_path(self, key: str) -> Path:
        parts = key.split(":")
        return self._cache_dir / "/".join(parts[:-1]) / f"{parts[-1]}.json"

    def _read_entry(self, path: Path) -> CacheEntry | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CacheEntry.model_validate(data)
        except Exception:
            return None

    def _write_entry(self, path: Path, entry: CacheEntry) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            entry.model_dump_json(indent=2),
            encoding="utf-8",
        )

    async def get(self, key: str) -> Any | None:
        path = self._key_to_path(key)
        entry = await asyncio.to_thread(self._read_entry, path)
        if entry is None:
            return None
        elapsed = (datetime.now(UTC) - entry.fetched_at).total_seconds()
        if elapsed > entry.ttl_seconds:
            return None
        return entry.payload

    async def get_last_known_good(self, key: str) -> Any | None:
        path = self._key_to_path(key)
        entry = await asyncio.to_thread(self._read_entry, path)
        if entry is None:
            return None
        return entry.payload

    async def set(self, key: str, value: Any, ttl: int) -> None:
        path = self._key_to_path(key)
        entry = CacheEntry(
            fetched_at=datetime.now(UTC),
            ttl_seconds=ttl,
            payload=value,
        )
        await asyncio.to_thread(self._write_entry, path, entry)

    async def invalidate_prefix(self, prefix: str) -> int:
        """Drop a whole key family.

        Keys map one-to-one onto the directory tree, so a prefix is simply a directory
        (plus, when the prefix is itself a complete key, the matching ``.json`` file).
        """
        parts = prefix.split(":")
        directory = self._cache_dir / "/".join(parts)
        leaf = self._cache_dir / "/".join(parts[:-1]) / f"{parts[-1]}.json"

        def _delete() -> int:
            removed = 0
            if directory.is_dir():
                removed = sum(1 for _ in directory.rglob("*.json"))
                shutil.rmtree(directory, ignore_errors=True)
            if leaf.is_file():
                leaf.unlink(missing_ok=True)
                removed += 1
            return removed

        return await asyncio.to_thread(_delete)

    async def invalidate(self, key: str) -> None:
        path = self._key_to_path(key)

        def _delete() -> None:
            if path.exists():
                path.unlink()

        await asyncio.to_thread(_delete)

    async def is_healthy(self) -> bool:
        def _check() -> bool:
            try:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
                return self._cache_dir.is_dir()
            except Exception:
                return False

        return await asyncio.to_thread(_check)
