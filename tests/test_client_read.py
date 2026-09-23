"""Read-client tests: request contract and response parsing.

Two regressions are locked down here, both of which used to pass silently:

* query-parameter casing — v2 names every filter in snake_case, and sending camelCase
  drops the filter without an error;
* model aliases — a camelCase alias on a v2 model made the field parse as empty.
"""

from __future__ import annotations

import json
import re

import httpx
import pytest
import respx

from dataforge_mcp.dataforge.client import DataForgeClient
from dataforge_mcp.errors import DataForgeError, ErrorCode
from tests.fixtures import api_v2 as fx

BASE = "https://api.test.example.com"
PFX = f"{BASE}/df-api/v2/projects/392/versions/948"


@pytest.fixture
def client() -> DataForgeClient:
    return DataForgeClient(base_url=BASE, api_key="test-api-key-12345", max_retries=2)


# ---------------------------------------------------------------------------
# Query-parameter contract
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_filters_are_snake_case(client: DataForgeClient) -> None:
    """The six filters that used to be sent in camelCase."""
    routes = {
        "data_marts": respx.get(f"{PFX}/data-marts").mock(
            return_value=httpx.Response(200, json=fx.DATA_MARTS_200)
        ),
        "connections": respx.get(f"{PFX}/connections").mock(
            return_value=httpx.Response(200, json=fx.CONNECTIONS_200)
        ),
        "connection": respx.get(f"{PFX}/connections/3821").mock(
            return_value=httpx.Response(200, json=fx.CONNECTION_DETAIL_WITH_SCHEMA_200)
        ),
        "fact_table": respx.get(f"{PFX}/fact-tables/6784").mock(
            return_value=httpx.Response(200, json=fx.FACT_TABLE_DETAIL_WITH_DEPS_200)
        ),
        "relationships": respx.get(f"{PFX}/relationships").mock(
            return_value=httpx.Response(200, json=fx.RELATIONSHIPS_200)
        ),
    }

    async with client:
        await client.get_data_marts(392, 948, merge_type="join", mart_type="with_grouping")
        await client.get_connections(392, 948, db_type="postgresql", status="active")
        await client.get_connection(392, 948, 3821, include_db_schema=True)
        await client.get_fact_table(392, 948, 6784, include_dependencies=True)
        await client.get_relationships(392, 948, fact_table_id=6784, dimension_group_id=1204)

    marts = routes["data_marts"].calls[0].request.url.params
    assert marts["merge_type"] == "join"
    assert marts["type"] == "with_grouping"

    conns = routes["connections"].calls[0].request.url.params
    assert conns["db_type"] == "postgresql"
    assert conns["status"] == "active"

    assert routes["connection"].calls[0].request.url.params["include_db_schema"] == "true"
    assert routes["fact_table"].calls[0].request.url.params["include_dependencies"] == "true"

    rels = routes["relationships"].calls[0].request.url.params
    assert rels["fact_table_id"] == "6784"
    assert rels["dimension_group_id"] == "1204"


@respx.mock
@pytest.mark.asyncio
async def test_no_camel_case_query_params_except_page_size(client: DataForgeClient) -> None:
    """pageSize is the only camelCase query parameter in the whole v2 surface."""
    respx.route(host="api.test.example.com").mock(
        return_value=httpx.Response(200, json=fx.PROJECTS_200)
    )

    async with client:
        await client.get_projects(page=2, page_size=50)
        await client.get_versions(392)
        await client.get_measures(392, 948, include_sql=True)
        await client.get_rmd(392, 948, include_sql=True)

    camel = re.compile(r"[a-z][A-Z]")
    for call in respx.calls:
        for key in call.request.url.params:
            assert key == "pageSize" or not camel.search(key), f"camelCase param: {key}"


@respx.mock
@pytest.mark.asyncio
async def test_rmd_listings_are_paged(client: DataForgeClient) -> None:
    """Without page/pageSize the API silently returns only its default 20 rows."""
    route = respx.get(f"{PFX}/measures").mock(
        return_value=httpx.Response(200, json=fx.MEASURES_200)
    )
    async with client:
        await client.get_measures(392, 948)

    params = route.calls[0].request.url.params
    assert params["page"] == "1"
    assert params["pageSize"] == "100"


