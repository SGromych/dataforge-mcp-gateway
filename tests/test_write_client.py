"""Write client: paths, HTTP verbs and request bodies for every write endpoint."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from dataforge_mcp.dataforge.client import DataForgeClient, new_idempotency_key
from dataforge_mcp.dataforge.write_client import _ASSIGN_BODY_KEY, _ASSIGN_SEGMENT
from dataforge_mcp.dataforge.write_schemas import (
    DimensionGroupWrite,
    DimensionWrite,
    ExportGitBody,
    FactTableWrite,
    FactWrite,
    GitAuth,
    GitConnectionWrite,
    GroupMember,
    GroupMembersBody,
    ImportGitBody,
    ImportTarget,
    MeasureWrite,
    ProjectAccessWrite,
    ProjectWrite,
    RelationshipWrite,
    SourceObject,
    VerificationFilterWrite,
    VersionWrite,
)
from tests.fixtures import api_v2 as fx

BASE = "https://api.test.example.com"
PFX = f"{BASE}/df-api/v2/projects/392/versions/948"
KEY = new_idempotency_key()


@pytest.fixture
def client() -> DataForgeClient:
    return DataForgeClient(base_url=BASE, api_key="test-api-key-12345", max_retries=1)


def body_of(route: respx.Route) -> dict:
    return json.loads(route.calls[0].request.content)


SOURCE = SourceObject(
    connection="Production PostgreSQL",
    db="analytics_db",
    schema="public",
    table="dim_customer",
    column="customer_id",
)


# ---------------------------------------------------------------------------
# Projects and versions
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_project_lifecycle(client: DataForgeClient) -> None:
    create = respx.post(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(201, json={"id": "12", "name": "Sales"})
    )
    patch = respx.patch(f"{BASE}/df-api/v2/projects/12").mock(
        return_value=httpx.Response(200, json={"id": "12", "name": "Sales v2"})
    )
    delete = respx.delete(f"{BASE}/df-api/v2/projects/12").mock(return_value=httpx.Response(204))

    async with client:
        created = await client.create_project(
            ProjectWrite(name="Sales", color="#2479BC"), idempotency_key=KEY
        )
        await client.update_project(12, ProjectWrite(name="Sales v2"))
        deleted = await client.delete_project(12)

    assert created.status_code == 201
    assert body_of(create) == {"name": "Sales", "color": "#2479BC"}
    assert body_of(patch) == {"name": "Sales v2"}
    assert deleted.status_code == 204
    assert delete.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_version_lifecycle(client: DataForgeClient) -> None:
    create = respx.post(f"{BASE}/df-api/v2/projects/392/versions").mock(
        return_value=httpx.Response(201, json={"id": "34", "name": "Q1 2027"})
    )
    patch = respx.patch(PFX).mock(return_value=httpx.Response(200, json={"id": "948"}))
    respx.delete(PFX).mock(return_value=httpx.Response(204))

    async with client:
        await client.create_version(
            392, VersionWrite(name="Q1 2027", clone_from_version="33"), idempotency_key=KEY
        )
        await client.update_version(392, 948, VersionWrite(is_global=True))
        await client.delete_version(392, 948)

    assert body_of(create) == {"name": "Q1 2027", "clone_from_version": "33"}
    assert body_of(patch) == {"is_global": True}


# ---------------------------------------------------------------------------
# RMD content
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("entity", "segment", "model", "payload"),
    [
        ("measure", "measures", MeasureWrite, {"measure_name": "M", "measure_type": "Base"}),
        (
            "dimension",
            "dimensions",
            DimensionWrite,
            {"dimension_name": "D", "dimension_type": "Primary"},
        ),
        ("fact", "facts", FactWrite, {"fact_name": "F", "fact_type": "Primary"}),
    ],
)
@respx.mock
@pytest.mark.asyncio
async def test_rmd_entity_crud(
    client: DataForgeClient, entity: str, segment: str, model: type, payload: dict
) -> None:
    create = respx.post(f"{PFX}/{segment}").mock(
        return_value=httpx.Response(201, json={"id": "1", **payload})
    )
    put = respx.put(f"{PFX}/{segment}/1").mock(return_value=httpx.Response(200, json={"id": "1"}))
    patch = respx.patch(f"{PFX}/{segment}/1").mock(
        return_value=httpx.Response(200, json={"id": "1"})
    )
    delete = respx.delete(f"{PFX}/{segment}/1").mock(return_value=httpx.Response(204))

    async with client:
        await getattr(client, f"create_{entity}")(392, 948, model(**payload), idempotency_key=KEY)
        await getattr(client, f"replace_{entity}")(392, 948, 1, model(**payload))
        await getattr(client, f"update_{entity}")(392, 948, 1, model(comment="c"))
        result = await getattr(client, f"delete_{entity}")(392, 948, 1)

    assert body_of(create) == payload
    assert put.call_count == 1
    assert body_of(patch) == {"comment": "c"}
    assert result.status_code == 204
    assert delete.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_connected_source_serialized_with_schema_alias(client: DataForgeClient) -> None:
    route = respx.post(f"{PFX}/dimensions").mock(
        return_value=httpx.Response(201, json={"id": "1"})
    )
    async with client:
        await client.create_dimension(
            392,
            948,
            DimensionWrite(dimension_name="D", dimension_type="Primary", connected_source=SOURCE),
            idempotency_key=KEY,
        )

    source = body_of(route)["connected_source"]
    # The wire name is `schema`, not the python-safe `schema_`.
    assert source["schema"] == "public"
    assert source["connection"] == "Production PostgreSQL"


@respx.mock
@pytest.mark.asyncio
async def test_bulk_endpoints(client: DataForgeClient) -> None:
    from dataforge_mcp.dataforge.write_schemas import DimensionsBulk, FactsBulk, MeasuresBulk

    measures = respx.post(f"{PFX}/measures/bulk").mock(
        return_value=httpx.Response(201, json=fx.BULK_PARTIAL_207)
    )
    dimensions = respx.post(f"{PFX}/dimensions/bulk").mock(
        return_value=httpx.Response(201, json={"succeeded": [], "failed": []})
    )
    facts = respx.post(f"{PFX}/facts/bulk").mock(
        return_value=httpx.Response(201, json={"succeeded": [], "failed": []})
    )

    async with client:
        await client.bulk_write_measures(
            392,
            948,
            MeasuresBulk(measures=[MeasureWrite(measure_name="A", measure_type="Base")]),
            idempotency_key=KEY,
        )
        await client.bulk_write_dimensions(
            392,
            948,
            DimensionsBulk(
                dimensions=[DimensionWrite(dimension_name="D", dimension_type="Primary")]
            ),
            idempotency_key=KEY,
        )
        await client.bulk_write_facts(
            392,
            948,
            FactsBulk(facts=[FactWrite(fact_name="F", fact_type="Primary")]),
            idempotency_key=KEY,
        )

    assert body_of(measures)["measures"][0]["measure_name"] == "A"
    assert dimensions.call_count == 1
    assert facts.call_count == 1


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_dimension_group_membership(client: DataForgeClient) -> None:
    create = respx.post(f"{PFX}/dimension-groups").mock(
        return_value=httpx.Response(201, json={"id": "9"})
    )
    add = respx.post(f"{PFX}/dimension-groups/9/dimensions").mock(
        return_value=httpx.Response(200, json={"id": "9"})
    )
    level = respx.patch(f"{PFX}/dimension-groups/9/dimensions/724").mock(
        return_value=httpx.Response(200, json={"id": "9"})
    )
    remove = respx.delete(f"{PFX}/dimension-groups/9/dimensions/724").mock(
        return_value=httpx.Response(204)
    )

    async with client:
        await client.create_dimension_group(
            392,
            948,
            DimensionGroupWrite(name="Geography", primary_key=SOURCE),
            idempotency_key=KEY,
        )
        await client.add_group_dimensions(
            392,
            948,
            9,
            GroupMembersBody(dimensions=[GroupMember(id="724", level=3)]),
            idempotency_key=KEY,
        )
        await client.patch_group_dimension_level(392, 948, 9, 724, 2)
        await client.remove_group_dimension(392, 948, 9, 724)

    assert body_of(create)["primary_key"]["table"] == "dim_customer"
    assert body_of(add) == {"dimensions": [{"id": "724", "level": 3}]}
    assert body_of(level) == {"level": 2}
    assert remove.call_count == 1


@pytest.mark.parametrize("element_type", list(_ASSIGN_SEGMENT))
@respx.mock
@pytest.mark.asyncio
async def test_fact_table_assignment_paths_and_body_keys(
    client: DataForgeClient, element_type: str
) -> None:
    """Both the URL segment and the body key differ per element type."""
    segment = _ASSIGN_SEGMENT[element_type]
    assign = respx.post(f"{PFX}/fact-tables/6784/{segment}").mock(
        return_value=httpx.Response(201, json={"succeeded": [{"id": "501"}], "failed": []})
    )
    unassign = respx.delete(f"{PFX}/fact-tables/6784/{segment}/501").mock(
        return_value=httpx.Response(204)
    )

    async with client:
        await client.assign_to_fact_table(
            392, 948, 6784, element_type, ["501", "502"], idempotency_key=KEY
        )
        await client.unassign_from_fact_table(392, 948, 6784, element_type, 501)

    assert body_of(assign) == {_ASSIGN_BODY_KEY[element_type]: ["501", "502"]}
    assert unassign.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_assignment_partial_result(client: DataForgeClient) -> None:
    respx.post(f"{PFX}/fact-tables/6784/measures").mock(
        return_value=httpx.Response(207, json=fx.ASSIGN_PARTIAL_207)
    )
    async with client:
        result = await client.assign_to_fact_table(
            392, 948, 6784, "measure", ["501", "502"], idempotency_key=KEY
        )
    assert result.partial is True
    assert result.failed[0]["id"] == "502"


@respx.mock
@pytest.mark.asyncio
async def test_fact_table_crud(client: DataForgeClient) -> None:
    create = respx.post(f"{PFX}/fact-tables").mock(
        return_value=httpx.Response(201, json={"id": "6784"})
    )
    respx.put(f"{PFX}/fact-tables/6784").mock(return_value=httpx.Response(200, json={}))
    respx.patch(f"{PFX}/fact-tables/6784").mock(return_value=httpx.Response(200, json={}))
    respx.delete(f"{PFX}/fact-tables/6784").mock(return_value=httpx.Response(204))

    async with client:
        await client.create_fact_table(392, 948, FactTableWrite(name="Sales"), idempotency_key=KEY)
        await client.replace_fact_table(392, 948, 6784, FactTableWrite(name="Sales"))
        await client.update_fact_table(392, 948, 6784, FactTableWrite(description="d"))
        await client.delete_fact_table(392, 948, 6784)

    assert body_of(create) == {"name": "Sales"}


@respx.mock
@pytest.mark.asyncio
async def test_verification_filter_path_depends_on_fact_table(client: DataForgeClient) -> None:
    version_level = respx.post(f"{PFX}/verification-filters").mock(
        return_value=httpx.Response(201, json={"id": "77"})
    )
    table_level = respx.post(f"{PFX}/fact-tables/6784/verification-filters").mock(
        return_value=httpx.Response(201, json={"id": "78"})
    )
    delete_table_level = respx.delete(f"{PFX}/fact-tables/6784/verification-filters/78").mock(
        return_value=httpx.Response(204)
    )

    filter_body = VerificationFilterWrite(name="Positive", conditions="[Amount] > 0")
    async with client:
        await client.create_verification_filter(392, 948, filter_body, idempotency_key=KEY)
        await client.create_verification_filter(
            392, 948, filter_body, fact_table_id=6784, idempotency_key=KEY
        )
        await client.delete_verification_filter(392, 948, 78, fact_table_id=6784)

    assert version_level.call_count == 1
    assert table_level.call_count == 1
    assert delete_table_level.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_relationship_crud(client: DataForgeClient) -> None:
    create = respx.post(f"{PFX}/relationships").mock(
        return_value=httpx.Response(201, json={"id": "501"})
    )
    respx.patch(f"{PFX}/relationships/501").mock(return_value=httpx.Response(200, json={}))
    respx.delete(f"{PFX}/relationships/501").mock(return_value=httpx.Response(204))

    async with client:
        await client.create_relationship(
            392,
            948,
            RelationshipWrite(
                source_fact_table_id="6784",
                target_dimension_group_id="1204",
                foreign_key=SOURCE,
                primary_key=SOURCE,
                relationship_type="many_to_one",
            ),
            idempotency_key=KEY,
        )
        await client.update_relationship(392, 948, 501, RelationshipWrite(foreign_key=SOURCE))
        await client.delete_relationship(392, 948, 501)

    body = body_of(create)
    assert body["relationship_type"] == "many_to_one"
    assert body["foreign_key"]["connection"] == body["primary_key"]["connection"]


# ---------------------------------------------------------------------------
# Project access
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_project_access_uses_camel_case_bodies(client: DataForgeClient) -> None:
    """Access management keeps the internal API's camelCase field names."""
    grant = respx.post(f"{BASE}/df-api/v2/projects/392/access").mock(
        return_value=httpx.Response(201, json=fx.SUCCESS_FLAG)
    )
    revoke = respx.delete(f"{BASE}/df-api/v2/projects/392/access/12").mock(
        return_value=httpx.Response(200, json=fx.SUCCESS_FLAG)
    )
    owner = respx.put(f"{BASE}/df-api/v2/projects/392/owner").mock(
        return_value=httpx.Response(200, json=fx.SUCCESS_FLAG)
    )

    async with client:
        await client.set_project_access(
            392, ProjectAccessWrite(userId=12, accessLevel="developer"), idempotency_key=KEY
        )
        revoked = await client.revoke_project_access(392, 12)
        await client.transfer_project_ownership(392, 12)

    assert body_of(grant) == {"userId": 12, "accessLevel": "developer"}
    # This DELETE answers 200 with a body, unlike every other DELETE in the API.
    assert revoked.status_code == 200
    assert revoke.call_count == 1
    assert body_of(owner) == {"newOwnerId": 12}


