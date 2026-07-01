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

FACTS_RESPONSE = {
    "facts": [
        {
            "row_number": "1",
            "group": "Sales",
            "block": "Orders",
            "fact_name": "Order Amount",
            "fact_description": "Total order amount",
            "original_source_type": "Database",
            "original_source": "Sales DB",
            "original_object": "orders_table",
            "source_data_type": "Decimal",
            "fact_type": "Additive",
            "formula": "[Amount]",
            "connected_source": {"database": "Sales DB", "table": "orders"},
            "status": "Active",
            "relevance": "High",
            "required": True,
            "visibility": "Public",
        }
    ],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

RMD_RESPONSE = {
    "measures": MEASURES_RESPONSE["measures"],
    "dimensions": DIMENSIONS_RESPONSE["dimensions"],
    "facts": FACTS_RESPONSE["facts"],
    "pagination": {
        "measures": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
        "dimensions": {"total": 1, "page": 1, "pageSize": 50, "totalPages": 1},
        "facts": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
    },
}


@pytest.fixture
def client() -> DataForgeClient:
    return DataForgeClient(base_url=BASE, api_key="test-key", max_retries=2)


@respx.mock
@pytest.mark.asyncio
async def test_get_projects_success(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
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
    respx.get(f"{BASE}/df-api/v2/projects").mock(
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
    respx.get(f"{BASE}/df-api/v2/projects/392/versions").mock(
        return_value=httpx.Response(200, json=VERSIONS_RESPONSE)
    )
    async with client:
        result = await client.get_versions(392)
    assert len(result.versions) == 2
    assert result.versions[0].is_global is True


@respx.mock
@pytest.mark.asyncio
async def test_get_measures_success(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/measures").mock(
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
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/dimensions").mock(
        return_value=httpx.Response(200, json=DIMENSIONS_RESPONSE)
    )
    async with client:
        result = await client.get_dimensions(392, 948)
    assert len(result.dimensions) == 1
    assert result.dimensions[0].dimension_name == "Customer ID"
    assert result.dimensions[0].connected_source.db == 161


@respx.mock
@pytest.mark.asyncio
async def test_get_facts_success(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/facts").mock(
        return_value=httpx.Response(200, json=FACTS_RESPONSE)
    )
    async with client:
        result = await client.get_facts(392, 948)
    assert len(result.facts) == 1
    assert result.facts[0].fact_name == "Order Amount"
    assert result.facts[0].fact_type == "Additive"
    assert result.facts[0].connected_source.database == "Sales DB"


@respx.mock
@pytest.mark.asyncio
async def test_get_rmd_success(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=RMD_RESPONSE)
    )
    async with client:
        result = await client.get_rmd(392, 948)
    assert len(result.measures) == 1
    assert len(result.dimensions) == 1
    assert len(result.facts) == 1
    assert result.pagination.measures.total == 1
    assert result.pagination.dimensions.total == 1
    assert result.pagination.facts.total == 1


@respx.mock
@pytest.mark.asyncio
async def test_get_rmd_without_facts(client: DataForgeClient) -> None:
    """RMD response without facts array should still parse (backward compat)."""
    rmd_no_facts = {
        "measures": MEASURES_RESPONSE["measures"],
        "dimensions": DIMENSIONS_RESPONSE["dimensions"],
        "pagination": {
            "measures": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
            "dimensions": {"total": 1, "page": 1, "pageSize": 50, "totalPages": 1},
        },
    }
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=rmd_no_facts)
    )
    async with client:
        result = await client.get_rmd(392, 948)
    assert len(result.measures) == 1
    assert len(result.facts) == 0