@respx.mock
@pytest.mark.asyncio
async def test_optional_filters_are_omitted_when_none(client: DataForgeClient) -> None:
    route = respx.get(f"{PFX}/data-marts").mock(
        return_value=httpx.Response(200, json=fx.DATA_MARTS_200)
    )
    async with client:
        await client.get_data_marts(392, 948)

    params = route.calls[0].request.url.params
    for absent in ("type", "merge_type", "search"):
        assert absent not in params


@respx.mock
@pytest.mark.asyncio
async def test_generate_sql_is_post_with_query_and_no_body(client: DataForgeClient) -> None:
    """v2 moved limit/offset from the body into the query string."""
    route = respx.post(f"{PFX}/data-marts/9666/generate-sql").mock(
        return_value=httpx.Response(200, json=fx.GENERATE_SQL_OK_200)
    )
    async with client:
        await client.generate_sql(392, 948, 9666, limit=100, offset=0)

    request = route.calls[0].request
    assert request.method == "POST"
    assert request.url.params["limit"] == "100"
    assert request.url.params["offset"] == "0"
    assert request.content == b""


@respx.mock
@pytest.mark.asyncio
async def test_api_key_header_sent(client: DataForgeClient) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=fx.PROJECTS_200)
    )
    async with client:
        await client.get_projects()
    assert route.calls[0].request.headers["X-Api-Key"] == "test-api-key-12345"


@pytest.mark.asyncio
async def test_page_size_over_limit_rejected_locally(client: DataForgeClient) -> None:
    """Data marts, connections and Git connections answer 400 above 100."""
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_data_marts(392, 948, page_size=500)
    assert exc_info.value.code is ErrorCode.DATAFORGE_PAGE_SIZE_EXCEEDED


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_projects_and_versions(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, json=fx.PROJECTS_200)
    )
    respx.get(f"{BASE}/df-api/v2/projects/392/versions").mock(
        return_value=httpx.Response(200, json=fx.VERSIONS_200)
    )
    async with client:
        projects = await client.get_projects()
        versions = await client.get_versions(392)

    assert [p.name for p in projects.projects] == ["Sales Analytics", "Finance"]
    assert projects.pagination.total_pages == 1
    assert versions.versions[0].is_global is True


@respx.mock
@pytest.mark.asyncio
async def test_rmd_entities_carry_stable_ids(client: DataForgeClient) -> None:
    """`id` is the bridge between reading and writing — it must survive parsing."""
    respx.get(f"{PFX}/measures").mock(return_value=httpx.Response(200, json=fx.MEASURES_200))
    respx.get(f"{PFX}/dimensions").mock(return_value=httpx.Response(200, json=fx.DIMENSIONS_200))
    respx.get(f"{PFX}/facts").mock(return_value=httpx.Response(200, json=fx.FACTS_200))

    async with client:
        measures = await client.get_measures(392, 948)
        dimensions = await client.get_dimensions(392, 948)
        facts = await client.get_facts(392, 948)

    assert measures.measures[0].id == "1000"
    assert dimensions.dimensions[0].id == "2000"
    assert facts.facts[0].id == "3000"


@respx.mock
@pytest.mark.asyncio
async def test_connected_source_keeps_connection_and_schema(client: DataForgeClient) -> None:
    respx.get(f"{PFX}/dimensions").mock(return_value=httpx.Response(200, json=fx.DIMENSIONS_200))
    async with client:
        resp = await client.get_dimensions(392, 948)

    source = resp.dimensions[0].connected_source
    assert source.connection == "Production PostgreSQL"
    assert source.schema_ == "public"
    assert source.db == "analytics_db"


