"""Transport behaviour: retries, idempotency and write result shapes."""

from __future__ import annotations

import httpx
import pytest
import respx

from dataforge_mcp.dataforge.client import DataForgeClient, new_idempotency_key
from dataforge_mcp.dataforge.write_schemas import MeasuresBulk, MeasureWrite
from dataforge_mcp.errors import DataForgeError, ErrorCode
from tests.fixtures import api_v2 as fx

BASE = "https://api.test.example.com"
PFX = f"{BASE}/df-api/v2/projects/392/versions/948"


@pytest.fixture
def client() -> DataForgeClient:
    return DataForgeClient(base_url=BASE, api_key="test-api-key-12345", max_retries=3)


# ---------------------------------------------------------------------------
# Retries
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_5xx_is_retried_for_reads(client: DataForgeClient) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json=fx.PROJECTS_200),
        ]
    )
    async with client:
        resp = await client.get_projects()
    assert route.call_count == 2
    assert len(resp.projects) == 2


@respx.mock
@pytest.mark.asyncio
async def test_5xx_exhausts_retries(client: DataForgeClient) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects").mock(return_value=httpx.Response(503))
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert route.call_count == 3
    assert exc_info.value.code is ErrorCode.DATAFORGE_SERVER_ERROR
    assert exc_info.value.retryable is True


@respx.mock
@pytest.mark.asyncio
async def test_4xx_is_not_retried(client: DataForgeClient) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(404, json=fx.ERR_404_PROJECT)
    )
    async with client:
        with pytest.raises(DataForgeError):
            await client.get_projects()
    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_429_is_not_retried(client: DataForgeClient) -> None:
    route = respx.get(f"{BASE}/df-api/v2/projects").mock(
        return_value=httpx.Response(429, json=fx.ERR_429_RATE_LIMIT, headers=fx.RATE_LIMIT_HEADERS)
    )
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()

    assert route.call_count == 1
    error = exc_info.value
    assert error.code is ErrorCode.DATAFORGE_RATE_LIMIT_EXCEEDED
    assert error.retry_after_seconds == 1780000000.0


@respx.mock
@pytest.mark.asyncio
async def test_timeout_is_retried_for_reads(client: DataForgeClient) -> None:
    respx.get(f"{BASE}/df-api/v2/projects").mock(side_effect=httpx.ReadTimeout("timed out"))
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.get_projects()
    assert exc_info.value.code is ErrorCode.DATAFORGE_TIMEOUT


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_post_with_key_sends_header_and_is_retried(client: DataForgeClient) -> None:
    key = new_idempotency_key()
    route = respx.post(f"{PFX}/measures").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(201, json=fx.MEASURE_CREATED_201),
        ]
    )
    async with client:
        result = await client.create_measure(
            392, 948, MeasureWrite(measure_name="X", measure_type="Base"), idempotency_key=key
        )

    assert route.call_count == 2
    # The same key on the retry is what makes repeating a POST safe.
    assert {c.request.headers["Idempotency-Key"] for c in route.calls} == {key}
    assert result.status_code == 201


@respx.mock
@pytest.mark.asyncio
async def test_post_without_key_is_not_retried(client: DataForgeClient) -> None:
    route = respx.post(f"{PFX}/measures").mock(return_value=httpx.Response(500))
    async with client:
        with pytest.raises(DataForgeError):
            await client.create_measure(
                392, 948, MeasureWrite(measure_name="X", measure_type="Base")
            )
    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_post_timeout_without_key_flags_possibly_applied(client: DataForgeClient) -> None:
    respx.post(f"{PFX}/measures").mock(side_effect=httpx.ReadTimeout("timed out"))
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.create_measure(
                392, 948, MeasureWrite(measure_name="X", measure_type="Base")
            )

    error = exc_info.value
    assert error.code is ErrorCode.DATAFORGE_TIMEOUT
    assert error.details["possibly_applied"] is True
    assert "Verify the current state" in error.hint


@pytest.mark.asyncio
async def test_invalid_idempotency_key_rejected_locally(client: DataForgeClient) -> None:
    async with client:
        with pytest.raises(DataForgeError) as exc_info:
            await client.create_measure(
                392,
                948,
                MeasureWrite(measure_name="X", measure_type="Base"),
                idempotency_key="not-a-uuid",
            )
    assert exc_info.value.code is ErrorCode.DATAFORGE_INVALID_IDEMPOTENCY_KEY


@respx.mock
@pytest.mark.asyncio
async def test_idempotency_in_progress_is_retried(client: DataForgeClient) -> None:
    """409 in-progress is usually our own retry catching up with the original call."""
    route = respx.post(f"{PFX}/measures").mock(
        side_effect=[
            httpx.Response(409, json=fx.ERR_409_IDEMPOTENCY_IN_PROGRESS),
            httpx.Response(201, json=fx.MEASURE_CREATED_201),
        ]
    )
    async with client:
        result = await client.create_measure(
            392,
            948,
            MeasureWrite(measure_name="X", measure_type="Base"),
            idempotency_key=new_idempotency_key(),
        )
    assert route.call_count == 2
    assert result.status_code == 201


@respx.mock
@pytest.mark.asyncio
async def test_no_idempotency_key_where_api_ignores_it(client: DataForgeClient) -> None:
    """generate-sql, export/file and the dry runs explicitly ignore the header."""
    route = respx.post(f"{PFX}/data-marts/9666/generate-sql").mock(
        return_value=httpx.Response(200, json=fx.GENERATE_SQL_OK_200)
    )
    async with client:
        await client.generate_sql(392, 948, 9666)
    assert "Idempotency-Key" not in route.calls[0].request.headers


# ---------------------------------------------------------------------------
# Write result shapes
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_204_yields_empty_payload(client: DataForgeClient) -> None:
    respx.delete(f"{PFX}/measures/1000").mock(return_value=httpx.Response(204))
    async with client:
        result = await client.delete_measure(392, 948, 1000)
    assert result.status_code == 204
    assert result.payload is None
    assert result.partial is False


@respx.mock
@pytest.mark.asyncio
async def test_207_is_marked_partial(client: DataForgeClient) -> None:
    respx.post(f"{PFX}/measures/bulk").mock(
        return_value=httpx.Response(207, json=fx.BULK_PARTIAL_207)
    )
    async with client:
        result = await client.bulk_write_measures(
            392,
            948,
            MeasuresBulk(measures=[MeasureWrite(measure_name="A", measure_type="Base")]),
            idempotency_key=new_idempotency_key(),
        )

    assert result.status_code == 207
    assert result.partial is True
    assert result.failed[0]["error"]["code"] == "duplicate_name"
    assert len(result.succeeded) == 1


@respx.mock
@pytest.mark.asyncio
async def test_body_omits_unset_fields_but_keeps_explicit_null(client: DataForgeClient) -> None:
    """exclude_unset, not exclude_none: an explicit null is meaningful to the API."""
    route = respx.patch(f"{PFX}/measures/1000").mock(
        return_value=httpx.Response(200, json=fx.MEASURE_CREATED_201)
    )
    async with client:
        await client.update_measure(
            392, 948, 1000, MeasureWrite(measure_description=None, comment="hi")
        )

    import json

    body = json.loads(route.calls[0].request.content)
    assert body == {"measure_description": None, "comment": "hi"}