# ---------------------------------------------------------------------------
# Version transfer
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_export_to_git(client: DataForgeClient) -> None:
    route = respx.post(f"{PFX}/export/git").mock(
        return_value=httpx.Response(200, json=fx.EXPORT_GIT_200)
    )
    async with client:
        result = await client.export_version_to_git(
            392,
            948,
            ExportGitBody(
                repository_url="https://git.example.com/x.git",
                branch="main",
                commit_message="Export",
                authentication=GitAuth(method="pat", token="secret"),
            ),
            idempotency_key=KEY,
        )

    assert result.payload["commit_hash"].startswith("3f2a9c1")
    assert body_of(route)["authentication"]["method"] == "pat"


@respx.mock
@pytest.mark.asyncio
async def test_export_to_file_sends_no_idempotency_key(client: DataForgeClient) -> None:
    """A cached response would carry an expired signed URL."""
    from dataforge_mcp.dataforge.write_schemas import ExportFileBody

    route = respx.post(f"{PFX}/export/file").mock(
        return_value=httpx.Response(200, json=fx.EXPORT_FILE_200)
    )
    async with client:
        result = await client.export_version_to_file(392, 948, ExportFileBody())

    assert "Idempotency-Key" not in route.calls[0].request.headers
    assert result.payload["file_name"].endswith(".dfexport.zip")


