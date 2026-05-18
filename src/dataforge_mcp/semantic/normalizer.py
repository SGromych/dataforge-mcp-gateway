"""Normalize raw API responses into canonical models."""

from __future__ import annotations

from dataforge_mcp.dataforge.schemas import (
    ConnectedSourceRaw,
    DimensionRaw,
    FactRaw,
    MeasureRaw,
)

from .models import (
    CanonicalConnectedSource,
    CanonicalDimension,
    CanonicalFact,
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
        original_source_type=raw.original_source_type,
        original_source=raw.original_source,
        original_object=raw.original_object,
        report_for_verification=raw.report_for_verification,
        comment=raw.comment,
        display_data_type=raw.display_data_type,
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
        dimension_type=raw.dimension_type,
        original_source_type=raw.original_source_type,
        original_source=raw.original_source,
        original_object=raw.original_object,
        comment=raw.comment,
        formula=raw.formula,
        value_options=raw.value_options,
        display_data_type=raw.display_data_type,
        source_data_type=raw.source_data_type,
        status=raw.status,
        relevance=raw.relevance,
        required=raw.required,
        visibility=raw.visibility,
        responsible_for_data=raw.responsible_for_data,
        raw=raw.model_dump(),
    )


def normalize_fact(raw: FactRaw) -> CanonicalFact:
    return CanonicalFact(
        row_number=raw.row_number,
        group=raw.group,
        block=raw.block,
        name=raw.fact_name,
        description=raw.fact_description,
        original_source_type=raw.original_source_type,
        original_source=raw.original_source,
        original_object=raw.original_object,
        source_data_type=raw.source_data_type,
        fact_type=raw.fact_type,
        formula=raw.formula,
        connected_source=normalize_connected_source(raw.connected_source),
        report_for_verification=raw.report_for_verification,
        comment=raw.comment,
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


def normalize_facts(raw_list: list[FactRaw]) -> list[CanonicalFact]:
    return [normalize_fact(f) for f in raw_list]


def build_semantic_context(
    project: CanonicalProject,
    version: CanonicalVersion,
    measures: list[CanonicalMeasure],
    dimensions: list[CanonicalDimension],
    facts: list[CanonicalFact] | None = None,
) -> CanonicalSemanticContext:
    facts = facts or []
    return CanonicalSemanticContext(
        project=project,
        version=version,
        measures=measures,
        dimensions=dimensions,
        facts=facts,
        stats=SemanticStats(
            measure_count=len(measures),
            dimension_count=len(dimensions),
            fact_count=len(facts),
        ),
    )
