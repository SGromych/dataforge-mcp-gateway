"""SemanticService: normalization, caching and the read flows an agent follows."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from dataforge_mcp.application.use_cases import SemanticService
from dataforge_mcp.cache.file_store import FileCacheStore
from dataforge_mcp.cache.store import connection_key, rmd_key
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
# Normalization
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_measures_are_normalized(service: SemanticService) -> None:
    respx.get(f"{PFX}/measures").mock(return_value=httpx.Response(200, json=fx.MEASURES_200))
    result = await service.get_measures(392, 948)

    measure = result["measures"][0]
    assert measure["id"] == "1000"
    assert measure["name"] == "Total revenue"
    assert measure["description"] == "Gross revenue across all channels"
    # v2 only sends display_data_type; the canonical data_type falls back to it.
    assert measure["data_type"] == "Number"


@respx.mock
@pytest.mark.asyncio
async def test_dimensions_keep_the_source_connection(service: SemanticService) -> None:
    respx.get(f"{PFX}/dimensions").mock(return_value=httpx.Response(200, json=fx.DIMENSIONS_200))
    result = await service.get_dimensions(392, 948)

    source = result["dimensions"][0]["connected_source"]
    assert source["connection"] == "Production PostgreSQL"
    assert source["schema_"] == "public"
    assert source["table"] == "dim_customer"


@respx.mock
@pytest.mark.asyncio
async def test_facts_are_normalized(service: SemanticService) -> None:
    respx.get(f"{PFX}/facts").mock(return_value=httpx.Response(200, json=fx.FACTS_200))
    result = await service.get_facts(392, 948)

    fact = result["facts"][0]
    assert fact["id"] == "3000"
    assert fact["name"] == "Order line"
    assert fact["source_data_type"] == "DECIMAL(18,2)"


@respx.mock
@pytest.mark.asyncio
async def test_listings_are_paged_through(service: SemanticService) -> None:
    """A version with more rows than one page must come back complete."""
    page_one = {
        "measures": [fx.MEASURE_ROW],
        "pagination": fx.pagination(total=2, page=1, pages=2),
    }
    page_two = {
        "measures": [{**fx.MEASURE_ROW, "id": "1001", "measure_name": "Net revenue"}],
        "pagination": fx.pagination(total=2, page=2, pages=2),
    }
    route = respx.get(f"{PFX}/measures").mock(
        side_effect=[httpx.Response(200, json=page_one), httpx.Response(200, json=page_two)]
    )

    result = await service.get_measures(392, 948)

    assert route.call_count == 2
    assert [m["id"] for m in result["measures"]] == ["1000", "1001"]
    assert result["pagination"]["fetched"] == 2


# ---------------------------------------------------------------------------
# RMD snapshot
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_rmd_builds_semantic_context(service: SemanticService) -> None:
    respx.get(f"{PFX}/rmd").mock(return_value=httpx.Response(200, json=fx.RMD_EXPORT_200))
    result = await service.get_rmd(392, 948)

    # Project and version come from the payload, not from the path arguments.
    assert result["project"]["name"] == "Sales Analytics"
    assert result["version"]["is_global"] is True
    assert result["stats"] == {"measure_count": 1, "dimension_count": 1, "fact_count": 1}
    assert "raw" not in result["measures"][0]


@respx.mock
@pytest.mark.asyncio
async def test_rmd_include_raw(service: SemanticService) -> None:
    respx.get(f"{PFX}/rmd").mock(return_value=httpx.Response(200, json=fx.RMD_EXPORT_200))
    result = await service.get_rmd(392, 948, include_raw=True)
    assert result["measures"][0]["raw"]["measure_name"] == "Total revenue"


@respx.mock
@pytest.mark.asyncio
async def test_rmd_and_consolidated_share_one_call(service: SemanticService) -> None:
    """Both tools read the same endpoint, so they must share the fetch and the cache."""
    route = respx.get(f"{PFX}/rmd").mock(return_value=httpx.Response(200, json=fx.RMD_EXPORT_200))

    semantic = await service.get_rmd(392, 948)
    consolidated = await service.get_consolidated_rmd(392, 948)

    assert route.call_count == 1
    assert semantic["stats"]["measure_count"] == 1
    assert len(consolidated["fact_tables"]) == 1
    assert len(consolidated["relationships"]) == 1
    assert consolidated["exported_at"] is not None


@respx.mock
@pytest.mark.asyncio
async def test_rmd_include_sql_uses_its_own_cache_entry(service: SemanticService) -> None:
    route = respx.get(f"{PFX}/rmd").mock(return_value=httpx.Response(200, json=fx.RMD_EXPORT_200))
    await service.get_consolidated_rmd(392, 948, include_sql=False)
    await service.get_consolidated_rmd(392, 948, include_sql=True)
    assert route.call_count == 2


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_second_read_is_served_from_cache(service: SemanticService) -> None:
    route = respx.get(f"{PFX}/measures").mock(
        return_value=httpx.Response(200, json=fx.MEASURES_200)
    )
    await service.get_measures(392, 948)
    await service.get_measures(392, 948)
    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_use_cache_false_refetches(service: SemanticService) -> None:
    route = respx.get(f"{PFX}/measures").mock(
        return_value=httpx.Response(200, json=fx.MEASURES_200)
    )
    await service.get_measures(392, 948)
    await service.get_measures(392, 948, use_cache=False)
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_connection_schema_flag_is_part_of_the_cache_key(
    service: SemanticService,
) -> None:
    """Without the flag in the key, a schema-less answer was served for a schema request."""
    route = respx.get(f"{PFX}/connections/3821").mock(
        side_effect=[
            httpx.Response(200, json=fx.CONNECTION_DETAIL_200),
            httpx.Response(200, json=fx.CONNECTION_DETAIL_WITH_SCHEMA_200),
        ]
    )

    short = await service.get_connection(392, 948, 3821)
    full = await service.get_connection(392, 948, 3821, include_db_schema=True)

    assert route.call_count == 2
    assert short.get("db_schema") is None
    assert full["db_schema"]["tables"][0]["table_name"] == "fact_sales"
    assert connection_key(392, 948, 3821, "ru", False) != connection_key(
        392, 948, 3821, "ru", True
    )


@respx.mock
@pytest.mark.asyncio
async def test_last_known_good_serves_a_failed_read(service: SemanticService) -> None:
    route = respx.get(f"{PFX}/measures").mock(
        side_effect=[
            httpx.Response(200, json=fx.MEASURES_200),
            httpx.Response(503),
        ]
    )
    await service.get_measures(392, 948)
    await service.cache.invalidate_prefix("measures:392:948")

    # Entry is gone, so the stale copy is not available either.
    with pytest.raises(DataForgeError):
        await service.get_measures(392, 948, use_cache=False)
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_expired_entry_is_reused_when_the_api_fails(
    settings: Settings, tmp_path: Path
) -> None:
    settings.cache_ttl_seconds = 0
    client = DataForgeClient(base_url=BASE, api_key="k", max_retries=1)
    service = SemanticService(client, FileCacheStore(str(tmp_path / "cache")), settings)

    respx.get(f"{PFX}/measures").mock(
        side_effect=[
            httpx.Response(200, json=fx.MEASURES_200),
            httpx.Response(503),
        ]
    )
    await service.get_measures(392, 948)
    stale = await service.get_measures(392, 948)
    assert stale["measures"][0]["name"] == "Total revenue"


# ---------------------------------------------------------------------------
# Data model reads
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_data_model_listings(service: SemanticService) -> None:
    respx.get(f"{PFX}/data-marts").mock(return_value=httpx.Response(200, json=fx.DATA_MARTS_200))
    respx.get(f"{PFX}/dimension-groups").mock(
        return_value=httpx.Response(200, json=fx.DIMENSION_GROUPS_200)
    )
    respx.get(f"{PFX}/fact-tables").mock(return_value=httpx.Response(200, json=fx.FACT_TABLES_200))
    respx.get(f"{PFX}/relationships").mock(
        return_value=httpx.Response(200, json=fx.RELATIONSHIPS_200)
    )

    marts = await service.list_data_marts(392, 948)
    groups = await service.list_dimension_groups(392, 948)
    tables = await service.list_fact_tables(392, 948)
    relationships = await service.list_relationships(392, 948)

    assert len(marts["data_marts"]) == 1
    assert marts["data_marts"][0]["has_physical_view"] is False
    assert len(groups["dimension_groups"]) == 1
    assert len(tables["fact_tables"]) == 1
    assert relationships["relationships"][0]["relationship_type"] == "many_to_one"


@respx.mock
@pytest.mark.asyncio
async def test_generate_sql_marks_success(service: SemanticService) -> None:
    respx.post(f"{PFX}/data-marts/9666/generate-sql").mock(
        side_effect=[
            httpx.Response(200, json=fx.GENERATE_SQL_OK_200),
            httpx.Response(200, json=fx.GENERATE_SQL_FAILED_200),
        ]
    )

    ok = await service.generate_sql(392, 948, 9666, limit=100)
    failed = await service.generate_sql(392, 948, 9666)

    assert ok["succeeded"] is True
    assert ok["sql_script"].startswith("SELECT")
    assert failed["succeeded"] is False
    assert failed["validation_errors"][0]["code"] == "SQL_GENERATION_FAILED"


@respx.mock
@pytest.mark.asyncio
async def test_physical_view_and_connection_schema(service: SemanticService) -> None:
    respx.get(f"{PFX}/data-marts/9666/view").mock(
        return_value=httpx.Response(200, json=fx.PHYSICAL_VIEW_EXISTS_200)
    )
    respx.get(f"{PFX}/connections/3821/schema").mock(
        return_value=httpx.Response(200, json=fx.CONNECTION_SCHEMA_200)
    )

    view = await service.get_data_mart_view(392, 948, 9666)
    schema = await service.get_connection_schema(392, 948, 3821)

    assert view["status"] == "active"
    assert view["is_stale"] is False
    assert view["connection"]["db_type"] == "clickhouse"
    assert schema["schema"]["tables"][0]["table_name"] == "fact_sales"


@respx.mock
@pytest.mark.asyncio
async def test_project_access_and_git_connections(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/access").mock(
        return_value=httpx.Response(200, json=fx.PROJECT_ACCESS_200)
    )
    respx.get(f"{BASE}/df-api/v2/git-connections").mock(
        return_value=httpx.Response(200, json=fx.GIT_CONNECTIONS_200)
    )

    access = await service.get_project_access(392)
    git = await service.list_git_connections()

    assert access["access"][0]["email"] == "pavel@example.com"
    assert git["git_connections"][0]["platform"] == "gitlab"


# ---------------------------------------------------------------------------
# Integration flows
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_flow_projects_versions_rmd(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=fx.PROJECTS_200)
    )
    respx.get(f"{BASE}/df-api/v2/projects/392/versions").mock(
        return_value=httpx.Response(200, json=fx.VERSIONS_200)
    )
    respx.get(f"{PFX}/rmd").mock(return_value=httpx.Response(200, json=fx.RMD_EXPORT_200))

    projects = await service.list_projects()
    versions = await service.list_versions(392)
    rmd = await service.get_rmd(392, 948)

    assert projects["projects"][0]["id"] == 12
    assert versions["versions"][0]["name"] == "Q4 2025"
    assert rmd["measures"][0]["name"] == "Total revenue"


@respx.mock
@pytest.mark.asyncio
async def test_flow_data_mart_to_sql(service: SemanticService) -> None:
    respx.get(f"{PFX}/data-marts").mock(return_value=httpx.Response(200, json=fx.DATA_MARTS_200))
    respx.get(f"{PFX}/data-marts/9666").mock(
        return_value=httpx.Response(200, json=fx.DATA_MART_DETAIL_200)
    )
    respx.post(f"{PFX}/data-marts/9666/generate-sql").mock(
        return_value=httpx.Response(200, json=fx.GENERATE_SQL_OK_200)
    )

    listing = await service.list_data_marts(392, 948, search="Fashion")
    mart_id = int(listing["data_marts"][0]["id"])
    detail = await service.get_data_mart(392, 948, mart_id)
    sql = await service.generate_sql(392, 948, mart_id, limit=100)

    assert detail["selected_measures"][0]["measure_name"] == "Items Gross, count"
    assert sql["target_db_type"] == "clickhouse"


@respx.mock
@pytest.mark.asyncio
async def test_flow_read_then_write_then_reread(service: SemanticService) -> None:
    """The core agent loop: read an id, write with it, read the fresh state back."""
    measures = respx.get(f"{PFX}/measures").mock(
        return_value=httpx.Response(200, json=fx.MEASURES_200)
    )
    respx.patch(f"{PFX}/measures/1000").mock(
        return_value=httpx.Response(200, json=fx.MEASURE_CREATED_201)
    )

    first = await service.get_measures(392, 948)
    measure_id = int(first["measures"][0]["id"])

    written = await service.write_measure(
        392, 948, mode="update", measure_id=measure_id, comment="reviewed"
    )
    await service.get_measures(392, 948)

    assert written["status"] == "ok"
    # The write invalidated the cache, so the re-read hit the API again.
    assert measures.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_health_reports_unavailable_api(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(return_value=httpx.Response(500))
    health = await service.check_health()
    assert health["server_status"] == "ok"
    assert health["product_api_status"] == "unavailable"


@respx.mock
@pytest.mark.asyncio
async def test_api_key_error_propagates(service: SemanticService) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(401, json=fx.ERR_401_INVALID_API_KEY)
    )
    with pytest.raises(DataForgeError) as exc_info:
        await service.list_projects()
    assert exc_info.value.code is ErrorCode.DATAFORGE_API_KEY_INVALID


@respx.mock
@pytest.mark.asyncio
async def test_rmd_cache_key_is_shared(service: SemanticService) -> None:
    respx.get(f"{PFX}/rmd").mock(return_value=httpx.Response(200, json=fx.RMD_EXPORT_200))
    await service.get_rmd(392, 948)
    assert await service.cache.get(rmd_key(392, 948, "ru", False)) is not None