@respx.mock
@pytest.mark.asyncio
async def test_import_dry_runs_json_branch(client: DataForgeClient) -> None:
    from dataforge_mcp.dataforge.write_schemas import ImportSourceBody

    validate = respx.post(f"{PFX}/import/validate").mock(
        return_value=httpx.Response(200, json=fx.IMPORT_VALIDATE_200)
    )
    preview = respx.post(f"{PFX}/import/preview").mock(
        return_value=httpx.Response(200, json=fx.IMPORT_PREVIEW_200)
    )
    source = ImportSourceBody(
        source_type="git",
        repository_url="https://git.example.com/x.git",
        branch="main",
        connection_id="17",
    )

    async with client:
        validated = await client.validate_import_source(392, 948, body=source)
        previewed = await client.preview_import(392, 948, body=source)

    assert validated.payload["valid"] is True
    assert previewed.payload["preview_id"].startswith("0b1d2c3e")
    assert "Idempotency-Key" not in validate.calls[0].request.headers
    assert "Idempotency-Key" not in preview.calls[0].request.headers


@respx.mock
@pytest.mark.asyncio
async def test_import_from_git(client: DataForgeClient) -> None:
    route = respx.post(f"{PFX}/import/git").mock(
        return_value=httpx.Response(200, json=fx.IMPORT_GIT_200)
    )
    async with client:
        result = await client.import_version_from_git(
            392,
            948,
            ImportGitBody(
                repository_url="https://git.example.com/x.git",
                branch="main",
                connection_id="17",
                target=ImportTarget(method="create", version_name="staging_4711"),
                conflict_strategy="smart_merge",
            ),
            idempotency_key=KEY,
        )

    body = body_of(route)
    assert body["target"] == {"method": "create", "version_name": "staging_4711"}
    assert result.payload["target_version_id"] == "35"
    assert route.calls[0].request.headers["Idempotency-Key"] == KEY


