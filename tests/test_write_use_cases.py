"""Write use cases: cache invalidation, idempotency keys and local validation."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from dataforge_mcp.application.invalidation import WriteScope, prefixes_for
from dataforge_mcp.application.use_cases import SemanticService
from dataforge_mcp.cache.file_store import FileCacheStore
from dataforge_mcp.cache.store import measures_key, rmd_key
from dataforge_mcp.config import Settings
from dataforge_mcp.dataforge.client import DataForgeClient
from dataforge_mcp.errors import DataForgeError, ErrorCode
from tests.fixtures import api_v2 as fx

BASE = "https://api.test.example.com"
PFX = f"{BASE}/df-api/v2/projects/392/versions/948"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        dataforge_base_url=BASE,
        dataforge_api_key="test-api-key-12345",
        default_language="ru",
        cache_dir=str(tmp_path / "cache"),
        cache_ttl_seconds=60,
    )


@pytest.fixture
def service(settings: Settings, tmp_path: Path) -> SemanticService:
    client = DataForgeClient(
        base_url=settings.dataforge_base_url,
        api_key=settings.dataforge_api_key,
        max_retries=1,
    )
    return SemanticService(client, FileCacheStore(str(tmp_path / "cache")), settings)


# ---------------------------------------------------------------------------
# Invalidation scopes
# ---------------------------------------------------------------------------


def test_version_scope_covers_every_version_family() -> None:
    prefixes = prefixes_for(WriteScope.VERSION, 392, 948)
    assert "measures:392:948" in prefixes
    assert "rmd:392:948" in prefixes
    assert "fact_table:392:948" in prefixes
    assert all(p.endswith(":392:948") for p in prefixes)


def test_project_scope_includes_listings() -> None:
    prefixes = prefixes_for(WriteScope.PROJECT, 392)
    assert "projects" in prefixes
    assert "versions:392" in prefixes
    assert "measures:392" in prefixes
    assert "project_access:392" in prefixes


def test_global_and_git_scopes() -> None:
    assert prefixes_for(WriteScope.GLOBAL) == ["projects"]
    assert prefixes_for(WriteScope.GIT) == ["git_connections", "git_connection"]


def test_version_scope_without_ids_is_empty() -> None:
    assert prefixes_for(WriteScope.VERSION) == []


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_write_invalidates_cached_reads(service: SemanticService) -> None:
    """After a write, a cached read of the same version must not be served again."""
    measures_route = respx.get(f"{PFX}/measures").mock(
        return_value=httpx.Response(200, json=fx.MEASURES_200)
    )
    respx.post(f"{PFX}/measures").mock(
        return_value=httpx.Response(201, json=fx.MEASURE_CREATED_201)
    )

    await service.get_measures(392, 948)
    assert await service.cache.get(measures_key(392, 948, "ru", False)) is not None

    result = await service.write_measure(
        392, 948, mode="create", measure_name="Total revenue", measure_type="Base"
    )

    assert result["status"] == "created"
    assert await service.cache.get(measures_key(392, 948, "ru", False)) is None
    assert any(p.startswith("measures:") for p in result["cache_invalidated"])

    await service.get_measures(392, 948)
    assert measures_route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_write_generates_idempotency_key(service: SemanticService) -> None:
    route = respx.post(f"{PFX}/measures").mock(
        return_value=httpx.Response(201, json=fx.MEASURE_CREATED_201)
    )
    result = await service.write_measure(
        392, 948, measure_name="Total revenue", measure_type="Base"
    )
    sent = route.calls[0].request.headers["Idempotency-Key"]
    assert sent == result["idempotency_key"]


@respx.mock
@pytest.mark.asyncio
async def test_partial_bulk_is_reported_as_partial(service: SemanticService) -> None:
    """207 must never be flattened into success."""
    respx.post(f"{PFX}/measures/bulk").mock(
        return_value=httpx.Response(207, json=fx.BULK_PARTIAL_207)
    )
    result = await service.bulk_write_measures(
        392,
        948,
        measures=[
            {"measure_name": "A", "measure_type": "Base"},
            {"measure_name": "B", "measure_type": "Base"},
        ],
    )

    assert result["status"] == "partial"
    assert result["http_status"] == 207
    assert result["failed"][0]["error"]["code"] == "duplicate_name"
    assert len(result["succeeded"]) == 1


@respx.mock
@pytest.mark.asyncio
async def test_delete_reports_deleted(service: SemanticService) -> None:
    respx.delete(f"{PFX}/measures/1000").mock(return_value=httpx.Response(204))
    result = await service.delete_measure(392, 948, 1000)
    assert result["status"] == "deleted"
    assert result["result"] is None


@respx.mock
@pytest.mark.asyncio
async def test_failed_write_never_returns_stale_cache(service: SemanticService) -> None:
    """Last-known-good is for reads. Returning it for a write would fake success."""
    respx.get(f"{PFX}/measures").mock(return_value=httpx.Response(200, json=fx.MEASURES_200))
    await service.get_measures(392, 948)

    respx.post(f"{PFX}/measures").mock(
        return_value=httpx.Response(409, json=fx.ERR_409_DUPLICATE_NAME)
    )
    with pytest.raises(DataForgeError) as exc_info:
        await service.write_measure(392, 948, measure_name="Total revenue", measure_type="Base")

    assert exc_info.value.code is ErrorCode.DATAFORGE_DUPLICATE_NAME
    # The pre-existing cache entry stays untouched — the write did not happen.
    assert await service.cache.get(measures_key(392, 948, "ru", False)) is not None


# ---------------------------------------------------------------------------
# Local validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_field_rejected_locally(service: SemanticService) -> None:
    """Strict bodies: catching the typo here saves a round-trip to a 400."""
    with pytest.raises(DataForgeError) as exc_info:
        await service.write_measure(392, 948, measure_name="A", meassure_type="Base")

    error = exc_info.value
    assert error.code is ErrorCode.DATAFORGE_VALIDATION_FAILED
    assert error.field_errors[0]["code"] == "unknown_field"


@pytest.mark.asyncio
async def test_create_requires_mandatory_fields(service: SemanticService) -> None:
    with pytest.raises(DataForgeError) as exc_info:
        await service.write_measure(392, 948, measure_name="A")
    assert exc_info.value.code is ErrorCode.DATAFORGE_MISSING_REQUIRED_FIELD
    assert exc_info.value.field_errors == [{"field": "measure_type", "code": "missing_field"}]


@pytest.mark.asyncio
async def test_replace_requires_target_id(service: SemanticService) -> None:
    with pytest.raises(DataForgeError) as exc_info:
        await service.write_measure(
            392, 948, mode="replace", measure_name="A", measure_type="Base"
        )
    assert exc_info.value.code is ErrorCode.DATAFORGE_MISSING_REQUIRED_FIELD


@pytest.mark.asyncio
async def test_update_needs_no_mandatory_fields(service: SemanticService) -> None:
    """PATCH changes only what it carries, so nothing is required."""
    with respx.mock:
        respx.patch(f"{PFX}/measures/1000").mock(
            return_value=httpx.Response(200, json=fx.MEASURE_CREATED_201)
        )
        result = await service.write_measure(
            392, 948, mode="update", measure_id=1000, comment="note"
        )
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_body_id_must_match_path_id(service: SemanticService) -> None:
    with pytest.raises(DataForgeError) as exc_info:
        await service.write_measure(392, 948, mode="update", measure_id=1000, id="999")
    assert exc_info.value.code is ErrorCode.DATAFORGE_ID_MISMATCH


@pytest.mark.asyncio
async def test_read_object_can_be_sent_back(service: SemanticService) -> None:
    """A row read from the API carries its own id; sending it back must be accepted."""
    with respx.mock:
        respx.patch(f"{PFX}/measures/1000").mock(
            return_value=httpx.Response(200, json=fx.MEASURE_CREATED_201)
        )
        result = await service.write_measure(
            392,
            948,
            mode="update",
            measure_id=1000,
            id="1000",
            measure_name="Total revenue",
            measure_type="Base",
        )
    assert result["http_status"] == 200


# ---------------------------------------------------------------------------
# refresh_cache
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_refresh_cache_clears_the_whole_version(service: SemanticService) -> None:
    respx.get(f"{PFX}/measures").mock(return_value=httpx.Response(200, json=fx.MEASURES_200))
    respx.get(f"{PFX}/data-marts").mock(return_value=httpx.Response(200, json=fx.DATA_MARTS_200))
    respx.get(f"{PFX}/rmd").mock(return_value=httpx.Response(200, json=fx.RMD_EXPORT_200))

    await service.get_measures(392, 948)
    await service.list_data_marts(392, 948)
    assert await service.cache.get(measures_key(392, 948, "ru", False)) is not None

    result = await service.refresh_cache(392, 948)

    assert result["status"] == "refreshed"
    assert result["entries_removed"] >= 2
    assert await service.cache.get(measures_key(392, 948, "ru", False)) is None
    # The RMD snapshot is re-fetched, so its entry exists again.
    assert await service.cache.get(rmd_key(392, 948, "ru")) is not None
