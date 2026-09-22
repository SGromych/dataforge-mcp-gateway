"""Request bodies for DF API v2 write endpoints (doc sections 9.9.5–9.9.11).

Two rules from the spec shape this module:

* **Bodies are strict.** An unknown field answers ``400 DF_API.VALIDATION_FAILED`` with
  ``details[].code = unknown_field``. ``extra="forbid"`` reproduces that check locally,
  so a typo costs a validation error instead of a network round-trip.
* **Read-only fields are accepted and ignored.** ``id``, ``timestamp``, ``created_at``,
  ``updated_at`` stay in the models on purpose — that is what lets an object obtained
  from a read endpoint be sent straight back.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dataforge_mcp.errors import DataForgeError, ErrorCode

WriteMode = Literal["create", "replace", "update"]

# Flag columns are transmitted as the strings "true"/"false", not as booleans.
FlagStr = Literal["true", "false"]


class WriteBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SourceObject(WriteBody):
    """Physical location of data (doc section 9.3.6).

    Passing ``connection`` switches the API to the strict contract: db, schema, table and
    column are then verified against that connection's cached schema. Omitting it keeps
    the legacy lenient behaviour where ``db`` is resolved loosely and nothing is checked.
    """

    connection: str | None = None
    db: str
    schema_: str | None = Field(alias="schema", default=None)
    table: str
    column: str | None = None


# ---------------------------------------------------------------------------
# Projects and versions
# ---------------------------------------------------------------------------


class ProjectWrite(WriteBody):
    id: str | None = None
    name: str | None = None
    description: str | None = None
    color: str | None = None


class VersionWrite(WriteBody):
    """Versions expose only name and is_global — the API rejects ``description``."""

    id: str | None = None
    name: str | None = None
    is_global: bool | None = None
    clone_from_version: str | None = None


# ---------------------------------------------------------------------------
# RMD content
# ---------------------------------------------------------------------------


class MeasureWrite(WriteBody):
    id: str | None = None
    measure_name: str | None = None
    measure_type: str | None = None
    group: str | None = None
    block: str | None = None
    measure_description: str | None = None
    original_source_type: str | None = None
    original_source: str | None = None
    original_object: str | None = None
    display_data_type: str | None = None
    restrictions: str | None = None
    formula: str | None = None
    report_for_verification: str | None = None
    comment: str | None = None
    status: str | None = None
    relevance: FlagStr | None = None
    required: FlagStr | None = None
    visibility: FlagStr | None = None
    responsible_for_data: str | None = None
    variation: str | None = None


class DimensionWrite(WriteBody):
    id: str | None = None
    dimension_name: str | None = None
    dimension_type: str | None = None
    group: str | None = None
    block: str | None = None
    dimension_description: str | None = None
    original_source_type: str | None = None
    original_source: str | None = None
    original_object: str | None = None
    dimension_group: str | None = None
    display_data_type: str | None = None
    connected_source: SourceObject | None = None
    formula: str | None = None
    value_options: str | None = None
    comment: str | None = None
    status: str | None = None
    relevance: FlagStr | None = None
    required: FlagStr | None = None
    visibility: FlagStr | None = None
    responsible_for_data: str | None = None


class FactWrite(WriteBody):
    id: str | None = None
    fact_name: str | None = None
    fact_type: str | None = None
    group: str | None = None
    block: str | None = None
    fact_description: str | None = None
    original_source_type: str | None = None
    original_source: str | None = None
    original_object: str | None = None
    connected_source: SourceObject | None = None
    formula: str | None = None
    report_for_verification: str | None = None
    comment: str | None = None
    status: str | None = None
    relevance: FlagStr | None = None
    required: FlagStr | None = None
    visibility: FlagStr | None = None
    responsible_for_data: str | None = None


class MeasuresBulk(WriteBody):
    measures: list[MeasureWrite] = Field(min_length=1)


class DimensionsBulk(WriteBody):
    dimensions: list[DimensionWrite] = Field(min_length=1)


class FactsBulk(WriteBody):
    facts: list[FactWrite] = Field(min_length=1)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class GroupMember(WriteBody):
    id: str
    level: int = Field(ge=1)


class DimensionGroupWrite(WriteBody):
    id: str | None = None
    name: str | None = None
    description: str | None = None
    primary_key: SourceObject | None = None
    dimensions: list[GroupMember] | None = None


class GroupMembersBody(WriteBody):
    dimensions: list[GroupMember] = Field(min_length=1)


class GroupLevelBody(WriteBody):
    level: int = Field(ge=1)


class FactTableWrite(WriteBody):
    id: str | None = None
    name: str | None = None
    description: str | None = None
    owner: str | None = None  # accepted and ignored by the API


class VerificationFilterWrite(WriteBody):
    id: str | None = None
    name: str | None = None
    description: str | None = None
    conditions: str | None = None


class RelationshipWrite(WriteBody):
    id: str | None = None
    source_fact_table_id: str | None = None
    target_dimension_group_id: str | None = None
    foreign_key: SourceObject | None = None
    primary_key: SourceObject | None = None
    relationship_type: Literal["many_to_one"] | None = None


# ---------------------------------------------------------------------------
# Project access (camelCase on the wire, like the internal API)
# ---------------------------------------------------------------------------


class ProjectAccessWrite(WriteBody):
    user_id: int = Field(alias="userId")
    access_level: Literal["developer", "analyst", "viewer"] = Field(alias="accessLevel")


class TransferOwnerBody(WriteBody):
    new_owner_id: int = Field(alias="newOwnerId")


# ---------------------------------------------------------------------------
# Version transfer (doc section 9.9.10)
# ---------------------------------------------------------------------------


class GitAuth(WriteBody):
    """Git credentials, sent in the clear over TLS. Never logged, never echoed back."""

    method: Literal["pat", "ssh", "password"]
    token: str | None = None
    private_key: str | None = None
    passphrase: str | None = None
    username: str | None = None
    password: str | None = None

    @model_validator(mode="after")
    def _check_method_fields(self) -> GitAuth:
        required: dict[str, tuple[str, ...]] = {
            "pat": ("token",),
            "ssh": ("private_key",),
            "password": ("username", "password"),
        }
        missing = [f for f in required[self.method] if not getattr(self, f)]
        if missing:
            raise ValueError(f"authentication.method={self.method} requires: {', '.join(missing)}")
        return self


class ExportOptions(WriteBody):
    include_rmd: bool | None = None
    include_fact_tables: bool | None = None
    include_data_marts: bool | None = None
    include_connections: bool | None = None
    include_history: bool | None = None
    encrypt_sensitive: bool | None = None
    add_gitattributes: bool | None = None
    save_connection: bool | None = None
    connection_name: str | None = None
    encryption_password: str | None = None
    use_system_key: bool | None = None


class ExportGitBody(WriteBody):
    repository_url: str
    branch: str
    commit_message: str
    path: str | None = None
    connection_id: str | None = None
    authentication: GitAuth | None = None
    options: ExportOptions | None = None

    @model_validator(mode="after")
    def _check_credentials(self) -> ExportGitBody:
        if not self.connection_id and not self.authentication:
            raise ValueError("either connection_id or authentication must be provided")
        return self


class ExportFileBody(WriteBody):
    options: ExportOptions | None = None


class ImportOptions(WriteBody):
    import_rmd: bool | None = None
    import_fact_tables: bool | None = None
    import_data_marts: bool | None = None
    import_connections: bool | None = None
    import_history: bool | None = None
    detect_merges: bool | None = None
    decrypt_sensitive: bool | None = None
    encryption_password: str | None = None


class ImportTarget(WriteBody):
    method: Literal["create", "replace"] = "create"
    version_name: str


ConflictStrategy = Literal["smart_merge", "overwrite", "skip", "manual"]


class ImportSourceBody(WriteBody):
    """Body of the dry-run endpoints (``import/validate``, ``import/preview``)."""

    source_type: Literal["git", "file"] | None = None
    repository_url: str | None = None
    branch: str | None = None
    path: str | None = None
    commit_hash: str | None = None
    connection_id: str | None = None
    authentication: GitAuth | None = None
    encryption_password: str | None = None
    conflict_strategy: ConflictStrategy | None = None
    options: ImportOptions | None = None


class ImportGitBody(WriteBody):
    repository_url: str
    branch: str
    target: ImportTarget
    path: str | None = None
    commit_hash: str | None = None
    connection_id: str | None = None
    authentication: GitAuth | None = None
    conflict_strategy: ConflictStrategy | None = None
    options: ImportOptions | None = None

    @model_validator(mode="after")
    def _check_credentials(self) -> ImportGitBody:
        if not self.connection_id and not self.authentication:
            raise ValueError("either connection_id or authentication must be provided")
        return self


# ---------------------------------------------------------------------------
# Git connections (doc section 9.9.11)
# ---------------------------------------------------------------------------


GitPlatform = Literal["github", "gitlab", "bitbucket", "azure-devops", "generic"]


class GitConnectionSettings(WriteBody):
    allow_branch_override: bool | None = None
    allow_path_override: bool | None = None
    set_as_default: bool | None = None
    share_with_all: bool | None = None


class GitConnectionWrite(WriteBody):
    name: str | None = None
    platform: GitPlatform | None = None
    repository_url: str | None = None
    branch: str | None = None
    path: str | None = None
    authentication: GitAuth | None = None
    settings: GitConnectionSettings | None = None


# ---------------------------------------------------------------------------
# Mode-dependent required fields
# ---------------------------------------------------------------------------

REQUIRED_BY_ENTITY: dict[str, tuple[str, ...]] = {
    "measure": ("measure_name", "measure_type"),
    "dimension": ("dimension_name", "dimension_type"),
    "fact": ("fact_name", "fact_type"),
    "dimension_group": ("name", "primary_key"),
    "fact_table": ("name",),
    "verification_filter": ("name", "conditions"),
    "relationship": (
        "source_fact_table_id",
        "target_dimension_group_id",
        "foreign_key",
        "primary_key",
        "relationship_type",
    ),
    "project": ("name",),
    "version": ("name",),
    "git_connection": ("name", "platform", "repository_url", "branch", "authentication"),
}


def require_for_mode(body: WriteBody, entity: str, mode: WriteMode) -> None:
    """Enforce the mandatory fields of ``create`` and ``replace`` locally.

    ``update`` (PATCH) has no required fields. ``replace`` (PUT) resets every optional
    field it does not carry, so the API demands the mandatory ones — we raise the same
    error shape before spending a round-trip on it.
    """
    if mode == "update":
        return
    missing = [
        field
        for field in REQUIRED_BY_ENTITY.get(entity, ())
        if getattr(body, field, None) in (None, "")
    ]
    if missing:
        raise DataForgeError(
            code=ErrorCode.DATAFORGE_MISSING_REQUIRED_FIELD,
            message=(f"mode={mode} requires {', '.join(missing)} for {entity.replace('_', ' ')}"),
            field_errors=[{"field": field, "code": "missing_field"} for field in missing],
        )


def validation_error_fields(exc: Any) -> list[dict[str, str]]:
    """Convert a pydantic ValidationError into the v2 ``details[]`` shape.

    Local and server-side validation failures must be indistinguishable to the agent —
    otherwise it has to learn two error formats.
    """
    mapping = {
        "missing": "missing_field",
        "extra_forbidden": "unknown_field",
    }
    fields: list[dict[str, str]] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        fields.append(
            {
                "field": location or "body",
                "code": mapping.get(error.get("type", ""), "invalid_value"),
                "message": error.get("msg", ""),
            }
        )
    return fields
