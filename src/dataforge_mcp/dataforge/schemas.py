"""Pydantic models for raw DataForge API v2 responses.

Two invariants hold across this module and are enforced by tests:

* DF API v2 serializes every key in snake_case. The only camelCase keys in the whole
  surface are ``pageSize`` and ``totalPages`` inside the pagination object, so
  ``PaginationResponse`` is the only model that carries aliases.
* Every model allows unknown fields — the contract is extended additively, and a new
  field must never break a running server.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

_ALLOW = {"extra": "allow", "populate_by_name": True}

# Entity ids are strings in v2 bodies and in most responses, but the project and
# version listings still serialize them as integers.
IdValue = int | str


class PaginationResponse(BaseModel):
    model_config = _ALLOW

    total: int | None = None
    page: int | None = None
    page_size: int | None = Field(alias="pageSize", default=None)
    total_pages: int | None = Field(alias="totalPages", default=None)


class ProjectItem(BaseModel):
    model_config = _ALLOW

    id: IdValue
    name: str | None = None
    description: str | None = None


class ProjectListResponse(BaseModel):
    model_config = _ALLOW

    projects: list[ProjectItem] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class VersionItem(BaseModel):
    model_config = _ALLOW

    id: IdValue
    name: str | None = None
    is_global: bool | None = None


class VersionListResponse(BaseModel):
    model_config = _ALLOW

    versions: list[VersionItem] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class ConnectedSourceRaw(BaseModel):
    """Source object (doc section 9.3.6).

    ``connection`` is the only field that identifies a source unambiguously — several
    connections of one version may point at the same database. It is v2-only.
    """

    model_config = _ALLOW

    connection: str | None = None
    database: str | None = None
    db: IdValue | None = None
    schema_: str | None = Field(alias="schema", default=None)
    table: str | None = None
    column: str | None = None


class SqlScript(BaseModel):
    model_config = _ALLOW

    fact_table_id: str | None = None
    fact_table_name: str | None = None
    sql: str


class MeasureSqlCode(BaseModel):
    model_config = _ALLOW

    generated_at: str
    sql_scripts: list[SqlScript] = Field(default_factory=list)


class MeasureRaw(BaseModel):
    model_config = _ALLOW

    id: str | None = None
    row_number: str | int | None = None
    group: str | None = None
    block: str | None = None
    measure_name: str | None = None
    measure_description: str | None = None
    original_source_type: str | None = None
    original_source: str | None = None
    original_object: str | None = None
    data_type: str | None = None
    display_data_type: str | None = None
    measure_type: str | None = None
    restrictions: str | None = None
    formula: str | None = None
    connected_source: ConnectedSourceRaw | None = None
    report_for_verification: str | None = None
    comment: str | None = None
    status: str | None = None
    relevance: str | None = None
    required: str | None = None
    visibility: str | None = None
    responsible_for_data: str | None = None
    variation: str | None = None
    sql_code: MeasureSqlCode | None = None


class MeasureListResponse(BaseModel):
    model_config = _ALLOW

    measures: list[MeasureRaw] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class DimensionRaw(BaseModel):
    model_config = _ALLOW

    id: str | None = None
    row_number: str | int | None = None
    group: str | None = None
    block: str | None = None
    dimension_name: str | None = None
    dimension_description: str | None = None
    original_source_type: str | None = None
    original_source: str | None = None
    original_object: str | None = None
    dimension_group: str | None = None
    data_type: str | None = None
    display_data_type: str | None = None
    source_data_type: str | None = None
    connected_source: ConnectedSourceRaw | None = None
    dimension_type: str | None = None
    comment: str | None = None
    formula: str | None = None
    value_options: str | list | None = None
    status: str | None = None
    relevance: str | None = None
    required: str | None = None
    visibility: str | None = None
    responsible_for_data: str | None = None


class DimensionListResponse(BaseModel):
    model_config = _ALLOW

    dimensions: list[DimensionRaw] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class FactRaw(BaseModel):
    model_config = _ALLOW

    id: str | None = None
    row_number: str | int | None = None
    group: str | None = None
    block: str | None = None
    fact_name: str | None = None
    fact_description: str | None = None
    original_source_type: str | None = None
    original_source: str | None = None
    original_object: str | None = None
    source_data_type: str | None = None
    fact_type: str | None = None
    formula: str | None = None
    connected_source: ConnectedSourceRaw | None = None
    report_for_verification: str | None = None
    comment: str | None = None
    status: str | None = None
    relevance: str | None = None
    required: str | None = None
    visibility: str | None = None
    responsible_for_data: str | None = None


class FactListResponse(BaseModel):
    model_config = _ALLOW

    facts: list[FactRaw] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


# ---------------------------------------------------------------------------
# Data model entities
# ---------------------------------------------------------------------------


class DimensionGroupMemberRaw(BaseModel):
    model_config = _ALLOW

    id: IdValue | None = None
    name: str | None = None
    description: str | None = None
    level: int | None = None
    display_data_type: str | None = None
    physical_column: str | None = None


class RelatedFactTableRaw(BaseModel):
    model_config = _ALLOW

    fact_table_id: IdValue | None = None
    fact_table_name: str | None = None
    foreign_key_column: str | None = None


class DimensionGroupItem(BaseModel):
    model_config = _ALLOW

    id: IdValue
    name: str | None = None
    description: str | None = None
    primary_key: ConnectedSourceRaw | None = None
    related_fact_tables: list[str] | list[RelatedFactTableRaw] = Field(default_factory=list)


class DimensionGroupListResponse(BaseModel):
    model_config = _ALLOW

    dimension_groups: list[DimensionGroupItem] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class DimensionGroupDetail(BaseModel):
    model_config = _ALLOW

    id: IdValue
    name: str | None = None
    description: str | None = None
    primary_key: ConnectedSourceRaw | None = None
    dimensions: list[DimensionGroupMemberRaw] = Field(default_factory=list)
    related_fact_tables: list[RelatedFactTableRaw] = Field(default_factory=list)


class FactTableItem(BaseModel):
    model_config = _ALLOW

    id: IdValue
    name: str | None = None
    description: str | None = None
    owner: str | None = None
    created_at: str | None = None
    measures_count: int | None = None
    dimensions_count: int | None = None
    facts_count: int | None = None
    verification_filters_count: int | None = None
    related_dimension_groups_count: int | None = None


class FactTableListResponse(BaseModel):
    model_config = _ALLOW

    fact_tables: list[FactTableItem] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class FactTableMemberRaw(BaseModel):
    """Element assigned to a fact table.

    Reference columns here are raw slugs (``base``/``calculated``, ``primary``/
    ``derived``/``constant``), unlike the RMD listings which return localized labels.
    """

    model_config = _ALLOW

    id: IdValue | None = None
    name: str | None = None
    description: str | None = None
    formula: str | None = None
    display_data_type: str | None = None
    measure_type: str | None = None
    dimension_type: str | None = None
    fact_type: str | None = None
    physical_column: str | None = None
    is_from_dimension_group: bool | None = None
    dimension_group_id: IdValue | None = None
    dependencies: list[dict] | None = None


class FactTableDimensionGroupRaw(BaseModel):
    model_config = _ALLOW

    id: IdValue | None = None
    name: str | None = None
    description: str | None = None
    primary_key: ConnectedSourceRaw | None = None
    foreign_key: ConnectedSourceRaw | None = None


class VerificationFilterRaw(BaseModel):
    model_config = _ALLOW

    id: IdValue | None = None
    name: str | None = None
    description: str | None = None
    conditions: str | None = None
    is_valid: bool | None = None
    invalid_reason: str | None = None


class FactTableDetail(BaseModel):
    model_config = _ALLOW

    id: IdValue
    name: str | None = None
    description: str | None = None
    owner: str | None = None
    created_at: str | None = None
    measures: list[FactTableMemberRaw] = Field(default_factory=list)
    dimensions: list[FactTableMemberRaw] = Field(default_factory=list)
    facts: list[FactTableMemberRaw] = Field(default_factory=list)
    dimension_groups: list[FactTableDimensionGroupRaw] = Field(default_factory=list)
    verification_filters: list[VerificationFilterRaw] = Field(default_factory=list)


class RelationshipItem(BaseModel):
    model_config = _ALLOW

    id: IdValue
    source_fact_table: dict | None = None
    target_dimension_group: dict | None = None
    foreign_key: ConnectedSourceRaw | None = None
    primary_key: ConnectedSourceRaw | None = None
    relationship_type: str | None = None


class RelationshipListResponse(BaseModel):
    model_config = _ALLOW

    relationships: list[RelationshipItem] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class RelationshipDetail(RelationshipItem):
    model_config = _ALLOW


# ---------------------------------------------------------------------------
# Data marts
# ---------------------------------------------------------------------------


class DataMartItem(BaseModel):
    model_config = _ALLOW

    id: IdValue
    name: str | None = None
    description: str | None = None
    owner: str | None = None
    created_at: str | None = None
    type: str | None = None
    merge_type: str | None = None
    source_fact_table_count: int | None = None
    has_physical_view: bool | None = None


class DataMartListResponse(BaseModel):
    model_config = _ALLOW

    data_marts: list[DataMartItem] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class PhysicalViewBase(BaseModel):
    """Physical view metadata as embedded in the data mart detail response.

    The standalone ``/view`` endpoint returns the same fields plus ``connection``.
    """

    model_config = _ALLOW

    exists: bool | None = None
    type: str | None = None
    database: str | None = None
    schema_: str | None = Field(alias="schema", default=None)
    name: str | None = None
    created_at: str | None = None
    status: str | None = None
    is_stale: bool | None = None
    last_refresh_at: str | None = None


class ConnectionRef(BaseModel):
    model_config = _ALLOW

    id: IdValue | None = None
    name: str | None = None
    db_type: str | None = None


class PhysicalViewResponse(PhysicalViewBase):
    model_config = _ALLOW

    connection: ConnectionRef | None = None


class SelectedMeasureRaw(BaseModel):
    model_config = _ALLOW

    instance_id: str | None = None
    measure_id: str | None = None
    measure_name: str | None = None
    description: str | None = None
    formula: str | None = None
    data_type: str | None = None
    display_name: str | None = None
    aggregation_configuration: dict | None = None
    source_fact_table_id: str | None = None


class SelectedFactRaw(BaseModel):
    model_config = _ALLOW

    fact_id: str | None = None
    fact_name: str | None = None
    description: str | None = None
    data_type: str | None = None
    display_name: str | None = None
    include_in_result: bool | None = None
    filter_condition: str | None = None
    source_fact_table_id: str | None = None


class SelectedDimensionRaw(BaseModel):
    model_config = _ALLOW

    dimension_id: str | None = None
    dimension_name: str | None = None
    description: str | None = None
    data_type: str | None = None
    display_name: str | None = None
    include_in_result: bool | None = None
    filter_condition: str | None = None
    source_fact_table_id: str | None = None
    source_dimension_group_id: str | None = None
    source_dimension_group_name: str | None = None


class DataMartDetail(BaseModel):
    model_config = _ALLOW

    id: IdValue
    name: str | None = None
    description: str | None = None
    owner: str | None = None
    created_at: str | None = None
    type: str | None = None
    merge_type: str | None = None
    source_fact_tables: list[dict] = Field(default_factory=list)
    selected_measures: list[SelectedMeasureRaw] = Field(default_factory=list)
    selected_facts: list[SelectedFactRaw] = Field(default_factory=list)
    selected_dimensions: list[SelectedDimensionRaw] = Field(default_factory=list)
    selected_measure_attributes: list[dict] | None = None
    physical_view: PhysicalViewBase | None = None


class SqlValidationError(BaseModel):
    model_config = _ALLOW

    code: str | None = None
    message: str | None = None


class SqlGenerationResponse(BaseModel):
    """Response of ``POST .../generate-sql`` — HTTP 200 even when generation fails."""

    model_config = _ALLOW

    sql_script: str | None = None
    target_db_type: str | None = None
    validation_errors: list[SqlValidationError] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------


class ConnectionItem(BaseModel):
    model_config = _ALLOW

    id: IdValue
    name: str | None = None
    db_type: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    schema_: str | None = Field(alias="schema", default=None)
    username: str | None = None
    status: str | None = None
    last_updated_at: str | None = None


class ConnectionListResponse(BaseModel):
    model_config = _ALLOW

    connections: list[ConnectionItem] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class SchemaColumn(BaseModel):
    model_config = _ALLOW

    column_name: str | None = None
    data_type: str | None = None


class SchemaTable(BaseModel):
    model_config = _ALLOW

    table_name: str | None = None
    schema_: str | None = Field(alias="schema", default=None)
    columns: list[SchemaColumn] = Field(default_factory=list)


class DbSchema(BaseModel):
    model_config = _ALLOW

    connection: str | None = None
    tables: list[SchemaTable] = Field(default_factory=list)


class ConnectionDetail(ConnectionItem):
    """Connection details.

    Exactly one of ``db_tables`` (short form) or ``db_schema`` (``include_db_schema=true``)
    is present. Credentials are never returned (doc section 9.6).
    """

    model_config = _ALLOW

    db_tables: list[dict] | None = None
    db_schema: DbSchema | None = None


class ConnectionSchemaResponse(BaseModel):
    model_config = _ALLOW

    id: IdValue | None = None
    name: str | None = None
    db_type: str | None = None
    last_updated_at: str | None = None
    schema_: DbSchema | None = Field(alias="schema", default=None)


# ---------------------------------------------------------------------------
# Consolidated RMD export (doc section 9.9.2.6)
# ---------------------------------------------------------------------------


class RmdExportResponse(BaseModel):
    """Full snapshot returned by ``GET {v}/rmd`` — no pagination."""

    model_config = _ALLOW

    project: ProjectItem | None = None
    version: VersionItem | None = None
    measures: list[MeasureRaw] = Field(default_factory=list)
    dimensions: list[DimensionRaw] = Field(default_factory=list)
    facts: list[FactRaw] = Field(default_factory=list)
    dimension_groups: list[DimensionGroupItem] = Field(default_factory=list)
    fact_tables: list[FactTableItem] = Field(default_factory=list)
    relationships: list[RelationshipItem] = Field(default_factory=list)
    exported_at: str | None = None


# ---------------------------------------------------------------------------
# Project access (doc section 9.9.7)
# ---------------------------------------------------------------------------


class ProjectAccessEntry(BaseModel):
    model_config = _ALLOW

    id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    isOwner: bool | None = None  # noqa: N815 - camelCase is the wire format here
    globalRole: str | None = None  # noqa: N815
    projectRole: str | None = None  # noqa: N815


# ---------------------------------------------------------------------------
# Git connections (doc section 9.9.11)
# ---------------------------------------------------------------------------


class GitConnectionItem(BaseModel):
    model_config = _ALLOW

    id: IdValue | None = None
    name: str | None = None
    platform: str | None = None
    repository_url: str | None = None
    branch: str | None = None
    path: str | None = None
    status: str | None = None
    last_used: str | None = None
    created_at: str | None = None
    created_by: str | None = None
    shared: bool | None = None
    default: bool | None = None


class GitConnectionListResponse(BaseModel):
    model_config = _ALLOW

    git_connections: list[GitConnectionItem] = Field(alias="git-connections", default_factory=list)
    pagination: PaginationResponse | None = None


class GitConnectionTestResponse(BaseModel):
    model_config = _ALLOW

    git_connection_id: str | None = Field(alias="git-connection_id", default=None)
    status: str | None = None
    tests: dict | None = None
    details: dict | None = None
