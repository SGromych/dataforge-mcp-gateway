"""Canonical Pydantic models — internal contract between layers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CanonicalProject(BaseModel):
    id: int
    name: str
    description: str | None = None


class CanonicalVersion(BaseModel):
    id: int
    name: str
    is_global: bool


class CanonicalConnectedSource(BaseModel):
    db: str | int | None = None
    schema_: str | None = Field(default=None, alias="schema")
    table: str | None = None
    column: str | None = None

    model_config = {"populate_by_name": True}


class CanonicalMeasure(BaseModel):
    row_number: str | int | None = None
    group: str | None = None
    block: str | None = None
    name: str | None = None
    description: str | None = None
    data_type: str | None = None
    measure_type: str | None = None
    formula: str | None = None
    restrictions: str | None = None
    connected_source: CanonicalConnectedSource | None = None
    original_source_type: str | None = None
    original_source: str | None = None
    original_object: str | None = None
    report_for_verification: str | None = None
    comment: str | None = None
    display_data_type: str | None = None
    status: str | None = None
    relevance: str | None = None
    required: bool | None = False
    visibility: str | None = None
    responsible_for_data: str | None = None
    variation: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class CanonicalDimension(BaseModel):
    row_number: str | int | None = None
    group: str | None = None
    block: str | None = None
    name: str | None = None
    description: str | None = None
    dimension_group: str | None = None
    data_type: str | None = None
    connected_source: CanonicalConnectedSource | None = None
    dimension_type: str | None = None
    original_source_type: str | None = None
    original_source: str | None = None
    original_object: str | None = None
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
    raw: dict[str, Any] = Field(default_factory=dict)


class SemanticStats(BaseModel):
    measure_count: int = 0
    dimension_count: int = 0


class CanonicalSemanticContext(BaseModel):
    project: CanonicalProject
    version: CanonicalVersion
    measures: list[CanonicalMeasure]
    dimensions: list[CanonicalDimension]
    stats: SemanticStats
