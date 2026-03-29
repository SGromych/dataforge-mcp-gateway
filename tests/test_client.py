"""Tests for DataForge API client."""

import httpx
import pytest
import respx

from dataforge_mcp.dataforge.client import DataForgeClient
from dataforge_mcp.errors import DataForgeError, ErrorCode

BASE = "https://api.test.example.com"

PROJECTS_RESPONSE = {
    "projects": [
        {"id": 1, "name": "Project A", "description": "Desc A"},
        {"id": 2, "name": "Project B", "description": None},
    ],
    "pagination": {"total": 2, "page": 1, "pageSize": 100, "totalPages": 1},
}

VERSIONS_RESPONSE = {
    "versions": [
        {"id": 10, "name": "v1", "is_global": True},
        {"id": 11, "name": "v2", "is_global": False},
    ],
    "pagination": {"total": 2, "page": 1, "pageSize": 100, "totalPages": 1},
}

MEASURES_RESPONSE = {
    "measures": [
        {
            "row_number": "1",
            "group": "Sales",
            "block": "Revenue",
            "measure_name": "Total Revenue",
            "measure_description": "Total revenue from all sales",
            "original_source_type": "Database",
            "original_source": "Sales DB",
            "original_object": "sales_table",
            "data_type": "Numeric",
            "measure_type": "Sum",
            "restrictions": None,
            "formula": "[Revenue]",
            "connected_source": {"database": "Sales DB", "table": "sales_table"},
            "report_for_verification": None,
            "comment": "Main revenue metric",
            "status": "Active",
            "relevance": "High",
            "required": True,
            "visibility": "Public",
            "responsible_for_data": "Data Team",
            "variation": None,
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
            "dimension_description": "Unique customer identifier",
            "original_source_type": "Database",
            "original_source": "Sales DB",
            "original_object": "customers_table",
            "dimension_group": "Customer Attributes",
            "data_type": "String",
            "connected_source": {"db": 161, "table": "customers", "column": "CompanyName"},
            "comment": "Primary key for customers",
            "value_options": None,
            "status": "Active",
            "relevance": "High",
            "required": True,
            "visibility": "Public",
            "responsible_for_data": "Data Team",
        }
    ],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
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
def client() -> DataForgeClient:
    return DataForgeClient(base_url=BASE, api_key="test-key", max_retries=2)


@respx.mock
@pytest.mark.asyncio
async def test_get_projects_success(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(200, json=PROJECTS_RESPONSE)
    )
    async with client:
        result = await client.get_projects()
    assert len(result.projects) == 2
    assert result.projects[0].name == "Project A"
    assert result.pagination.total == 2
    assert result.pagination.page_size == 100
    assert result.pagination.total_pages == 1


@respx.mock
@pytest.mark.asyncio
async def test_get_projects_empty(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(
            200,
            json={
                "projects": [],
                "pagination": {"total": 0, "page": 1, "pageSize": 100, "totalPages": 0},
            },
        )
    )
    async with client:
        result = await client.get_projects()
    assert len(result.projects) == 0


@respx.mock
@pytest.mark.asyncio
async def test_get_versions_success(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects/392/versions").mock(
        return_value=httpx.Response(200, json=VERSIONS_RESPONSE)
    )
    async with client:
        result = await client.get_versions(392)
    assert len(result.versions) == 2
    assert result.versions[0].is_global is True


@respx.mock
@pytest.mark.asyncio
async def test_get_measures_success(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects/392/versions/948/measures").mock(
        return_value=httpx.Response(200, json=MEASURES_RESPONSE)
    )
    async with client:
        result = await client.get_measures(392, 948)
    assert len(result.measures) == 1
    assert result.measures[0].measure_name == "Total Revenue"
    assert result.measures[0].connected_source.database == "Sales DB"


@respx.mock
@pytest.mark.asyncio
async def test_get_dimensions_success(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects/392/versions/948/dimensions").mock(
        return_value=httpx.Response(200, json=DIMENSIONS_RESPONSE)
    )
    async with client:
        result = await client.get_dimensions(392, 948)
    assert len(result.dimensions) == 1
    assert result.dimensions[0].dimension_name == "Customer ID"
    assert result.dimensions[0].connected_source.db == 161


@respx.mock
@pytest.mark.asyncio
async def test_get_rmd_success(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=RMD_RESPONSE)
    )
    async with client:
        result = await client.get_rmd(392, 948)
    assert len(result.measures) == 1
    assert len(result.dimensions) == 1
    assert result.pagination.measures.total == 1
    assert result.pagination.dimensions.total == 1


@respx.mock
@pytest.mark.asyncio
async def test_401_key_missing(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(401, text='{"error": "API_KEY.KEY_MISSING"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_API_KEY_MISSING


@respx.mock
@pytest.mark.asyncio
async def test_401_invalid_key(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(401, text='{"error": "API_KEY.INVALID_KEY"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_API_KEY_INVALID


@respx.mock
@pytest.mark.asyncio
async def test_401_unauthorized(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(401, text='{"error": "Unauthorized"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_UNAUTHORIZED


@respx.mock
@pytest.mark.asyncio
async def test_401_auth_failed(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(401, text='{"error": "API_KEY.AUTH_FAILED"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_AUTH_FAILED


@respx.mock
@pytest.mark.asyncio
async def test_404_not_found(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects/999/versions").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_versions(999)
    assert exc_info.value.code == ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND


@respx.mock
@pytest.mark.asyncio
async def test_timeout(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        side_effect=httpx.ReadTimeout("read timed out")
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_TIMEOUT


@respx.mock
@pytest.mark.asyncio
async def test_500_retry_then_success(client: DataForgeClient) -> None:
    route = respx.get(f"{BASE}/rmd-api/v1/projects")
    route.side_effect = [
        httpx.Response(500, text="Internal Server Error"),
        httpx.Response(200, json=PROJECTS_RESPONSE),
    ]
    async with client:
        result = await client.get_projects()
    assert len(result.projects) == 2
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_500_retries_exhausted(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_SERVER_ERROR


@respx.mock
@pytest.mark.asyncio
async def test_pagination_camelcase(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/rmd-api/v1/projects").mock(
        return_value=httpx.Response(200, json=PROJECTS_RESPONSE)
    )
    async with client:
        result = await client.get_projects()
    assert result.pagination.page_size == 100
    assert result.pagination.total_pages == 1
