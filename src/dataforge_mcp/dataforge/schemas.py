"""Pydantic models for raw DataForge API responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationResponse(BaseModel):
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    total_pages: int = Field(alias="totalPages")

    model_config = {"populate_by_name": True}


class ProjectItem(BaseModel):
    id: int
    name: str
    description: str | None = None


class ProjectListResponse(BaseModel):
    projects: list[ProjectItem]
    pagination: PaginationResponse


class VersionItem(BaseModel):
    id: int
    name: str
    is_global: bool


class VersionListResponse(BaseModel):
    versions: list[VersionItem]
    pagination: PaginationResponse


class ConnectedSourceRaw(BaseModel):
    model_config = {"extra": "allow"}

    database: str | None = None
    db: int | str | None = None
    schema_: str | None = Field(alias="schema", default=None)
    table: str | None = None
    column: str | None = None


class SqlScript(BaseModel):
    model_config = {"extra": "allow"}

    fact_table_id: str | None = None
    fact_table_name: str | None = None
    sql: str


class MeasureSqlCode(BaseModel):
    model_config = {"extra": "allow"}

    generated_at: str
    sql_scripts: list[SqlScript] = []


class MeasureRaw(BaseModel):
    model_config = {"extra": "allow"}

    row_number: str | int | None = None
    group: str | None = None
    block: str | None = None
    measure_name: str | None = None
    measure_description: str | None = None
    original_source_type: str | None = None
    original_source: str | None = None
    original_object: str | None = None
    data_type: str | None = None
    measure_type: str | None = None
    restrictions: str | None = None
    formula: str | None = None
    connected_source: ConnectedSourceRaw | None = None
    report_for_verification: str | None = None
    comment: str | None = None
    status: str | None = None
    relevance: str | None = None
    display_data_type: str | None = None
    required: bool | None = False
    visibility: str | None = None
    responsible_for_data: str | None = None
    variation: str | None = None
    sql_code: MeasureSqlCode | None = None


class MeasureListResponse(BaseModel):
    measures: list[MeasureRaw]
    pagination: PaginationResponse


class DimensionRaw(BaseModel):
    model_config = {"extra": "allow"}

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
    connected_source: ConnectedSourceRaw | None = None
    dimension_type: str | None = None
    comment: str | None = None
    formula: str | None = None
    value_options: str | list | None = None
    display_data_type: str | None = None
    source_data_type: str | None = None
    status: str | None = None
    relevance: str | None = None
    required: bool | None = False
    visibility: str | None = None
    responsible_for_data: str | None = None


class DimensionListResponse(BaseModel):
    dimensions: list[DimensionRaw]
    pagination: PaginationResponse


class FactRaw(BaseModel):
    model_config = {"extra": "allow"}

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
    required: bool | None = False
    visibility: str | None = None
    responsible_for_data: str | None = None


class FactListResponse(BaseModel):
    facts: list[FactRaw]
    pagination: PaginationResponse


class RmdPagination(BaseModel):
    model_config = {"extra": "allow"}

    measures: PaginationResponse
    dimensions: PaginationResponse
    facts: PaginationResponse | None = None


class RmdResponse(BaseModel):
    measures: list[MeasureRaw]
    dimensions: list[DimensionRaw]
    facts: list[FactRaw] = []
    pagination: RmdPagination


# ---------------------------------------------------------------------------
# DF API response models (/df-api/v2/)
# ---------------------------------------------------------------------------


class DataMartItem(BaseModel):
    model_config = {"extra": "allow"}

    id: int
    name: str | None = None
    type: str | None = None
    merge_type: str | None = None
    description: str | None = None


class DataMartListResponse(BaseModel):
    model_config = {"extra": "allow"}

    data_marts: list[DataMartItem] = Field(alias="dataMarts", default_factory=list)
    pagination: PaginationResponse | None = None


class DataMartDetail(BaseModel):
    model_config = {"extra": "allow", "populate_by_name": True}

    id: int
    name: str | None = None
    type: str | None = None
    merge_type: str | None = None
    description: str | None = None
    measures: list[dict] = Field(default_factory=list)
    dimensions: list[dict] = Field(default_factory=list)
    facts: list[dict] = Field(default_factory=list)
    source_fact_tables: list[dict] = Field(alias="sourceFactTables", default_factory=list)


class PhysicalViewResponse(BaseModel):
    model_config = {"extra": "allow"}


class SqlGenerationResponse(BaseModel):
    model_config = {"extra": "allow"}

    sql: str | None = None


class ConnectionItem(BaseModel):
    model_config = {"extra": "allow"}

    id: int
    name: str | None = None
    db_type: str | None = Field(alias="dbType", default=None)
    status: str | None = None


class ConnectionListResponse(BaseModel):
    model_config = {"extra": "allow"}

    connections: list[ConnectionItem] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class ConnectionDetail(BaseModel):
    model_config = {"extra": "allow", "populate_by_name": True}

    id: int
    name: str | None = None
    db_type: str | None = Field(alias="dbType", default=None)
    status: str | None = None


class ConnectionSchemaResponse(BaseModel):
    model_config = {"extra": "allow"}


class DimensionGroupItem(BaseModel):
    model_config = {"extra": "allow", "populate_by_name": True}

    id: int
    name: str | None = None
    description: str | None = None
    primary_key: str | None = Field(alias="primaryKey", default=None)
    related_fact_tables: list[str] | list[dict] = Field(
        alias="relatedFactTables", default_factory=list
    )
    created_at: str | None = Field(alias="createdAt", default=None)


class DimensionGroupListResponse(BaseModel):
    model_config = {"extra": "allow"}

    dimension_groups: list[DimensionGroupItem] = Field(
        alias="dimensionGroups", default_factory=list
    )
    pagination: PaginationResponse | None = None


class DimensionGroupDetail(BaseModel):
    model_config = {"extra": "allow", "populate_by_name": True}

    id: int
    name: str | None = None
    description: str | None = None
    primary_key: str | None = Field(alias="primaryKey", default=None)
    dimensions: list[dict] = Field(default_factory=list)
    related_fact_tables: list[dict] = Field(alias="relatedFactTables", default_factory=list)
    created_at: str | None = Field(alias="createdAt", default=None)
    updated_at: str | None = Field(alias="updatedAt", default=None)


class FactTableItem(BaseModel):
    model_config = {"extra": "allow", "populate_by_name": True}

    id: int
    name: str | None = None
    description: str | None = None
    owner: str | None = None
    created_at: str | None = Field(alias="createdAt", default=None)
    measures_count: int | None = Field(alias="measuresCount", default=None)
    dimensions_count: int | None = Field(alias="dimensionsCount", default=None)
    facts_count: int | None = Field(alias="factsCount", default=None)
    verification_filters_count: int | None = Field(alias="verificationFiltersCount", default=None)
    related_dimension_groups_count: int | None = Field(
        alias="relatedDimensionGroupsCount", default=None
    )


class FactTableListResponse(BaseModel):
    model_config = {"extra": "allow"}

    fact_tables: list[FactTableItem] = Field(alias="factTables", default_factory=list)
    pagination: PaginationResponse | None = None


class FactTableDetail(BaseModel):
    model_config = {"extra": "allow", "populate_by_name": True}

    id: int
    name: str | None = None
    description: str | None = None
    owner: str | None = None
    created_at: str | None = Field(alias="createdAt", default=None)
    updated_at: str | None = Field(alias="updatedAt", default=None)
    measures: list[dict] = Field(default_factory=list)
    dimensions: list[dict] = Field(default_factory=list)
    facts: list[dict] = Field(default_factory=list)
    dimension_groups: list[dict] = Field(alias="dimensionGroups", default_factory=list)
    verification_filters: list[dict] = Field(alias="verificationFilters", default_factory=list)


class RelationshipItem(BaseModel):
    model_config = {"extra": "allow", "populate_by_name": True}

    id: int
    source_fact_table: dict | None = Field(alias="sourceFactTable", default=None)
    target_dimension_group: dict | None = Field(alias="targetDimensionGroup", default=None)
    foreign_key: dict | None = Field(alias="foreignKey", default=None)
    primary_key: dict | None = Field(alias="primaryKey", default=None)
    relationship_type: str | None = Field(alias="relationshipType", default=None)
    created_at: str | None = Field(alias="createdAt", default=None)


class RelationshipListResponse(BaseModel):
    model_config = {"extra": "allow"}

    relationships: list[RelationshipItem] = Field(default_factory=list)
    pagination: PaginationResponse | None = None


class RelationshipDetail(BaseModel):
    model_config = {"extra": "allow", "populate_by_name": True}

    id: int
    source_fact_table: dict | None = Field(alias="sourceFactTable", default=None)
    target_dimension_group: dict | None = Field(alias="targetDimensionGroup", default=None)
    foreign_key: dict | None = Field(alias="foreignKey", default=None)
    primary_key: dict | None = Field(alias="primaryKey", default=None)
    relationship_type: str | None = Field(alias="relationshipType", default=None)
    created_at: str | None = Field(alias="createdAt", default=None)
    updated_at: str | None = Field(alias="updatedAt", default=None)


class ConsolidatedRmdResponse(BaseModel):
    model_config = {"extra": "allow"}

    project: dict = Field(default_factory=dict)
    version: dict = Field(default_factory=dict)
    measures: list[dict] = Field(default_factory=list)
    dimensions: list[dict] = Field(default_factory=list)
    facts: list[dict] = Field(default_factory=list)
    dimension_groups: list[dict] = Field(alias="dimensionGroups", default_factory=list)
    fact_tables: list[dict] = Field(alias="factTables", default_factory=list)
    relationships: list[dict] = Field(default_factory=list)
    exported_at: str | None = Field(alias="exportedAt", default=None)
