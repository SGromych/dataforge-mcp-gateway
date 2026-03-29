"""Normalize raw API responses into canonical models."""

from __future__ import annotations

from dataforge_mcp.dataforge.schemas import ConnectedSourceRaw, DimensionRaw, MeasureRaw

from .models import (
    CanonicalConnectedSource,
    CanonicalDimension,
    CanonicalMeasure,
    CanonicalProject,
    CanonicalSemanticContext,
    CanonicalVersion,
    SemanticStats,
)


def normalize_connected_source(
    raw: ConnectedSourceRaw | None,
) -> CanonicalConnectedSource | None:
    if raw is None:
        return None
    # Measures use "database", dimensions use "db" — unify into db
    db = raw.db if raw.db is not None else raw.database
    return CanonicalConnectedSource(
        db=db,
        table=raw.table,
        column=raw.column,
    )


def normalize_measure(raw: MeasureRaw) -> CanonicalMeasure:
    return CanonicalMeasure(
        row_number=raw.row_number,
        group=raw.group,
        block=raw.block,
        name=raw.measure_name,
        description=raw.measure_description,
        data_type=raw.data_type,
        measure_type=raw.measure_type,
        formula=raw.formula,
        restrictions=raw.restrictions,
        connected_source=normalize_connected_source(raw.connected_source),
        status=raw.status,
        relevance=raw.relevance,
        required=raw.required,
        visibility=raw.visibility,
        responsible_for_data=raw.responsible_for_data,
        variation=raw.variation,
        raw=raw.model_dump(),
    )


def normalize_dimension(raw: DimensionRaw) -> CanonicalDimension:
    return CanonicalDimension(
        row_number=raw.row_number,
        group=raw.group,
        block=raw.block,
        name=raw.dimension_name,
        description=raw.dimension_description,
        dimension_group=raw.dimension_group,
        data_type=raw.data_type,
        connected_source=normalize_connected_source(raw.connected_source),
        value_options=raw.value_options,
        status=raw.status,
        relevance=raw.relevance,
        required=raw.required,
        visibility=raw.visibility,
        responsible_for_data=raw.responsible_for_data,
        raw=raw.model_dump(),
    )


def normalize_measures(raw_list: list[MeasureRaw]) -> list[CanonicalMeasure]:
    return [normalize_measure(m) for m in raw_list]


def normalize_dimensions(raw_list: list[DimensionRaw]) -> list[CanonicalDimension]:
    return [normalize_dimension(d) for d in raw_list]


def build_semantic_context(
    project: CanonicalProject,
    version: CanonicalVersion,
    measures: list[CanonicalMeasure],
    dimensions: list[CanonicalDimension],
) -> CanonicalSemanticContext:
    return CanonicalSemanticContext(
        project=project,
        version=version,
        measures=measures,
        dimensions=dimensions,
        stats=SemanticStats(
            measure_count=len(measures),
            dimension_count=len(dimensions),
        ),
    )