@respx.mock
@pytest.mark.asyncio
async def test_reference_columns_accept_localized_labels(client: DataForgeClient) -> None:
    """`required` is a localized label in v2, not a boolean."""
    respx.get(f"{PFX}/dimensions").mock(return_value=httpx.Response(200, json=fx.DIMENSIONS_200))
    async with client:
        resp = await client.get_dimensions(392, 948)
    assert resp.dimensions[0].required == "Да"


@respx.mock
@pytest.mark.asyncio
async def test_measures_include_sql(client: DataForgeClient) -> None:
    route = respx.get(f"{PFX}/measures").mock(
        return_value=httpx.Response(200, json=fx.MEASURES_200_WITH_SQL)
    )
    async with client:
        resp = await client.get_measures(392, 948, include_sql=True)

    assert route.calls[0].request.url.params["include_sql"] == "true"
    sql_code = resp.measures[0].sql_code
    assert sql_code.sql_scripts[0].fact_table_name == "fact_sales"


@respx.mock
@pytest.mark.asyncio
async def test_rmd_export_parses_full_snapshot(client: DataForgeClient) -> None:
    """The v2 /rmd response has no `pagination` key — the old model required one."""
    route = respx.get(f"{PFX}/rmd").mock(return_value=httpx.Response(200, json=fx.RMD_EXPORT_200))
    async with client:
        resp = await client.get_rmd(392, 948, include_sql=True)

    assert route.calls[0].request.url.params["include_sql"] == "true"
    assert resp.project.name == "Sales Analytics"
    assert resp.version.is_global is True
    assert len(resp.dimension_groups) == 1
    assert len(resp.fact_tables) == 1
    assert len(resp.relationships) == 1
    assert resp.exported_at is not None


@respx.mock
@pytest.mark.asyncio
async def test_list_endpoints_are_not_empty(client: DataForgeClient) -> None:
    """Regression: camelCase aliases made these lists parse as empty."""
    respx.get(f"{PFX}/data-marts").mock(return_value=httpx.Response(200, json=fx.DATA_MARTS_200))
    respx.get(f"{PFX}/fact-tables").mock(return_value=httpx.Response(200, json=fx.FACT_TABLES_200))
    respx.get(f"{PFX}/dimension-groups").mock(
        return_value=httpx.Response(200, json=fx.DIMENSION_GROUPS_200)
    )
    respx.get(f"{PFX}/connections").mock(return_value=httpx.Response(200, json=fx.CONNECTIONS_200))

    async with client:
        marts = await client.get_data_marts(392, 948)
        tables = await client.get_fact_tables(392, 948)
        groups = await client.get_dimension_groups(392, 948)
        connections = await client.get_connections(392, 948)

    assert len(marts.data_marts) == 1
    assert marts.data_marts[0].has_physical_view is False
    assert marts.data_marts[0].owner == "Алёна Зубакова"
    assert len(tables.fact_tables) == 1
    assert tables.fact_tables[0].measures_count == 12
    assert len(groups.dimension_groups) == 1
    assert groups.dimension_groups[0].primary_key.connection == "Production PostgreSQL"
    assert len(connections.connections) == 1
    assert connections.connections[0].db_type == "postgresql"


@respx.mock
@pytest.mark.asyncio
async def test_data_mart_detail_selected_elements(client: DataForgeClient) -> None:
    respx.get(f"{PFX}/data-marts/9667").mock(
        return_value=httpx.Response(200, json=fx.DATA_MART_DETAIL_200)
    )
    async with client:
        mart = await client.get_data_mart(392, 948, 9667)

    measure = mart.selected_measures[0]
    # The same measure may appear twice with different aggregation settings, so the
    # instance id and the measure id are different things.
    assert measure.instance_id == "155341"
    assert measure.measure_id == "33540"
    assert measure.aggregation_configuration["type"] == "default"
    assert mart.selected_dimensions[0].source_dimension_group_name == "Calendar"
    assert mart.selected_facts[0].include_in_result is True
    # The embedded physical view carries no connection.
    assert not hasattr(mart.physical_view, "connection")


