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
    table: str | None = None
    column: str | None = None


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


class RmdPagination(BaseModel):
    measures: PaginationResponse
    dimensions: PaginationResponse


class RmdResponse(BaseModel):
    measures: list[MeasureRaw]
    dimensions: list[DimensionRaw]
    pagination: RmdPagination
