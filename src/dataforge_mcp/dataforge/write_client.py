"""Write endpoints of the DataForge Public API v2 (doc sections 9.9.6–9.9.11).

Every method here mutates DataForge. Conventions enforced by the transport layer:
POST creates (201), POST ``/bulk`` and assignment calls may answer 207, PUT fully
replaces (unset optional fields are reset), PATCH updates partially, DELETE answers 204.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx

from .schemas import GitConnectionTestResponse
from .write_results import WriteResult
from .write_schemas import (
    DimensionGroupWrite,
    DimensionsBulk,
    DimensionWrite,
    ExportFileBody,
    ExportGitBody,
    FactsBulk,
    FactTableWrite,
    FactWrite,
    GitConnectionWrite,
    GroupLevelBody,
    GroupMembersBody,
    ImportGitBody,
    ImportOptions,
    ImportSourceBody,
    MeasuresBulk,
    MeasureWrite,
    ProjectAccessWrite,
    ProjectWrite,
    RelationshipWrite,
    TransferOwnerBody,
    VerificationFilterWrite,
    VersionWrite,
    WriteBody,
)

ElementType = Literal["measure", "dimension", "fact", "dimension_group"]

# URL segment and request-body key differ per element type (doc 9.9.6.33–9.9.6.40).
_ASSIGN_SEGMENT: dict[str, str] = {
    "measure": "measures",
    "dimension": "dimensions",
    "fact": "facts",
    "dimension_group": "dimension-groups",
}
_ASSIGN_BODY_KEY: dict[str, str] = {
    "measure": "measure_ids",
    "dimension": "dimension_ids",
    "fact": "fact_ids",
    "dimension_group": "dimension_group_ids",
}


class _Transport(Protocol):
    async def _write(
        self,
        method: str,
        path: str,
        body: WriteBody | dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
        params: dict[str, Any] | None = None,
        timeout: httpx.Timeout | None = None,
        files: Any = None,
        data: dict[str, Any] | None = None,
    ) -> WriteResult: ...

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response: ...

    @staticmethod
    def _v2_prefix(project_id: int, version_id: int) -> str: ...

    @staticmethod
    def _project_prefix(project_id: int) -> str: ...


class WriteMixin:
    """Write half of :class:`~dataforge_mcp.dataforge.client.DataForgeClient`."""

    # -- projects -----------------------------------------------------------

    async def create_project(
        self: _Transport, body: ProjectWrite, *, idempotency_key: str | None = None
    ) -> WriteResult:
        return await self._write(
            "POST", "/df-api/v2/projects", body, idempotency_key=idempotency_key
        )

    async def update_project(self: _Transport, project_id: int, body: ProjectWrite) -> WriteResult:
        return await self._write("PATCH", self._project_prefix(project_id), body)

    async def delete_project(self: _Transport, project_id: int) -> WriteResult:
        return await self._write("DELETE", self._project_prefix(project_id))

    # -- versions -----------------------------------------------------------

    async def create_version(
        self: _Transport,
        project_id: int,
        body: VersionWrite,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._project_prefix(project_id)}/versions",
            body,
            idempotency_key=idempotency_key,
        )

    async def update_version(
        self: _Transport, project_id: int, version_id: int, body: VersionWrite
    ) -> WriteResult:
        return await self._write("PATCH", self._v2_prefix(project_id, version_id), body)

    async def delete_version(self: _Transport, project_id: int, version_id: int) -> WriteResult:
        return await self._write("DELETE", self._v2_prefix(project_id, version_id))

    # -- measures -----------------------------------------------------------

    async def create_measure(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: MeasureWrite,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/measures",
            body,
            idempotency_key=idempotency_key,
        )

    async def replace_measure(
        self: _Transport, project_id: int, version_id: int, measure_id: int, body: MeasureWrite
    ) -> WriteResult:
        return await self._write(
            "PUT", f"{self._v2_prefix(project_id, version_id)}/measures/{measure_id}", body
        )

    async def update_measure(
        self: _Transport, project_id: int, version_id: int, measure_id: int, body: MeasureWrite
    ) -> WriteResult:
        return await self._write(
            "PATCH", f"{self._v2_prefix(project_id, version_id)}/measures/{measure_id}", body
        )

    async def delete_measure(
        self: _Transport, project_id: int, version_id: int, measure_id: int
    ) -> WriteResult:
        return await self._write(
            "DELETE", f"{self._v2_prefix(project_id, version_id)}/measures/{measure_id}"
        )

    async def bulk_write_measures(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: MeasuresBulk,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/measures/bulk",
            body,
            idempotency_key=idempotency_key,
        )

    # -- dimensions ---------------------------------------------------------

    async def create_dimension(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: DimensionWrite,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/dimensions",
            body,
            idempotency_key=idempotency_key,
        )

    async def replace_dimension(
        self: _Transport,
        project_id: int,
        version_id: int,
        dimension_id: int,
        body: DimensionWrite,
    ) -> WriteResult:
        return await self._write(
            "PUT", f"{self._v2_prefix(project_id, version_id)}/dimensions/{dimension_id}", body
        )

    async def update_dimension(
        self: _Transport,
        project_id: int,
        version_id: int,
        dimension_id: int,
        body: DimensionWrite,
    ) -> WriteResult:
        return await self._write(
            "PATCH", f"{self._v2_prefix(project_id, version_id)}/dimensions/{dimension_id}", body
        )

    async def delete_dimension(
        self: _Transport, project_id: int, version_id: int, dimension_id: int
    ) -> WriteResult:
        return await self._write(
            "DELETE", f"{self._v2_prefix(project_id, version_id)}/dimensions/{dimension_id}"
        )

    async def bulk_write_dimensions(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: DimensionsBulk,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/dimensions/bulk",
            body,
            idempotency_key=idempotency_key,
        )

    # -- facts --------------------------------------------------------------

    async def create_fact(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: FactWrite,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/facts",
            body,
            idempotency_key=idempotency_key,
        )

    async def replace_fact(
        self: _Transport, project_id: int, version_id: int, fact_id: int, body: FactWrite
    ) -> WriteResult:
        return await self._write(
            "PUT", f"{self._v2_prefix(project_id, version_id)}/facts/{fact_id}", body
        )

    async def update_fact(
        self: _Transport, project_id: int, version_id: int, fact_id: int, body: FactWrite
    ) -> WriteResult:
        return await self._write(
            "PATCH", f"{self._v2_prefix(project_id, version_id)}/facts/{fact_id}", body
        )

    async def delete_fact(
        self: _Transport, project_id: int, version_id: int, fact_id: int
    ) -> WriteResult:
        return await self._write(
            "DELETE", f"{self._v2_prefix(project_id, version_id)}/facts/{fact_id}"
        )

    async def bulk_write_facts(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: FactsBulk,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/facts/bulk",
            body,
            idempotency_key=idempotency_key,
        )

    # -- dimension groups ---------------------------------------------------

    async def create_dimension_group(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: DimensionGroupWrite,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/dimension-groups",
            body,
            idempotency_key=idempotency_key,
        )

    async def replace_dimension_group(
        self: _Transport,
        project_id: int,
        version_id: int,
        dimension_group_id: int,
        body: DimensionGroupWrite,
    ) -> WriteResult:
        return await self._write(
            "PUT",
            f"{self._v2_prefix(project_id, version_id)}/dimension-groups/{dimension_group_id}",
            body,
        )

    async def update_dimension_group(
        self: _Transport,
        project_id: int,
        version_id: int,
        dimension_group_id: int,
        body: DimensionGroupWrite,
    ) -> WriteResult:
        return await self._write(
            "PATCH",
            f"{self._v2_prefix(project_id, version_id)}/dimension-groups/{dimension_group_id}",
            body,
        )

    async def delete_dimension_group(
        self: _Transport, project_id: int, version_id: int, dimension_group_id: int
    ) -> WriteResult:
        return await self._write(
            "DELETE",
            f"{self._v2_prefix(project_id, version_id)}/dimension-groups/{dimension_group_id}",
        )

    async def add_group_dimensions(
        self: _Transport,
        project_id: int,
        version_id: int,
        dimension_group_id: int,
        body: GroupMembersBody,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        """Add members and/or re-level existing ones. All-or-nothing, answers 200."""
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}"
            f"/dimension-groups/{dimension_group_id}/dimensions",
            body,
            idempotency_key=idempotency_key,
        )

    async def patch_group_dimension_level(
        self: _Transport,
        project_id: int,
        version_id: int,
        dimension_group_id: int,
        dimension_id: int,
        level: int,
    ) -> WriteResult:
        return await self._write(
            "PATCH",
            f"{self._v2_prefix(project_id, version_id)}"
            f"/dimension-groups/{dimension_group_id}/dimensions/{dimension_id}",
            GroupLevelBody(level=level),
        )

    async def remove_group_dimension(
        self: _Transport,
        project_id: int,
        version_id: int,
        dimension_group_id: int,
        dimension_id: int,
    ) -> WriteResult:
        return await self._write(
            "DELETE",
            f"{self._v2_prefix(project_id, version_id)}"
            f"/dimension-groups/{dimension_group_id}/dimensions/{dimension_id}",
        )

    # -- fact tables --------------------------------------------------------

    async def create_fact_table(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: FactTableWrite,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/fact-tables",
            body,
            idempotency_key=idempotency_key,
        )

    async def replace_fact_table(
        self: _Transport,
        project_id: int,
        version_id: int,
        fact_table_id: int,
        body: FactTableWrite,
    ) -> WriteResult:
        return await self._write(
            "PUT", f"{self._v2_prefix(project_id, version_id)}/fact-tables/{fact_table_id}", body
        )

    async def update_fact_table(
        self: _Transport,
        project_id: int,
        version_id: int,
        fact_table_id: int,
        body: FactTableWrite,
    ) -> WriteResult:
        return await self._write(
            "PATCH", f"{self._v2_prefix(project_id, version_id)}/fact-tables/{fact_table_id}", body
        )

    async def delete_fact_table(
        self: _Transport, project_id: int, version_id: int, fact_table_id: int
    ) -> WriteResult:
        return await self._write(
            "DELETE", f"{self._v2_prefix(project_id, version_id)}/fact-tables/{fact_table_id}"
        )

    async def assign_to_fact_table(
        self: _Transport,
        project_id: int,
        version_id: int,
        fact_table_id: int,
        element_type: ElementType,
        element_ids: list[str],
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        """Attach existing elements to a fact table. 201, or 207 if some were rejected."""
        segment = _ASSIGN_SEGMENT[element_type]
        body = {_ASSIGN_BODY_KEY[element_type]: element_ids}
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/fact-tables/{fact_table_id}/{segment}",
            body,
            idempotency_key=idempotency_key,
        )

    async def unassign_from_fact_table(
        self: _Transport,
        project_id: int,
        version_id: int,
        fact_table_id: int,
        element_type: ElementType,
        element_id: int,
    ) -> WriteResult:
        """Detach one element. The element itself stays in the RMD."""
        segment = _ASSIGN_SEGMENT[element_type]
        return await self._write(
            "DELETE",
            f"{self._v2_prefix(project_id, version_id)}"
            f"/fact-tables/{fact_table_id}/{segment}/{element_id}",
        )

    # -- verification filters -----------------------------------------------

    def _verification_filter_path(
        self: _Transport,
        project_id: int,
        version_id: int,
        fact_table_id: int | None,
        filter_id: int | None = None,
    ) -> str:
        base = self._v2_prefix(project_id, version_id)
        if fact_table_id is not None:
            base = f"{base}/fact-tables/{fact_table_id}"
        path = f"{base}/verification-filters"
        return f"{path}/{filter_id}" if filter_id is not None else path

    async def create_verification_filter(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: VerificationFilterWrite,
        *,
        fact_table_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            self._verification_filter_path(project_id, version_id, fact_table_id),
            body,
            idempotency_key=idempotency_key,
        )

    async def replace_verification_filter(
        self: _Transport,
        project_id: int,
        version_id: int,
        filter_id: int,
        body: VerificationFilterWrite,
        *,
        fact_table_id: int | None = None,
    ) -> WriteResult:
        return await self._write(
            "PUT",
            self._verification_filter_path(project_id, version_id, fact_table_id, filter_id),
            body,
        )

    async def update_verification_filter(
        self: _Transport,
        project_id: int,
        version_id: int,
        filter_id: int,
        body: VerificationFilterWrite,
        *,
        fact_table_id: int | None = None,
    ) -> WriteResult:
        return await self._write(
            "PATCH",
            self._verification_filter_path(project_id, version_id, fact_table_id, filter_id),
            body,
        )

    async def delete_verification_filter(
        self: _Transport,
        project_id: int,
        version_id: int,
        filter_id: int,
        *,
        fact_table_id: int | None = None,
    ) -> WriteResult:
        return await self._write(
            "DELETE",
            self._verification_filter_path(project_id, version_id, fact_table_id, filter_id),
        )

    # -- relationships ------------------------------------------------------

    async def create_relationship(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: RelationshipWrite,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/relationships",
            body,
            idempotency_key=idempotency_key,
        )

    async def replace_relationship(
        self: _Transport,
        project_id: int,
        version_id: int,
        relationship_id: int,
        body: RelationshipWrite,
    ) -> WriteResult:
        return await self._write(
            "PUT",
            f"{self._v2_prefix(project_id, version_id)}/relationships/{relationship_id}",
            body,
        )

    async def update_relationship(
        self: _Transport,
        project_id: int,
        version_id: int,
        relationship_id: int,
        body: RelationshipWrite,
    ) -> WriteResult:
        return await self._write(
            "PATCH",
            f"{self._v2_prefix(project_id, version_id)}/relationships/{relationship_id}",
            body,
        )

    async def delete_relationship(
        self: _Transport, project_id: int, version_id: int, relationship_id: int
    ) -> WriteResult:
        return await self._write(
            "DELETE", f"{self._v2_prefix(project_id, version_id)}/relationships/{relationship_id}"
        )

    # -- project access (doc section 9.9.7) ---------------------------------

    async def set_project_access(
        self: _Transport,
        project_id: int,
        body: ProjectAccessWrite,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        return await self._write(
            "POST",
            f"{self._project_prefix(project_id)}/access",
            body,
            idempotency_key=idempotency_key,
        )

    async def revoke_project_access(
        self: _Transport, project_id: int, user_id: int
    ) -> WriteResult:
        """Answers 200 with {"success": true} — not 204, unlike other DELETEs."""
        return await self._write("DELETE", f"{self._project_prefix(project_id)}/access/{user_id}")

    async def transfer_project_ownership(
        self: _Transport, project_id: int, new_owner_id: int
    ) -> WriteResult:
        return await self._write(
            "PUT",
            f"{self._project_prefix(project_id)}/owner",
            TransferOwnerBody(newOwnerId=new_owner_id),
        )

    # -- version transfer (doc section 9.9.10) ------------------------------

    async def export_version_to_git(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: ExportGitBody,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        from .client import TRANSFER_TIMEOUT

        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/export/git",
            body,
            idempotency_key=idempotency_key,
            timeout=TRANSFER_TIMEOUT,
        )

    async def export_version_to_file(
        self: _Transport, project_id: int, version_id: int, body: ExportFileBody
    ) -> WriteResult:
        from .client import TRANSFER_TIMEOUT

        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/export/file",
            body,
            timeout=TRANSFER_TIMEOUT,
        )

    async def validate_import_source(
        self: _Transport,
        project_id: int,
        version_id: int,
        *,
        body: ImportSourceBody | None = None,
        file_path: str | Path | None = None,
    ) -> WriteResult:
        return await self._import_dry_run(
            project_id, version_id, "validate", body=body, file_path=file_path
        )

    async def preview_import(
        self: _Transport,
        project_id: int,
        version_id: int,
        *,
        body: ImportSourceBody | None = None,
        file_path: str | Path | None = None,
    ) -> WriteResult:
        return await self._import_dry_run(
            project_id, version_id, "preview", body=body, file_path=file_path
        )

    async def _import_dry_run(
        self: _Transport,
        project_id: int,
        version_id: int,
        action: str,
        *,
        body: ImportSourceBody | None,
        file_path: str | Path | None,
    ) -> WriteResult:
        from .client import TRANSFER_TIMEOUT

        path = f"{self._v2_prefix(project_id, version_id)}/import/{action}"
        if file_path is not None:
            files, data = _multipart(file_path, body)
            return await self._write(
                "POST", path, files=files, data=data, timeout=TRANSFER_TIMEOUT
            )
        return await self._write("POST", path, body, timeout=TRANSFER_TIMEOUT)

    async def import_version_from_git(
        self: _Transport,
        project_id: int,
        version_id: int,
        body: ImportGitBody,
        *,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        from .client import TRANSFER_TIMEOUT

        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/import/git",
            body,
            idempotency_key=idempotency_key,
            timeout=TRANSFER_TIMEOUT,
        )

    async def import_version_from_file(
        self: _Transport,
        project_id: int,
        version_id: int,
        *,
        file_path: str | Path,
        target_method: str,
        target_version_name: str,
        conflict_strategy: str | None = None,
        options: ImportOptions | None = None,
        encryption_password: str | None = None,
        idempotency_key: str | None = None,
    ) -> WriteResult:
        """On-premises only: the cloud gateway does not forward binary bodies."""
        from .client import TRANSFER_TIMEOUT

        data: dict[str, Any] = {
            "target.method": target_method,
            "target.version_name": target_version_name,
        }
        if conflict_strategy:
            data["conflict_strategy"] = conflict_strategy
        if options is not None:
            data["options"] = json.dumps(
                options.model_dump(mode="json", by_alias=True, exclude_unset=True)
            )
        if encryption_password:
            data["encryption_password"] = encryption_password

        files = _file_part(file_path)
        return await self._write(
            "POST",
            f"{self._v2_prefix(project_id, version_id)}/import/file",
            files=files,
            data=data,
            idempotency_key=idempotency_key,
            timeout=TRANSFER_TIMEOUT,
        )

    # -- Git connections (doc section 9.9.11) -------------------------------

    async def create_git_connection(
        self: _Transport, body: GitConnectionWrite, *, idempotency_key: str | None = None
    ) -> WriteResult:
        return await self._write(
            "POST", "/df-api/v2/git-connections", body, idempotency_key=idempotency_key
        )

    async def update_git_connection(
        self: _Transport, connection_id: int, body: GitConnectionWrite
    ) -> WriteResult:
        return await self._write("PUT", f"/df-api/v2/git-connections/{connection_id}", body)

    async def delete_git_connection(self: _Transport, connection_id: int) -> WriteResult:
        return await self._write("DELETE", f"/df-api/v2/git-connections/{connection_id}")

    async def test_git_connection(self: _Transport, connection_id: int) -> WriteResult:
        """Runs five repository checks and refreshes the stored status.

        A failed check is not an error: the endpoint answers 200 with status ``failed``.
        """
        from .client import TRANSFER_TIMEOUT

        return await self._write(
            "POST", f"/df-api/v2/git-connections/{connection_id}/test", timeout=TRANSFER_TIMEOUT
        )


def _file_part(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    return {"file": (path.name, path.read_bytes(), "application/zip")}


def _multipart(
    file_path: str | Path, body: ImportSourceBody | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    data: dict[str, Any] = {}
    if body is not None:
        dumped = body.model_dump(mode="json", by_alias=True, exclude_unset=True)
        options = dumped.pop("options", None)
        for key, value in dumped.items():
            if value is None:
                continue
            data[key] = json.dumps(value) if isinstance(value, dict | list) else value
        if options is not None:
            # In multipart requests `options` travels as a JSON string.
            data["options"] = json.dumps(options)
    return _file_part(file_path), data


__all__ = [
    "ElementType",
    "GitConnectionTestResponse",
    "WriteMixin",
    "_ASSIGN_BODY_KEY",
    "_ASSIGN_SEGMENT",
]