@respx.mock
@pytest.mark.asyncio
async def test_data_mart_detail_pivot_attributes(client: DataForgeClient) -> None:
    respx.get(f"{PFX}/data-marts/9668").mock(
        return_value=httpx.Response(200, json=fx.DATA_MART_DETAIL_PIVOT_200)
    )
    async with client:
        mart = await client.get_data_mart(392, 948, 9668)
    assert len(mart.selected_measure_attributes) == 2


@respx.mock
@pytest.mark.asyncio
async def test_physical_view_fields(client: DataForgeClient) -> None:
    respx.get(f"{PFX}/data-marts/9666/view").mock(
        return_value=httpx.Response(200, json=fx.PHYSICAL_VIEW_EXISTS_200)
    )
    async with client:
        view = await client.get_data_mart_view(392, 948, 9666)

    assert view.exists is True
    assert view.status == "active"
    assert view.is_stale is False
    assert view.last_refresh_at == "2026-08-30T03:00:12.000Z"
    assert view.connection.db_type == "clickhouse"
    assert view.schema_ == "dataforge_test"


@respx.mock
@pytest.mark.asyncio
async def test_physical_view_absent(client: DataForgeClient) -> None:
    respx.get(f"{PFX}/data-marts/9666/view").mock(
        return_value=httpx.Response(200, json=fx.PHYSICAL_VIEW_ABSENT_200)
    )
    async with client:
        view = await client.get_data_mart_view(392, 948, 9666)
    assert view.exists is False
    assert view.connection is None


@respx.mock
@pytest.mark.asyncio
async def test_generate_sql_response_shape(client: DataForgeClient) -> None:
    respx.post(f"{PFX}/data-marts/9666/generate-sql").mock(
        return_value=httpx.Response(200, json=fx.GENERATE_SQL_OK_200)
    )
    async with client:
        resp = await client.generate_sql(392, 948, 9666)

    assert resp.sql_script.startswith("SELECT")
    assert resp.target_db_type == "clickhouse"
    assert resp.validation_errors == []


@respx.mock
@pytest.mark.asyncio
async def test_generate_sql_failure_is_still_200(client: DataForgeClient) -> None:
    """A generation failure is data, not an error — that is how it differs from a 404."""
    respx.post(f"{PFX}/data-marts/9666/generate-sql").mock(
        return_value=httpx.Response(200, json=fx.GENERATE_SQL_FAILED_200)
    )
    async with client:
        resp = await client.generate_sql(392, 948, 9666)

    assert resp.sql_script == ""
    assert resp.target_db_type is None
    assert resp.validation_errors[0].code == "SQL_GENERATION_FAILED"


@respx.mock
@pytest.mark.asyncio
async def test_connection_detail_short_and_full_schema(client: DataForgeClient) -> None:
    respx.get(f"{PFX}/connections/3821").mock(
        side_effect=[
            httpx.Response(200, json=fx.CONNECTION_DETAIL_200),
            httpx.Response(200, json=fx.CONNECTION_DETAIL_WITH_SCHEMA_200),
        ]
    )
    async with client:
        short = await client.get_connection(392, 948, 3821)
        full = await client.get_connection(392, 948, 3821, include_db_schema=True)

    assert short.host == "db.production.company.com"
    assert short.port == 5432
    assert short.db_tables is not None
    assert full.db_schema.tables[0].table_name == "fact_sales"
    assert full.db_schema.tables[0].columns[0].column_name == "amount"


@respx.mock
@pytest.mark.asyncio
async def test_connection_schema_container_key(client: DataForgeClient) -> None:
    """The container is named `schema`, which collides with a BaseModel attribute."""
    respx.get(f"{PFX}/connections/3821/schema").mock(
        return_value=httpx.Response(200, json=fx.CONNECTION_SCHEMA_200)
    )
    async with client:
        resp = await client.get_connection_schema(392, 948, 3821)

    assert resp.schema_.tables[0].table_name == "fact_sales"
    assert "schema" in resp.model_dump(by_alias=True)


