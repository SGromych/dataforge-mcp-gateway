"""Write use cases: call the API, then drop the cache scope the write touched.

Two rules hold for every operation here:

* A write never goes through ``_cached_fetch`` and never falls back to last-known-good.
  Serving a stale read as the outcome of a write would be a lie.
* Every logical write generates an ``Idempotency-Key``, which is what makes retrying a
  POST after a 5xx safe.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pydantic import ValidationError

from dataforge_mcp.dataforge.client import DataForgeClient, new_idempotency_key
from dataforge_mcp.dataforge.write_client import ElementType
from dataforge_mcp.dataforge.write_results import WriteResult
from dataforge_mcp.dataforge.write_schemas import (
    DimensionGroupWrite,
    DimensionsBulk,
    DimensionWrite,
    ExportFileBody,
    ExportGitBody,
    FactsBulk,
    FactTableWrite,
    FactWrite,
    GitConnectionWrite,
    GroupMembersBody,
    ImportGitBody,
    ImportOptions,
    ImportSourceBody,
    MeasuresBulk,
    MeasureWrite,
    ProjectAccessWrite,
    ProjectWrite,
    RelationshipWrite,
    VerificationFilterWrite,
    VersionWrite,
    WriteBody,
    WriteMode,
    require_for_mode,
    validation_error_fields,
)
from dataforge_mcp.errors import DataForgeError, ErrorCode
from dataforge_mcp.logging import get_logger

from .invalidation import WriteScope, prefixes_for

logger = get_logger(__name__)

BodyT = TypeVar("BodyT", bound=WriteBody)

_STATUS_BY_CODE = {200: "ok", 201: "created", 204: "deleted", 207: "partial"}


def parse_body(model: type[BodyT], fields: dict[str, Any]) -> BodyT:
    """Validate tool arguments against a write body.

    ``extra="forbid"`` mirrors the server's strict-body rule, and the failure is
    reshaped into the v2 error envelope so local and remote validation look identical
    to the agent.
    """
    try:
        return model.model_validate(fields)
    except ValidationError as exc:
        raise DataForgeError(
            code=ErrorCode.DATAFORGE_VALIDATION_FAILED,
            message=f"Invalid body for {model.__name__}",
            field_errors=validation_error_fields(exc),
        ) from exc


def _check_target_id(body: WriteBody, entity_id: int | None, mode: WriteMode) -> None:
    if mode in ("replace", "update") and entity_id is None:
        raise DataForgeError(
            code=ErrorCode.DATAFORGE_MISSING_REQUIRED_FIELD,
            message=f"mode={mode} requires the id of the entity to modify",
            field_errors=[{"field": "id", "code": "missing_field"}],
        )
    body_id = getattr(body, "id", None)
    if body_id is not None and entity_id is not None and str(body_id) != str(entity_id):
        raise DataForgeError(
            code=ErrorCode.DATAFORGE_ID_MISMATCH,
            message=f"id in body ({body_id}) differs from id in path ({entity_id})",
            field_errors=[{"field": "id", "code": "invalid_value"}],
        )


class WriteUseCasesMixin:
    """Write half of :class:`~dataforge_mcp.application.use_cases.SemanticService`."""

    cache: Any
    settings: Any

    def _new_client(self) -> DataForgeClient:  # provided by SemanticService
        raise NotImplementedError

    # -----------------------------------------------------------------------
    # Core
    # -----------------------------------------------------------------------

    async def _write_op(
        self,
        *,
        tool_name: str,
        scope: WriteScope,
        call: Callable[[DataForgeClient, str], Awaitable[WriteResult]],
        project_id: int | None = None,
        version_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        key = idempotency_key or new_idempotency_key()

        async with self._new_client() as client:
            result = await call(client, key)

        invalidated = []
        for prefix in prefixes_for(scope, project_id, version_id):
            if await self.cache.invalidate_prefix(prefix):
                invalidated.append(prefix)

        logger.info(
            "write_op",
            tool_name=tool_name,
            scope=scope.value,
            http_status=result.status_code,
            partial=result.partial,
            project_id=project_id,
            version_id=version_id,
            invalidated=len(invalidated),
        )

        response: dict[str, Any] = {
            "status": _STATUS_BY_CODE.get(result.status_code, "ok"),
            "http_status": result.status_code,
            "idempotency_key": key,
            "result": result.payload,
            "cache_invalidated": invalidated,
        }
        if result.partial:
            # 207 must stay visible: part of the input was rejected.
            response["failed"] = result.failed
            response["succeeded"] = result.succeeded
        return response

    # -----------------------------------------------------------------------
    # Projects and versions
    # -----------------------------------------------------------------------

    async def create_project(
        self, idempotency_key: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        body = parse_body(ProjectWrite, fields)
        require_for_mode(body, "project", "create")
        return await self._write_op(
            tool_name="df_create_project",
            scope=WriteScope.GLOBAL,
            call=lambda c, key: c.create_project(body, idempotency_key=key),
            idempotency_key=idempotency_key,
        )

    async def update_project(self, project_id: int, **fields: Any) -> dict[str, Any]:
        body = parse_body(ProjectWrite, fields)
        _check_target_id(body, project_id, "update")
        return await self._write_op(
            tool_name="df_update_project",
            scope=WriteScope.PROJECT,
            call=lambda c, key: c.update_project(project_id, body),
            project_id=project_id,
        )

    async def delete_project(self, project_id: int) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_delete_project",
            scope=WriteScope.PROJECT,
            call=lambda c, key: c.delete_project(project_id),
            project_id=project_id,
        )

    async def create_version(
        self, project_id: int, idempotency_key: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        body = parse_body(VersionWrite, fields)
        require_for_mode(body, "version", "create")
        return await self._write_op(
            tool_name="df_create_version",
            scope=WriteScope.PROJECT,
            call=lambda c, key: c.create_version(project_id, body, idempotency_key=key),
            project_id=project_id,
            idempotency_key=idempotency_key,
        )

    async def update_version(
        self, project_id: int, version_id: int, **fields: Any
    ) -> dict[str, Any]:
        body = parse_body(VersionWrite, fields)
        _check_target_id(body, version_id, "update")
        return await self._write_op(
            tool_name="df_update_version",
            scope=WriteScope.PROJECT,
            call=lambda c, key: c.update_version(project_id, version_id, body),
            project_id=project_id,
            version_id=version_id,
        )

    async def delete_version(self, project_id: int, version_id: int) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_delete_version",
            scope=WriteScope.PROJECT,
            call=lambda c, key: c.delete_version(project_id, version_id),
            project_id=project_id,
            version_id=version_id,
        )

    # -----------------------------------------------------------------------
    # RMD content — one generic implementation for measures/dimensions/facts
    # -----------------------------------------------------------------------

    async def _write_rmd_entity(
        self,
        *,
        entity: str,
        tool_name: str,
        model: type[WriteBody],
        project_id: int,
        version_id: int,
        mode: WriteMode,
        entity_id: int | None,
        idempotency_key: str | None,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        body = parse_body(model, fields)
        require_for_mode(body, entity, mode)
        _check_target_id(body, entity_id, mode)

        create = {
            "measure": "create_measure",
            "dimension": "create_dimension",
            "fact": "create_fact",
        }
        replace = {
            "measure": "replace_measure",
            "dimension": "replace_dimension",
            "fact": "replace_fact",
        }
        update = {
            "measure": "update_measure",
            "dimension": "update_dimension",
            "fact": "update_fact",
        }

        async def call(client: DataForgeClient, key: str) -> WriteResult:
            if mode == "create":
                method = getattr(client, create[entity])
                return await method(project_id, version_id, body, idempotency_key=key)
            method = getattr(client, (replace if mode == "replace" else update)[entity])
            return await method(project_id, version_id, entity_id, body)

        return await self._write_op(
            tool_name=tool_name,
            scope=WriteScope.VERSION,
            call=call,
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def write_measure(
        self,
        project_id: int,
        version_id: int,
        mode: WriteMode = "create",
        measure_id: int | None = None,
        idempotency_key: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        return await self._write_rmd_entity(
            entity="measure",
            tool_name="df_write_measure",
            model=MeasureWrite,
            project_id=project_id,
            version_id=version_id,
            mode=mode,
            entity_id=measure_id,
            idempotency_key=idempotency_key,
            fields=fields,
        )

    async def write_dimension(
        self,
        project_id: int,
        version_id: int,
        mode: WriteMode = "create",
        dimension_id: int | None = None,
        idempotency_key: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        return await self._write_rmd_entity(
            entity="dimension",
            tool_name="df_write_dimension",
            model=DimensionWrite,
            project_id=project_id,
            version_id=version_id,
            mode=mode,
            entity_id=dimension_id,
            idempotency_key=idempotency_key,
            fields=fields,
        )

    async def write_fact(
        self,
        project_id: int,
        version_id: int,
        mode: WriteMode = "create",
        fact_id: int | None = None,
        idempotency_key: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        return await self._write_rmd_entity(
            entity="fact",
            tool_name="df_write_fact",
            model=FactWrite,
            project_id=project_id,
            version_id=version_id,
            mode=mode,
            entity_id=fact_id,
            idempotency_key=idempotency_key,
            fields=fields,
        )

    async def delete_measure(
        self, project_id: int, version_id: int, measure_id: int
    ) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_delete_measure",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.delete_measure(project_id, version_id, measure_id),
            project_id=project_id,
            version_id=version_id,
        )

    async def delete_dimension(
        self, project_id: int, version_id: int, dimension_id: int
    ) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_delete_dimension",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.delete_dimension(project_id, version_id, dimension_id),
            project_id=project_id,
            version_id=version_id,
        )

    async def delete_fact(self, project_id: int, version_id: int, fact_id: int) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_delete_fact",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.delete_fact(project_id, version_id, fact_id),
            project_id=project_id,
            version_id=version_id,
        )

    async def bulk_write_measures(
        self,
        project_id: int,
        version_id: int,
        measures: list[dict[str, Any]],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body = parse_body(MeasuresBulk, {"measures": measures})
        return await self._write_op(
            tool_name="df_bulk_write_measures",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.bulk_write_measures(
                project_id, version_id, body, idempotency_key=key
            ),
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def bulk_write_dimensions(
        self,
        project_id: int,
        version_id: int,
        dimensions: list[dict[str, Any]],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body = parse_body(DimensionsBulk, {"dimensions": dimensions})
        return await self._write_op(
            tool_name="df_bulk_write_dimensions",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.bulk_write_dimensions(
                project_id, version_id, body, idempotency_key=key
            ),
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def bulk_write_facts(
        self,
        project_id: int,
        version_id: int,
        facts: list[dict[str, Any]],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body = parse_body(FactsBulk, {"facts": facts})
        return await self._write_op(
            tool_name="df_bulk_write_facts",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.bulk_write_facts(
                project_id, version_id, body, idempotency_key=key
            ),
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    # -----------------------------------------------------------------------
    # Dimension groups
    # -----------------------------------------------------------------------

    async def write_dimension_group(
        self,
        project_id: int,
        version_id: int,
        mode: WriteMode = "create",
        dimension_group_id: int | None = None,
        idempotency_key: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        body = parse_body(DimensionGroupWrite, fields)
        require_for_mode(body, "dimension_group", mode)
        _check_target_id(body, dimension_group_id, mode)

        async def call(client: DataForgeClient, key: str) -> WriteResult:
            if mode == "create":
                return await client.create_dimension_group(
                    project_id, version_id, body, idempotency_key=key
                )
            method = (
                client.replace_dimension_group
                if mode == "replace"
                else client.update_dimension_group
            )
            return await method(project_id, version_id, dimension_group_id, body)

        return await self._write_op(
            tool_name="df_write_dimension_group",
            scope=WriteScope.VERSION,
            call=call,
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def delete_dimension_group(
        self, project_id: int, version_id: int, dimension_group_id: int
    ) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_delete_dimension_group",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.delete_dimension_group(
                project_id, version_id, dimension_group_id
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def set_group_dimensions(
        self,
        project_id: int,
        version_id: int,
        dimension_group_id: int,
        dimensions: list[dict[str, Any]],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body = parse_body(GroupMembersBody, {"dimensions": dimensions})
        return await self._write_op(
            tool_name="df_set_group_dimensions",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.add_group_dimensions(
                project_id, version_id, dimension_group_id, body, idempotency_key=key
            ),
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def remove_group_dimension(
        self, project_id: int, version_id: int, dimension_group_id: int, dimension_id: int
    ) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_remove_group_dimension",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.remove_group_dimension(
                project_id, version_id, dimension_group_id, dimension_id
            ),
            project_id=project_id,
            version_id=version_id,
        )

    # -----------------------------------------------------------------------
    # Fact tables
    # -----------------------------------------------------------------------

    async def write_fact_table(
        self,
        project_id: int,
        version_id: int,
        mode: WriteMode = "create",
        fact_table_id: int | None = None,
        idempotency_key: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        body = parse_body(FactTableWrite, fields)
        require_for_mode(body, "fact_table", mode)
        _check_target_id(body, fact_table_id, mode)

        async def call(client: DataForgeClient, key: str) -> WriteResult:
            if mode == "create":
                return await client.create_fact_table(
                    project_id, version_id, body, idempotency_key=key
                )
            method = client.replace_fact_table if mode == "replace" else client.update_fact_table
            return await method(project_id, version_id, fact_table_id, body)

        return await self._write_op(
            tool_name="df_write_fact_table",
            scope=WriteScope.VERSION,
            call=call,
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def delete_fact_table(
        self, project_id: int, version_id: int, fact_table_id: int
    ) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_delete_fact_table",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.delete_fact_table(project_id, version_id, fact_table_id),
            project_id=project_id,
            version_id=version_id,
        )

    async def assign_to_fact_table(
        self,
        project_id: int,
        version_id: int,
        fact_table_id: int,
        element_type: ElementType,
        element_ids: list[str],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_assign_to_fact_table",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.assign_to_fact_table(
                project_id,
                version_id,
                fact_table_id,
                element_type,
                [str(i) for i in element_ids],
                idempotency_key=key,
            ),
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def unassign_from_fact_table(
        self,
        project_id: int,
        version_id: int,
        fact_table_id: int,
        element_type: ElementType,
        element_id: int,
    ) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_unassign_from_fact_table",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.unassign_from_fact_table(
                project_id, version_id, fact_table_id, element_type, element_id
            ),
            project_id=project_id,
            version_id=version_id,
        )

    # -----------------------------------------------------------------------
    # Verification filters (version level and fact-table level)
    # -----------------------------------------------------------------------

    async def write_verification_filter(
        self,
        project_id: int,
        version_id: int,
        mode: WriteMode = "create",
        filter_id: int | None = None,
        fact_table_id: int | None = None,
        idempotency_key: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        body = parse_body(VerificationFilterWrite, fields)
        require_for_mode(body, "verification_filter", mode)
        _check_target_id(body, filter_id, mode)

        async def call(client: DataForgeClient, key: str) -> WriteResult:
            if mode == "create":
                return await client.create_verification_filter(
                    project_id,
                    version_id,
                    body,
                    fact_table_id=fact_table_id,
                    idempotency_key=key,
                )
            method = (
                client.replace_verification_filter
                if mode == "replace"
                else client.update_verification_filter
            )
            return await method(
                project_id, version_id, filter_id, body, fact_table_id=fact_table_id
            )

        return await self._write_op(
            tool_name="df_write_verification_filter",
            scope=WriteScope.VERSION,
            call=call,
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def delete_verification_filter(
        self,
        project_id: int,
        version_id: int,
        filter_id: int,
        fact_table_id: int | None = None,
    ) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_delete_verification_filter",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.delete_verification_filter(
                project_id, version_id, filter_id, fact_table_id=fact_table_id
            ),
            project_id=project_id,
            version_id=version_id,
        )

    # -----------------------------------------------------------------------
    # Relationships
    # -----------------------------------------------------------------------

    async def write_relationship(
        self,
        project_id: int,
        version_id: int,
        mode: WriteMode = "create",
        relationship_id: int | None = None,
        idempotency_key: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        body = parse_body(RelationshipWrite, fields)
        require_for_mode(body, "relationship", mode)
        _check_target_id(body, relationship_id, mode)

        async def call(client: DataForgeClient, key: str) -> WriteResult:
            if mode == "create":
                return await client.create_relationship(
                    project_id, version_id, body, idempotency_key=key
                )
            method = (
                client.replace_relationship if mode == "replace" else client.update_relationship
            )
            return await method(project_id, version_id, relationship_id, body)

        return await self._write_op(
            tool_name="df_write_relationship",
            scope=WriteScope.VERSION,
            call=call,
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def delete_relationship(
        self, project_id: int, version_id: int, relationship_id: int
    ) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_delete_relationship",
            scope=WriteScope.VERSION,
            call=lambda c, key: c.delete_relationship(project_id, version_id, relationship_id),
            project_id=project_id,
            version_id=version_id,
        )

    # -----------------------------------------------------------------------
    # Project access
    # -----------------------------------------------------------------------

    async def set_project_access(
        self,
        project_id: int,
        user_id: int,
        access_level: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        body = parse_body(ProjectAccessWrite, {"userId": user_id, "accessLevel": access_level})
        return await self._write_op(
            tool_name="df_set_project_access",
            scope=WriteScope.PROJECT,
            call=lambda c, key: c.set_project_access(project_id, body, idempotency_key=key),
            project_id=project_id,
            idempotency_key=idempotency_key,
        )

    async def revoke_project_access(self, project_id: int, user_id: int) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_revoke_project_access",
            scope=WriteScope.PROJECT,
            call=lambda c, key: c.revoke_project_access(project_id, user_id),
            project_id=project_id,
        )

    async def transfer_project_ownership(
        self, project_id: int, new_owner_id: int
    ) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_transfer_project_ownership",
            scope=WriteScope.PROJECT,
            call=lambda c, key: c.transfer_project_ownership(project_id, new_owner_id),
            project_id=project_id,
        )

    # -----------------------------------------------------------------------
    # Version transfer
    # -----------------------------------------------------------------------

    async def export_version_to_git(
        self, project_id: int, version_id: int, idempotency_key: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        body = parse_body(ExportGitBody, fields)
        return await self._write_op(
            tool_name="df_export_version_to_git",
            scope=WriteScope.GIT,
            call=lambda c, key: c.export_version_to_git(
                project_id, version_id, body, idempotency_key=key
            ),
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def export_version_to_file(
        self, project_id: int, version_id: int, **fields: Any
    ) -> dict[str, Any]:
        body = parse_body(ExportFileBody, fields)
        return await self._write_op(
            tool_name="df_export_version_to_file",
            scope=WriteScope.GIT,
            call=lambda c, key: c.export_version_to_file(project_id, version_id, body),
            project_id=project_id,
            version_id=version_id,
        )

    async def check_import_source(
        self, project_id: int, version_id: int, file_path: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        body = parse_body(ImportSourceBody, fields) if fields else None
        return await self._write_op(
            tool_name="df_check_import_source",
            scope=WriteScope.GIT,
            call=lambda c, key: c.validate_import_source(
                project_id, version_id, body=body, file_path=file_path
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def preview_import(
        self, project_id: int, version_id: int, file_path: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        body = parse_body(ImportSourceBody, fields) if fields else None
        return await self._write_op(
            tool_name="df_preview_import",
            scope=WriteScope.GIT,
            call=lambda c, key: c.preview_import(
                project_id, version_id, body=body, file_path=file_path
            ),
            project_id=project_id,
            version_id=version_id,
        )

    async def import_version_from_git(
        self, project_id: int, version_id: int, idempotency_key: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        body = parse_body(ImportGitBody, fields)
        return await self._write_op(
            tool_name="df_import_version_from_git",
            scope=WriteScope.PROJECT,
            call=lambda c, key: c.import_version_from_git(
                project_id, version_id, body, idempotency_key=key
            ),
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    async def import_version_from_file(
        self,
        project_id: int,
        version_id: int,
        file_path: str,
        target_version_name: str,
        target_method: str = "create",
        conflict_strategy: str | None = None,
        encryption_password: str | None = None,
        idempotency_key: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        parsed_options = parse_body(ImportOptions, options) if options else None
        return await self._write_op(
            tool_name="df_import_version_from_file",
            scope=WriteScope.PROJECT,
            call=lambda c, key: c.import_version_from_file(
                project_id,
                version_id,
                file_path=file_path,
                target_method=target_method,
                target_version_name=target_version_name,
                conflict_strategy=conflict_strategy,
                options=parsed_options,
                encryption_password=encryption_password,
                idempotency_key=key,
            ),
            project_id=project_id,
            version_id=version_id,
            idempotency_key=idempotency_key,
        )

    # -----------------------------------------------------------------------
    # Git connections
    # -----------------------------------------------------------------------

    async def create_git_connection(
        self, idempotency_key: str | None = None, **fields: Any
    ) -> dict[str, Any]:
        body = parse_body(GitConnectionWrite, fields)
        require_for_mode(body, "git_connection", "create")
        return await self._write_op(
            tool_name="df_create_git_connection",
            scope=WriteScope.GIT,
            call=lambda c, key: c.create_git_connection(body, idempotency_key=key),
            idempotency_key=idempotency_key,
        )

    async def update_git_connection(self, connection_id: int, **fields: Any) -> dict[str, Any]:
        body = parse_body(GitConnectionWrite, fields)
        return await self._write_op(
            tool_name="df_update_git_connection",
            scope=WriteScope.GIT,
            call=lambda c, key: c.update_git_connection(connection_id, body),
        )

    async def delete_git_connection(self, connection_id: int) -> dict[str, Any]:
        return await self._write_op(
            tool_name="df_delete_git_connection",
            scope=WriteScope.GIT,
            call=lambda c, key: c.delete_git_connection(connection_id),
        )

    async def test_git_connection(self, connection_id: int) -> dict[str, Any]:
        """A failed check answers 200 with status "failed" — it is not an error."""
        return await self._write_op(
            tool_name="df_test_git_connection",
            scope=WriteScope.GIT,
            call=lambda c, key: c.test_git_connection(connection_id),
        )