@respx.mock
@pytest.mark.asyncio
async def test_import_from_file_is_multipart(client: DataForgeClient, tmp_path: Path) -> None:
    archive = tmp_path / "export.dfexport.zip"
    archive.write_bytes(b"PK\x03\x04 not really a zip")

    route = respx.post(f"{PFX}/import/file").mock(
        return_value=httpx.Response(200, json=fx.IMPORT_GIT_200)
    )
    async with client:
        await client.import_version_from_file(
            392,
            948,
            file_path=archive,
            target_method="replace",
            target_version_name="staging",
            conflict_strategy="overwrite",
            idempotency_key=KEY,
        )

    request = route.calls[0].request
    content = request.content.decode("utf-8", errors="replace")
    assert request.headers["content-type"].startswith("multipart/form-data")
    # Form field names contain a literal dot.
    assert 'name="target.method"' in content
    assert 'name="target.version_name"' in content
    assert "export.dfexport.zip" in content


# ---------------------------------------------------------------------------
# Git connections
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_git_connection_crud_and_test(client: DataForgeClient) -> None:
    create = respx.post(f"{BASE}/df-api/v2/git-connections").mock(
        return_value=httpx.Response(201, json=fx.GIT_CONNECTION)
    )
    respx.put(f"{BASE}/df-api/v2/git-connections/17").mock(
        return_value=httpx.Response(200, json=fx.GIT_CONNECTION)
    )
    respx.delete(f"{BASE}/df-api/v2/git-connections/17").mock(return_value=httpx.Response(204))
    test_route = respx.post(f"{BASE}/df-api/v2/git-connections/17/test").mock(
        return_value=httpx.Response(200, json=fx.GIT_CONNECTION_TEST_FAILED_200)
    )

    async with client:
        await client.create_git_connection(
            GitConnectionWrite(
                name="Config repository",
                platform="gitlab",
                repository_url="https://gitlab.example.com/x.git",
                branch="main",
                authentication=GitAuth(method="pat", token="secret"),
            ),
            idempotency_key=KEY,
        )
        await client.update_git_connection(17, GitConnectionWrite(branch="develop"))
        deleted = await client.delete_git_connection(17)
        tested = await client.test_git_connection(17)

    assert body_of(create)["platform"] == "gitlab"
    assert deleted.status_code == 204
    # A failed check is reported as data, not as an error.
    assert tested.status_code == 200
    assert tested.payload["status"] == "failed"
    assert "Idempotency-Key" not in test_route.calls[0].request.headers
