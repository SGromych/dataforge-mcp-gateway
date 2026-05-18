"""Tests for the normalizer."""

from dataforge_mcp.dataforge.schemas import (
    ConnectedSourceRaw,
    DimensionRaw,
    FactRaw,
    MeasureRaw,
)
from dataforge_mcp.semantic.models import CanonicalProject, CanonicalVersion
from dataforge_mcp.semantic.normalizer import (
    build_semantic_context,
    normalize_connected_source,
    normalize_dimension,
    normalize_dimensions,
    normalize_fact,
    normalize_facts,
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


def test_fact_name_normalized() -> None:
    raw = FactRaw(fact_name="Order Amount", fact_description="Total order amount")
    result = normalize_fact(raw)
    assert result.name == "Order Amount"
    assert result.description == "Total order amount"


def test_fact_fields() -> None:
    raw = FactRaw(
        row_number="1",
        group="Sales",
        block="Orders",
        fact_name="Order Amount",
        fact_type="Additive",
        source_data_type="Decimal",
        formula="[Amount]",
        status="Active",
        required=True,
    )
    result = normalize_fact(raw)
    assert result.row_number == "1"
    assert result.group == "Sales"
    assert result.fact_type == "Additive"
    assert result.source_data_type == "Decimal"
    assert result.formula == "[Amount]"
    assert result.required is True


def test_fact_connected_source() -> None:
    raw = FactRaw(
        fact_name="Test",
        connected_source=ConnectedSourceRaw(database="DB", table="orders"),
    )
    result = normalize_fact(raw)
    assert result.connected_source is not None
    assert result.connected_source.db == "DB"
    assert result.connected_source.table == "orders"


def test_fact_raw_preserved() -> None:
    raw = FactRaw(fact_name="Revenue", fact_type="Additive")
    result = normalize_fact(raw)
    assert result.raw["fact_name"] == "Revenue"
    assert result.raw["fact_type"] == "Additive"


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


def test_nullable_fact_fields() -> None:
    raw = FactRaw()
    result = normalize_fact(raw)
    assert result.name is None
    assert result.description is None
    assert result.formula is None
    assert result.connected_source is None
    assert result.fact_type is None


def test_build_semantic_context_stats() -> None:
    project = CanonicalProject(id=1, name="Test", description=None)
    version = CanonicalVersion(id=10, name="v1", is_global=True)
    m1 = normalize_measure(MeasureRaw(measure_name="M1"))
    m2 = normalize_measure(MeasureRaw(measure_name="M2"))
    d1 = normalize_dimension(DimensionRaw(dimension_name="D1"))

    ctx = build_semantic_context(project, version, [m1, m2], [d1])
    assert ctx.stats.measure_count == 2
    assert ctx.stats.dimension_count == 1
    assert ctx.stats.fact_count == 0
    assert ctx.project.id == 1
    assert ctx.version.name == "v1"


def test_build_semantic_context_with_facts() -> None:
    project = CanonicalProject(id=1, name="Test", description=None)
    version = CanonicalVersion(id=10, name="v1", is_global=True)
    m1 = normalize_measure(MeasureRaw(measure_name="M1"))
    d1 = normalize_dimension(DimensionRaw(dimension_name="D1"))
    f1 = normalize_fact(FactRaw(fact_name="F1"))
    f2 = normalize_fact(FactRaw(fact_name="F2"))

    ctx = build_semantic_context(project, version, [m1], [d1], [f1, f2])
    assert ctx.stats.measure_count == 1
    assert ctx.stats.dimension_count == 1
    assert ctx.stats.fact_count == 2
    assert len(ctx.facts) == 2
    assert ctx.facts[0].name == "F1"


def test_unknown_fields_ignored() -> None:
    raw = MeasureRaw.model_validate(
        {"measure_name": "Test", "some_new_field": "value", "another": 42}
    )
    result = normalize_measure(raw)
    assert result.name == "Test"
    assert "some_new_field" in result.raw


def test_batch_normalize() -> None:
    measures = normalize_measures([MeasureRaw(measure_name="A"), MeasureRaw(measure_name="B")])
    assert len(measures) == 2
    assert measures[0].name == "A"

    dimensions = normalize_dimensions(
        [DimensionRaw(dimension_name="X"), DimensionRaw(dimension_name="Y")]
    )
    assert len(dimensions) == 2
    assert dimensions[1].name == "Y"


def test_batch_normalize_facts() -> None:
    facts = normalize_facts(
        [FactRaw(fact_name="F1"), FactRaw(fact_name="F2"), FactRaw(fact_name="F3")]
    )
    assert len(facts) == 3
    assert facts[0].name == "F1"
    assert facts[2].name == "F3"