@respx.mock
@pytest.mark.asyncio
async def test_401_key_missing(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(401, text='{"error": "API_KEY.KEY_MISSING"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_API_KEY_MISSING


@respx.mock
@pytest.mark.asyncio
async def test_401_invalid_key(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(401, text='{"error": "API_KEY.INVALID_KEY"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_API_KEY_INVALID


@respx.mock
@pytest.mark.asyncio
async def test_401_unauthorized(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(401, text='{"error": "Unauthorized"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_UNAUTHORIZED


@respx.mock
@pytest.mark.asyncio
async def test_401_auth_failed(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(401, text='{"error": "API_KEY.AUTH_FAILED"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_AUTH_FAILED


@respx.mock
@pytest.mark.asyncio
async def test_403_account_locked(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(403, text='{"error": "API_KEY.ACCOUNT_LOCKED"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_ACCOUNT_LOCKED


@respx.mock
@pytest.mark.asyncio
async def test_403_ip_blocked(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(403, text='{"error": "API_KEY.IP_BLOCKED"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_IP_BLOCKED


@respx.mock
@pytest.mark.asyncio
async def test_403_license_invalid(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(
            403, text='{"error": "API.NOT_AVAILABLE_WITHOUT_VALID_LICENSE"}'
        )
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_LICENSE_INVALID


@respx.mock
@pytest.mark.asyncio
async def test_400_invalid_parameter(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts").mock(
        return_value=httpx.Response(400, text='{"error": "DF_API.INVALID_PARAMETER"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_data_marts(392, 948)
    assert exc_info.value.code == ErrorCode.DATAFORGE_INVALID_PARAMETER


@respx.mock
@pytest.mark.asyncio
async def test_404_not_found(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/999/versions").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_versions(999)
    assert exc_info.value.code == ErrorCode.DATAFORGE_RESOURCE_NOT_FOUND


@respx.mock
@pytest.mark.asyncio
async def test_timeout(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(side_effect=httpx.ReadTimeout("read timed out"))
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_TIMEOUT


@respx.mock
@pytest.mark.asyncio
async def test_500_retry_then_success(client: DataForgeClient) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects")
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
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_SERVER_ERROR


@respx.mock
@pytest.mark.asyncio
async def test_pagination_camelcase(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=PROJECTS_RESPONSE)
    )
    async with client:
        result = await client.get_projects()
    assert result.pagination.page_size == 100
    assert result.pagination.total_pages == 1


# ---------------------------------------------------------------------------
# DF API client tests
# ---------------------------------------------------------------------------

DATA_MARTS_RESPONSE = {
    "dataMarts": [{"id": 1, "name": "Sales Mart", "type": "standard", "merge_type": "union"}],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

DATA_MART_DETAIL = {
    "id": 1,
    "name": "Sales Mart",
    "type": "standard",
    "measures": [{"id": 10, "name": "Revenue"}],
    "dimensions": [{"id": 20, "name": "Date"}],
    "facts": [],
    "sourceFactTables": [{"id": 30, "name": "orders"}],
}

CONNECTIONS_RESPONSE = {
    "connections": [{"id": 1, "name": "Main DB", "dbType": "postgresql", "status": "active"}],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

DIMENSION_GROUPS_RESPONSE = {
    "dimensionGroups": [{"id": 1, "name": "Date Group", "primaryKey": "date_id"}],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

FACT_TABLES_RESPONSE = {
    "factTables": [{"id": 1, "name": "orders"}],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

RELATIONSHIPS_RESPONSE = {
    "relationships": [
        {
            "id": 1,
            "sourceFactTable": {"id": 1, "name": "orders"},
            "targetDimensionGroup": {"id": 1, "name": "Date Group"},
            "relationshipType": "many_to_one",
            "createdAt": "2026-01-01T00:00:00Z",
        }
    ],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

CONSOLIDATED_RMD_RESPONSE = {
    "project": {"id": 392, "name": "Fashion"},
    "version": {"id": 948, "name": "v1"},
    "measures": [],
    "dimensions": [],
    "facts": [],
    "dimensionGroups": [],
    "factTables": [],
    "relationships": [],
    "exportedAt": "2026-05-18T12:00:00Z",
}

SQL_RESPONSE = {"sql": "SELECT * FROM orders LIMIT 100"}


@respx.mock
@pytest.mark.asyncio
async def test_get_data_marts(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts").mock(
        return_value=httpx.Response(200, json=DATA_MARTS_RESPONSE)
    )
    async with client:
        result = await client.get_data_marts(392, 948)
    assert len(result.data_marts) == 1
    assert result.data_marts[0].name == "Sales Mart"


@respx.mock
@pytest.mark.asyncio
async def test_get_data_mart_detail(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts/1").mock(
        return_value=httpx.Response(200, json=DATA_MART_DETAIL)
    )
    async with client:
        result = await client.get_data_mart(392, 948, 1)
    assert result.id == 1
    assert len(result.measures) == 1
    assert len(result.source_fact_tables) == 1


@respx.mock
@pytest.mark.asyncio
async def test_generate_sql(client: DataForgeClient) -> None:
    respx.post(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts/1/generate-sql").mock(
        return_value=httpx.Response(200, json=SQL_RESPONSE)
    )
    async with client:
        result = await client.generate_sql(392, 948, 1)
    assert result.sql == "SELECT * FROM orders LIMIT 100"


@respx.mock
@pytest.mark.asyncio
async def test_get_connections(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/connections").mock(
        return_value=httpx.Response(200, json=CONNECTIONS_RESPONSE)
    )
    async with client:
        result = await client.get_connections(392, 948)
    assert len(result.connections) == 1
    assert result.connections[0].db_type == "postgresql"


@respx.mock
@pytest.mark.asyncio
async def test_get_dimension_groups(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/dimension-groups").mock(
        return_value=httpx.Response(200, json=DIMENSION_GROUPS_RESPONSE)
    )
    async with client:
        result = await client.get_dimension_groups(392, 948)
    assert len(result.dimension_groups) == 1
    assert result.dimension_groups[0].primary_key == "date_id"


@respx.mock
@pytest.mark.asyncio
async def test_get_fact_tables(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/fact-tables").mock(
        return_value=httpx.Response(200, json=FACT_TABLES_RESPONSE)
    )
    async with client:
        result = await client.get_fact_tables(392, 948)
    assert len(result.fact_tables) == 1
    assert result.fact_tables[0].name == "orders"


@respx.mock
@pytest.mark.asyncio
async def test_get_relationships(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/relationships").mock(
        return_value=httpx.Response(200, json=RELATIONSHIPS_RESPONSE)
    )
    async with client:
        result = await client.get_relationships(392, 948)
    assert len(result.relationships) == 1
    assert result.relationships[0].source_fact_table["id"] == 1
    assert result.relationships[0].relationship_type == "many_to_one"


@respx.mock
@pytest.mark.asyncio
async def test_get_consolidated_rmd(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=CONSOLIDATED_RMD_RESPONSE)
    )
    async with client:
        result = await client.get_consolidated_rmd(392, 948)
    assert result.project["id"] == 392
    assert result.exported_at == "2026-05-18T12:00:00Z"


# ---------------------------------------------------------------------------
# v2 new feature tests
# ---------------------------------------------------------------------------


MEASURES_WITH_SQL_RESPONSE = {
    "measures": [
        {
            "measure_name": "Total Revenue",
            "measure_type": "Sum",
            "sql_code": {
                "generated_at": "2026-06-01T10:00:00Z",
                "sql_scripts": [
                    {
                        "fact_table_id": "1",
                        "fact_table_name": "orders",
                        "sql": "SELECT SUM(amount) FROM orders",
                    }
                ],
            },
        }
    ],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}


@respx.mock
@pytest.mark.asyncio
async def test_get_measures_include_sql(client: DataForgeClient) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/measures")
    route.mock(return_value=httpx.Response(200, json=MEASURES_WITH_SQL_RESPONSE))
    async with client:
        result = await client.get_measures(392, 948, include_sql=True)
    assert len(result.measures) == 1
    assert result.measures[0].sql_code is not None
    assert result.measures[0].sql_code.generated_at == "2026-06-01T10:00:00Z"
    assert len(result.measures[0].sql_code.sql_scripts) == 1
    assert result.measures[0].sql_code.sql_scripts[0].sql == "SELECT SUM(amount) FROM orders"
    # Verify include_sql param was sent
    assert route.calls[0].request.url.params["include_sql"] == "true"


@respx.mock
@pytest.mark.asyncio
async def test_429_rate_limit(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(429, text='{"error": "rate limit exceeded"}')
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code == ErrorCode.DATAFORGE_RATE_LIMIT_EXCEEDED


@respx.mock
@pytest.mark.asyncio
async def test_429_no_retry(client: DataForgeClient) -> None:
    """429 should NOT be retried — raises immediately."""
    route = respx.get(f"{BASE}/df-api/v2/projects")
    route.mock(return_value=httpx.Response(429, text="rate limited"))
    async with client:
        with pytest.raises(DataForgeError):
            await client.get_projects()
    assert route.call_count == 1  # no retry


@respx.mock
@pytest.mark.asyncio
async def test_get_consolidated_rmd_include_sql(client: DataForgeClient) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/rmd")
    route.mock(return_value=httpx.Response(200, json=CONSOLIDATED_RMD_RESPONSE))
    async with client:
        result = await client.get_consolidated_rmd(392, 948, include_sql=True)
    assert result.project["id"] == 392
    assert route.calls[0].request.url.params["include_sql"] == "true"


@respx.mock
@pytest.mark.asyncio
async def test_get_fact_table_include_dependencies(client: DataForgeClient) -> None:
    ft_detail = {
        "id": 1,
        "name": "orders",
        "measures": [],
        "dimensions": [],
        "facts": [],
        "dimensionGroups": [],
        "verificationFilters": [],
    }
    route = respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/fact-tables/1")
    route.mock(return_value=httpx.Response(200, json=ft_detail))
    async with client:
        result = await client.get_fact_table(392, 948, 1, include_dependencies=True)
    assert result.id == 1
    assert route.calls[0].request.url.params["includeDependencies"] == "true"


@respx.mock
@pytest.mark.asyncio
async def test_get_relationships_with_filters(client: DataForgeClient) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/relationships")
    route.mock(return_value=httpx.Response(200, json=RELATIONSHIPS_RESPONSE))
    async with client:
        result = await client.get_relationships(392, 948, fact_table_id=5, dimension_group_id=10)
    assert len(result.relationships) == 1
    assert route.calls[0].request.url.params["factTableId"] == "5"
    assert route.calls[0].request.url.params["dimensionGroupId"] == "10"
