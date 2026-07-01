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

FACTS_RESPONSE = {
    "facts": [
        {
            "row_number": "1",
            "group": "Sales",
            "block": "Orders",
            "fact_name": "Order Amount",
            "fact_description": "Total order amount",
            "source_data_type": "Decimal",
            "fact_type": "Additive",
            "formula": "[Amount]",
            "status": "Active",
            "required": True,
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

# DF API mock responses
DATA_MARTS_RESPONSE = {
    "dataMarts": [{"id": 1, "name": "Sales Mart", "type": "standard"}],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

DATA_MART_DETAIL = {
    "id": 1,
    "name": "Sales Mart",
    "type": "standard",
    "measures": [{"id": 10}],
    "dimensions": [],
    "facts": [],
    "sourceFactTables": [],
}

CONNECTIONS_RESPONSE = {
    "connections": [{"id": 1, "name": "Main DB", "dbType": "postgresql", "status": "active"}],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

CONNECTION_DETAIL = {"id": 1, "name": "Main DB", "dbType": "postgresql", "status": "active"}

DIMENSION_GROUPS_RESPONSE = {
    "dimensionGroups": [{"id": 1, "name": "Date Group", "primaryKey": "date_id"}],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

DIMENSION_GROUP_DETAIL = {
    "id": 1,
    "name": "Date Group",
    "primaryKey": "date_id",
    "dimensions": [{"id": 10}],
    "relatedFactTables": [{"id": 20}],
}

FACT_TABLES_RESPONSE = {
    "factTables": [{"id": 1, "name": "orders"}],
    "pagination": {"total": 1, "page": 1, "pageSize": 100, "totalPages": 1},
}

FACT_TABLE_DETAIL = {
    "id": 1,
    "name": "orders",
    "measures": [],
    "dimensions": [],
    "facts": [],
    "dimensionGroups": [],
    "verificationFilters": [],
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

RELATIONSHIP_DETAIL = {
    "id": 1,
    "sourceFactTable": {"id": 1, "name": "orders"},
    "targetDimensionGroup": {"id": 1, "name": "Date Group"},
    "relationshipType": "many_to_one",
    "createdAt": "2026-01-01T00:00:00Z",
    "updatedAt": "2026-01-02T00:00:00Z",
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


# ---------------------------------------------------------------------------
# Existing RMD API tool tests
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_health_ok(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=PROJECTS_RESPONSE)
    )
    result = await service.check_health()
    assert result["server_status"] == "ok"
    assert result["product_api_status"] == "ok"
    assert result["cache_status"] == "ok"


@respx.mock
@pytest.mark.asyncio
async def test_health_api_unavailable(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    result = await service.check_health()
    assert result["product_api_status"] == "unavailable"


@respx.mock
@pytest.mark.asyncio
async def test_list_projects(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=PROJECTS_RESPONSE)
    )
    result = await service.list_projects()
    assert len(result["projects"]) == 1
    assert result["projects"][0]["name"] == "Fashion Retail"


@respx.mock
@pytest.mark.asyncio
async def test_get_measures_normalized(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/measures").mock(
        return_value=httpx.Response(200, json=MEASURES_RESPONSE)
    )
    result = await service.get_measures(392, 948)
    m = result["measures"][0]
    assert m["name"] == "Total Revenue"
    assert "measure_name" not in m  # normalized away at top level
    assert m["connected_source"]["db"] == "Sales DB"


@respx.mock
@pytest.mark.asyncio
async def test_get_facts(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/facts").mock(
        return_value=httpx.Response(200, json=FACTS_RESPONSE)
    )
    result = await service.get_facts(392, 948)
    f = result["facts"][0]
    assert f["name"] == "Order Amount"
    assert f["fact_type"] == "Additive"
    assert "fact_name" not in f  # normalized


@respx.mock
@pytest.mark.asyncio
async def test_get_rmd(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=RMD_RESPONSE)
    )
    result = await service.get_rmd(392, 948)
    assert result["stats"]["measure_count"] == 1
    assert result["stats"]["dimension_count"] == 1
    assert result["stats"]["fact_count"] == 1
    assert result["measures"][0]["name"] == "Total Revenue"
    assert result["dimensions"][0]["name"] == "Customer ID"
    assert result["facts"][0]["name"] == "Order Amount"
    # raw should be stripped by default
    assert "raw" not in result["measures"][0]
    assert "raw" not in result["facts"][0]


@respx.mock
@pytest.mark.asyncio
async def test_get_rmd_with_raw(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=RMD_RESPONSE)
    )
    result = await service.get_rmd(392, 948, include_raw=True)
    assert "raw" in result["measures"][0]
    assert "raw" in result["facts"][0]


@respx.mock
@pytest.mark.asyncio
async def test_refresh_cache(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=RMD_RESPONSE)
    )
    result = await service.refresh_cache(392, 948)
    assert result["status"] == "refreshed"
    assert "rmd:392:948:ru" in result["cache_key"]


@respx.mock
@pytest.mark.asyncio
async def test_error_401(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(401, text='{"error": "API_KEY.INVALID_KEY"}')
    )
    from dataforge_mcp.errors import DataForgeError

    with pytest.raises(DataForgeError) as exc_info:
        await service.list_projects(use_cache=False)
    assert exc_info.value.code == ErrorCode.DATAFORGE_API_KEY_INVALID


@respx.mock
@pytest.mark.asyncio
async def test_cache_hit(service: SemanticService) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects")
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
    """Integration test: projects -> versions -> rmd (with facts)."""
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=PROJECTS_RESPONSE)
    )
    respx.get(f"{BASE}/df-api/v2/projects/392/versions").mock(
        return_value=httpx.Response(200, json=VERSIONS_RESPONSE)
    )
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/rmd").mock(
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
    assert rmd["stats"]["fact_count"] == 1
    assert rmd["measures"][0]["name"] == "Total Revenue"
    assert rmd["dimensions"][0]["name"] == "Customer ID"
    assert rmd["facts"][0]["name"] == "Order Amount"
    assert rmd["dimensions"][0]["connected_source"]["db"] == 161


# ---------------------------------------------------------------------------
# DF API tool tests
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_list_data_marts(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts").mock(
        return_value=httpx.Response(200, json=DATA_MARTS_RESPONSE)
    )
    result = await service.list_data_marts(392, 948)
    assert len(result["data_marts"]) == 1
    assert result["data_marts"][0]["name"] == "Sales Mart"


@respx.mock
@pytest.mark.asyncio
async def test_get_data_mart(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts/1").mock(
        return_value=httpx.Response(200, json=DATA_MART_DETAIL)
    )
    result = await service.get_data_mart(392, 948, 1)
    assert result["id"] == 1
    assert result["name"] == "Sales Mart"
    assert len(result["measures"]) == 1


@respx.mock
@pytest.mark.asyncio
async def test_generate_sql(service: SemanticService) -> None:
    respx.post(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts/1/generate-sql").mock(
        return_value=httpx.Response(200, json=SQL_RESPONSE)
    )
    result = await service.generate_sql(392, 948, 1)
    assert result["sql"] == "SELECT * FROM orders LIMIT 100"


@respx.mock
@pytest.mark.asyncio
async def test_list_connections(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/connections").mock(
        return_value=httpx.Response(200, json=CONNECTIONS_RESPONSE)
    )
    result = await service.list_connections(392, 948)
    assert len(result["connections"]) == 1
    assert result["connections"][0]["name"] == "Main DB"


@respx.mock
@pytest.mark.asyncio
async def test_get_connection(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/connections/1").mock(
        return_value=httpx.Response(200, json=CONNECTION_DETAIL)
    )
    result = await service.get_connection(392, 948, 1)
    assert result["id"] == 1
    assert result["name"] == "Main DB"


@respx.mock
@pytest.mark.asyncio
async def test_list_dimension_groups(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/dimension-groups").mock(
        return_value=httpx.Response(200, json=DIMENSION_GROUPS_RESPONSE)
    )
    result = await service.list_dimension_groups(392, 948)
    assert len(result["dimension_groups"]) == 1
    assert result["dimension_groups"][0]["name"] == "Date Group"


@respx.mock
@pytest.mark.asyncio
async def test_get_dimension_group(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/dimension-groups/1").mock(
        return_value=httpx.Response(200, json=DIMENSION_GROUP_DETAIL)
    )
    result = await service.get_dimension_group(392, 948, 1)
    assert result["id"] == 1
    assert result["name"] == "Date Group"


@respx.mock
@pytest.mark.asyncio
async def test_list_fact_tables(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/fact-tables").mock(
        return_value=httpx.Response(200, json=FACT_TABLES_RESPONSE)
    )
    result = await service.list_fact_tables(392, 948)
    assert len(result["fact_tables"]) == 1
    assert result["fact_tables"][0]["name"] == "orders"


@respx.mock
@pytest.mark.asyncio
async def test_get_fact_table(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/fact-tables/1").mock(
        return_value=httpx.Response(200, json=FACT_TABLE_DETAIL)
    )
    result = await service.get_fact_table(392, 948, 1)
    assert result["id"] == 1
    assert result["name"] == "orders"


@respx.mock
@pytest.mark.asyncio
async def test_list_relationships(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/relationships").mock(
        return_value=httpx.Response(200, json=RELATIONSHIPS_RESPONSE)
    )
    result = await service.list_relationships(392, 948)
    assert len(result["relationships"]) == 1
    assert result["relationships"][0]["source_fact_table"]["id"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_get_relationship(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/relationships/1").mock(
        return_value=httpx.Response(200, json=RELATIONSHIP_DETAIL)
    )
    result = await service.get_relationship(392, 948, 1)
    assert result["id"] == 1
    assert result["source_fact_table"]["id"] == 1
    assert result["target_dimension_group"]["id"] == 1


@respx.mock
@pytest.mark.asyncio
async def test_get_consolidated_rmd(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/rmd").mock(
        return_value=httpx.Response(200, json=CONSOLIDATED_RMD_RESPONSE)
    )
    result = await service.get_consolidated_rmd(392, 948)
    assert result["project"]["id"] == 392
    assert result["exported_at"] == "2026-05-18T12:00:00Z"


@respx.mock
@pytest.mark.asyncio
async def test_df_api_cache_hit(service: SemanticService) -> None:
    """Test that DF API responses are cached."""
    route = respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts")
    route.mock(return_value=httpx.Response(200, json=DATA_MARTS_RESPONSE))

    result1 = await service.list_data_marts(392, 948)
    assert route.call_count == 1

    result2 = await service.list_data_marts(392, 948)
    assert route.call_count == 1  # cached
    assert result1 == result2


@respx.mock
@pytest.mark.asyncio
async def test_df_api_integration_flow(service: SemanticService) -> None:
    """Integration test: data marts -> detail -> sql generation."""
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts").mock(
        return_value=httpx.Response(200, json=DATA_MARTS_RESPONSE)
    )
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts/1").mock(
        return_value=httpx.Response(200, json=DATA_MART_DETAIL)
    )
    respx.post(f"{BASE}/df-api/v2/projects/392/versions/948/data-marts/1/generate-sql").mock(
        return_value=httpx.Response(200, json=SQL_RESPONSE)
    )

    dms = await service.list_data_marts(392, 948)
    dm_id = dms["data_marts"][0]["id"]
    assert dm_id == 1

    detail = await service.get_data_mart(392, 948, dm_id)
    assert detail["name"] == "Sales Mart"

    sql = await service.generate_sql(392, 948, dm_id)
    assert "SELECT" in sql["sql"]


# ---------------------------------------------------------------------------
# v2 new feature tests
# ---------------------------------------------------------------------------

MEASURES_WITH_SQL = {
    "measures": [
        {
            "row_number": "1",
            "measure_name": "Total Revenue",
            "measure_type": "Sum",
            "data_type": "Numeric",
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
async def test_get_measures_with_sql(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/measures").mock(
        return_value=httpx.Response(200, json=MEASURES_WITH_SQL)
    )
    result = await service.get_measures(392, 948, include_sql=True)
    m = result["measures"][0]
    assert m["name"] == "Total Revenue"
    assert m["sql_code"] is not None
    assert m["sql_code"]["generated_at"] == "2026-06-01T10:00:00Z"
    assert len(m["sql_code"]["sql_scripts"]) == 1
    assert m["sql_code"]["sql_scripts"][0]["sql"] == "SELECT SUM(amount) FROM orders"


@respx.mock
@pytest.mark.asyncio
async def test_get_consolidated_rmd_with_sql(service: SemanticService) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects/392/versions/948/rmd")
    route.mock(return_value=httpx.Response(200, json=CONSOLIDATED_RMD_RESPONSE))
    result = await service.get_consolidated_rmd(392, 948, include_sql=True)
    assert result["project"]["id"] == 392
    assert route.calls[0].request.url.params["include_sql"] == "true"
