"""Tests for the normalizer."""


from dataforge_mcp.dataforge.schemas import ConnectedSourceRaw, DimensionRaw, MeasureRaw
from dataforge_mcp.semantic.models import CanonicalProject, CanonicalVersion
from dataforge_mcp.semantic.normalizer import (
    build_semantic_context,
    normalize_connected_source,
    normalize_dimension,
    normalize_dimensions,
    normalize_measure,
    normalize_measures,
)


def test_measure_name_normalized() -> None:
    raw = MeasureRaw(measure_name="Total Revenue", measure_description="All revenue")
    result = normalize_measure(raw)
    assert result.name == "Total Revenue"
    assert result.description == "All revenue"


def test_dimension_name_normalized() -> None:
    raw = DimensionRaw(dimension_name="Customer ID", dimension_description="Unique ID")
    result = normalize_dimension(raw)
    assert result.name == "Customer ID"
    assert result.description == "Unique ID"


def test_connected_source_measures_format() -> None:
    raw = ConnectedSourceRaw(database="Sales DB", table="sales_table")
    result = normalize_connected_source(raw)
    assert result.db == "Sales DB"
    assert result.table == "sales_table"
    assert result.column is None


def test_connected_source_dimensions_format() -> None:
    raw = ConnectedSourceRaw(db=161, table="customers", column="CompanyName")
    result = normalize_connected_source(raw)
    assert result.db == 161
    assert result.table == "customers"
    assert result.column == "CompanyName"


def test_connected_source_none() -> None:
    result = normalize_connected_source(None)
    assert result is None


def test_raw_preserved() -> None:
    raw = MeasureRaw(
        measure_name="Revenue",
        data_type="Numeric",
        required=True,
    )
    result = normalize_measure(raw)
    assert result.raw["measure_name"] == "Revenue"
    assert result.raw["data_type"] == "Numeric"
    assert result.raw["required"] is True


def test_nullable_fields() -> None:
    raw = MeasureRaw()
    result = normalize_measure(raw)
    assert result.name is None
    assert result.description is None
    assert result.formula is None
    assert result.connected_source is None


def test_build_semantic_context_stats() -> None:
    project = CanonicalProject(id=1, name="Test", description=None)
    version = CanonicalVersion(id=10, name="v1", is_global=True)
    m1 = normalize_measure(MeasureRaw(measure_name="M1"))
    m2 = normalize_measure(MeasureRaw(measure_name="M2"))
    d1 = normalize_dimension(DimensionRaw(dimension_name="D1"))

    ctx = build_semantic_context(project, version, [m1, m2], [d1])
    assert ctx.stats.measure_count == 2
    assert ctx.stats.dimension_count == 1
    assert ctx.project.id == 1
    assert ctx.version.name == "v1"


def test_unknown_fields_ignored() -> None:
    raw = MeasureRaw.model_validate(
        {"measure_name": "Test", "some_new_field": "value", "another": 42}
    )
    result = normalize_measure(raw)
    assert result.name == "Test"
    assert "some_new_field" in result.raw


def test_batch_normalize() -> None:
    measures = normalize_measures(
        [MeasureRaw(measure_name="A"), MeasureRaw(measure_name="B")]
    )
    assert len(measures) == 2
    assert measures[0].name == "A"

    dimensions = normalize_dimensions(
        [DimensionRaw(dimension_name="X"), DimensionRaw(dimension_name="Y")]
    )
    assert len(dimensions) == 2
    assert dimensions[1].name == "Y"
