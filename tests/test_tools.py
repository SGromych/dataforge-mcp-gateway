"""Tests for MCP tools via SemanticService with mocked HTTP."""

from pathlib import Path

import httpx
import pytest
import respx

from dataforge_mcp.application.use_cases import SemanticService
from dataforge_mcp.cache.file_store import FileCacheStore
from dataforge_mcp.config import Settings
from dataforge_mcp.dataforge.client import DataForgeClient
from dataforge_mcp.errors import ErrorCode

BASE = "https://api.test.example.com"

PROJECTS_RESPONSE = {
    "projects": [
        {"id": 392, "name": "Fashion Retail", "description": "Fashion project"},
    ],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

VERSIONS_RESPONSE = {
    "versions": [{"id": 948, "name": "Global Version", "is_global": True}],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

MEASURES_RESPONSE = {
    "measures": [
        {
            "row_number": "1",
            "group": "Sales",
            "block": "Revenue",
            "measure_name": "Total Revenue",
            "measure_description": "All revenue",
            "data_type": "Numeric",
            "measure_type": "Sum",
            "formula": "[Revenue]",
            "connected_source": {"database": "Sales DB", "table": "sales_table"},
            "status": "Active",
            "required": True,
            "visibility": "Public",
        }
    ],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

DIMENSIONS_RESPONSE = {
    "dimensions": [
        {
            "row_number": "1",
            "group": "Sales",
            "block": "Customer",
            "dimension_name": "Customer ID",
            "dimension_description": "Unique ID",
            "dimension_group": "Customer Attributes",
            "data_type": "String",
            "connected_source": {"db": 161, "table": "customers", "column": "CompanyName"},
            "status": "Active",
            "required": True,
            "visibility": "Public",
        }
    ],
    "pagination": {"total": 1, "page": 1, "pageSize": 50, "totalPages": 1},
}

RMD_RESPONSE = {
    "measures": MEASURES_RESPONSE["measures"],
    "dimensions": DIMENSIONS_RESPONSE["dimensions"],
    "pagination": {
        "measures": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
        "dimensions": {"total": 1, "page": 1, "pageSize": 50, "totalPages": 1},
    },
}


@pytest.fixture
def settings() -> Settings:
    return Settings(
        dataforge_base_url=BASE,
        dataforge_api_key="test-key",
        cache_ttl_seconds=60,
        log_level="DEBUG",
    )


@pytest.fixture
def service(settings: Settings, tmp_path: Path) -> SemanticService:
    client = DataForgeClient(base_url=BASE, api_key=settings.dataforge_api_key)
    cache = FileCacheStore(str(tmp_path / "cache"))
    return SemanticService(client=client, cache=cache, settings=settings)


@respx.mock
@pytest.mark.asyncio
async def test_health_ok(service: SemanticService) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(200, json=PROJECTS_RESPONSE)
    )
    result = await service.check_health()
    assert result["server_status"] == "ok"
    assert result["product_api_status"] == "ok"
    assert result["cache_status"] == "ok"


@respx.mock
@pytest.mark.asyncio
async def test_health_api_unavailable(service: SemanticService) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    result = await service.check_health()
    assert result["product_api_status"] == "unavailable"


@respx.mock
@pytest.mark.asyncio
async def test_list_projects(service: SemanticService) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(200, json=PROJECTS_RESPONSE)
    )
    result = await service.list_projects()
    assert len(result["projects"]) == 1
    assert result["projects"][0]["name"] == "Fashion Retail"


@respx.mock
@pytest.mark.asyncio
async def test_get_measures_normalized(service: SemanticService) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects/392/versions/948/measures").mock(
        return_value=httpx.Response(200, json=MEASURES_RESPONSE)
    )
    result = await service.get_measures(392, 948)
    m = result["measures"][0]
    assert m["name"] == "Total Revenue"
    assert "measure_name" not in m  # normalized away at top level
    assert m["connected_source"]["db"] == "Sales DB"


@respx.mock
@pytest.mark.asyncio
async def test_get_rmd(service: SemanticService) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=RMD_RESPONSE)
    )
    result = await service.get_rmd(392, 948)
    assert result["stats"]["measure_count"] == 1
    assert result["stats"]["dimension_count"] == 1
    assert result["measures"][0]["name"] == "Total Revenue"
    assert result["dimensions"][0]["name"] == "Customer ID"
    # raw should be stripped by default
    assert "raw" not in result["measures"][0]


@respx.mock
@pytest.mark.asyncio
async def test_get_rmd_with_raw(service: SemanticService) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=RMD_RESPONSE)
    )
    result = await service.get_rmd(392, 948, include_raw=True)
    assert "raw" in result["measures"][0]


@respx.mock
@pytest.mark.asyncio
async def test_refresh_cache(service: SemanticService) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=RMD_RESPONSE)
    )
    result = await service.refresh_cache(392, 948)
    assert result["status"] == "refreshed"
    assert "rmd:392:948:ru" in result["cache_key"]


@respx.mock
@pytest.mark.asyncio
async def test_error_401(service: SemanticService) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(401, text='{"error": "API_KEY.INVALID_KEY"}')
    )
    from dataforge_mcp.errors import DataForgeError

    with pytest.raises(DataForgeError) as exc_info:
        await service.list_projects(use_cache=False)
    assert exc_info.value.code == ErrorCode.DATAFORGE_API_KEY_INVALID


@respx.mock
@pytest.mark.asyncio
async def test_cache_hit(service: SemanticService) -> None:
    route = respx.get(f"{BASE}/rmd-api/v1/projects")
    route.mock(return_value=httpx.Response(200, json=PROJECTS_RESPONSE))

    # First call — cache miss
    result1 = await service.list_projects()
    assert route.call_count == 1

    # Second call — cache hit
    result2 = await service.list_projects()
    assert route.call_count == 1  # no additional HTTP call
    assert result1 == result2


@respx.mock
@pytest.mark.asyncio
async def test_integration_flow(service: SemanticService) -> None:
    """Integration test: projects → versions → rmd."""
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(200, json=PROJECTS_RESPONSE)
    )
    respx.get(f"{BASE}/rmd-api/v1/projects/392/versions").mock(
        return_value=httpx.Response(200, json=VERSIONS_RESPONSE)
    )
    respx.get(f"{BASE}/rmd-api/v1/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=RMD_RESPONSE)
    )

    projects = await service.list_projects()
    project_id = projects["projects"][0]["id"]
    assert project_id == 392

    versions = await service.list_versions(project_id)
    version_id = versions["versions"][0]["id"]
    assert version_id == 948

    rmd = await service.get_rmd(project_id, version_id)
    assert rmd["stats"]["measure_count"] == 1
    assert rmd["stats"]["dimension_count"] == 1
    assert rmd["measures"][0]["name"] == "Total Revenue"
    assert rmd["dimensions"][0]["name"] == "Customer ID"
    assert rmd["dimensions"][0]["connected_source"]["db"] == 161