@respx.mock
@pytest.mark.asyncio
async def test_fact_table_and_relationship_details(client: DataForgeClient) -> None:
    respx.get(f"{PFX}/fact-tables/6784").mock(
        return_value=httpx.Response(200, json=fx.FACT_TABLE_DETAIL_WITH_DEPS_200)
    )
    respx.get(f"{PFX}/relationships/501").mock(
        return_value=httpx.Response(200, json=fx.RELATIONSHIP_DETAIL_200)
    )
    respx.get(f"{PFX}/dimension-groups/1204").mock(
        return_value=httpx.Response(200, json=fx.DIMENSION_GROUP_DETAIL_200)
    )

    async with client:
        table = await client.get_fact_table(392, 948, 6784, include_dependencies=True)
        relationship = await client.get_relationship(392, 948, 501)
        group = await client.get_dimension_group(392, 948, 1204)

    assert table.measures[0].measure_type == "base"
    assert table.measures[0].dependencies[0]["name"] == "Order line"
    assert table.dimensions[0].is_from_dimension_group is True
    assert table.verification_filters[0].is_valid is True
    assert relationship.relationship_type == "many_to_one"
    assert relationship.foreign_key.connection == "Production PostgreSQL"
    assert group.dimensions[0].level == 1
    assert group.related_fact_tables[0].foreign_key_column == "date_id"


@respx.mock
@pytest.mark.asyncio
async def test_project_access_and_git_connections(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects/392/access").mock(
        return_value=httpx.Response(200, json=fx.PROJECT_ACCESS_200)
    )
    respx.get(f"{BASE}/df-api/v2/git-connections").mock(
        return_value=httpx.Response(200, json=fx.GIT_CONNECTIONS_200)
    )
    respx.get(f"{BASE}/df-api/v2/git-connections/17").mock(
        return_value=httpx.Response(200, json=fx.GIT_CONNECTION)
    )

    async with client:
        access = await client.get_project_access(392)
        listing = await client.list_git_connections()
        one = await client.get_git_connection(17)

    assert access[0].isOwner is True
    assert access[0].projectRole == "Разработчик"
    # The listing key is hyphenated on the wire.
    assert len(listing.git_connections) == 1
    assert one.platform == "gitlab"


@respx.mock
@pytest.mark.asyncio
async def test_unknown_fields_do_not_break_parsing(client: DataForgeClient) -> None:
    """The contract is extended additively; a new field must never break a live server."""
    payload = {
        "measures": [{**fx.MEASURE_ROW, "__future_field__": 1}],
        "pagination": {**fx.pagination(), "__future__": True},
        "__top_level__": "x",
    }
    respx.get(f"{PFX}/measures").mock(return_value=httpx.Response(200, json=payload))
    async with client:
        resp = await client.get_measures(392, 948)
    assert resp.measures[0].measure_name == "Total revenue"


# ---------------------------------------------------------------------------
# Non-JSON answers (the base-URL trap)
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_html_answer_becomes_a_diagnosable_error(client: DataForgeClient) -> None:
    """A base URL pointing at the site root serves the SPA, with HTTP 200.

    Before this, `resp.json()` raised and the agent saw `JSONDecodeError` - true, but
    useless. The one fact that fixes it (point DATAFORGE_BASE_URL at the API root,
    often `https://<host>/api`) now travels with the error.
    """
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(
            200,
            html="<!doctype html><html><head><title>DataForge</title></head></html>",
        )
    )

    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()

    error = exc_info.value
    assert error.code is ErrorCode.DATAFORGE_INVALID_RESPONSE
    assert "/api" in (error.hint or "")
    assert error.details["content_type"].startswith("text/html")
    assert error.details["body_preview"].startswith("<!doctype html")


@respx.mock
@pytest.mark.asyncio
async def test_json_without_a_content_type_still_parses(client: DataForgeClient) -> None:
    """Never trade a working deployment for a stricter check: the body decides."""
    respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(200, content=json.dumps(fx.PROJECTS_200).encode(), headers={})
    )
    async with client:
        resp = await client.get_projects()
    assert resp.projects
