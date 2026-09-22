"""Response fixtures copied from the DataForge Public API v2 documentation.

These are transcriptions of the example payloads in the product API doc (IM-9,
sections 9.9.2, 9.9.4, 9.9.8, 9.9.9, 9.9.11), not invented shapes. When the API changes,
this file is what gets updated first.
"""

from __future__ import annotations

from typing import Any

RATE_LIMIT_HEADERS = {
    "X-RateLimit-Limit": "100",
    "X-RateLimit-Remaining": "7",
    "X-RateLimit-Reset": "1780000000",
}


def pagination(total: int = 1, page: int = 1, page_size: int = 100, pages: int = 1) -> dict:
    return {"total": total, "page": page, "pageSize": page_size, "totalPages": pages}


# --- 9.9.2.1 / 9.9.2.2 -----------------------------------------------------

PROJECTS_200: dict[str, Any] = {
    "projects": [
        {"id": 12, "name": "Sales Analytics", "description": "Production sales warehouse"},
        {"id": 13, "name": "Finance", "description": None},
    ],
    "pagination": pagination(total=2),
}

VERSIONS_200: dict[str, Any] = {
    "versions": [{"id": 33, "name": "Q4 2025", "is_global": True}],
    "pagination": pagination(),
}

# --- 9.9.2.3 measures ------------------------------------------------------

MEASURE_ROW: dict[str, Any] = {
    "id": "1000",
    "row_number": 1,
    "group": "Revenue",
    "block": "Sales",
    "measure_name": "Total revenue",
    "measure_description": "Gross revenue across all channels",
    "original_source_type": "Database",
    "original_source": "ERP",
    "original_object": "sales.amount",
    "display_data_type": "Number",
    "measure_type": "Base",
    "restrictions": None,
    "formula": None,
    "report_for_verification": None,
    "comment": None,
    "status": "Active",
    "relevance": None,
    "required": None,
    "visibility": None,
    "responsible_for_data": None,
    "variation": None,
}

MEASURES_200: dict[str, Any] = {
    "measures": [MEASURE_ROW],
    "pagination": pagination(total=1),
}

# 9.9.3 — sql_code is only present when generation succeeded.
MEASURES_200_WITH_SQL: dict[str, Any] = {
    "measures": [
        {
            **MEASURE_ROW,
            "sql_code": {
                "generated_at": "2026-05-29T08:00:00.000Z",
                "sql_scripts": [
                    {
                        "fact_table_id": "11",
                        "fact_table_name": "fact_sales",
                        "sql": "SELECT SUM(amount) FROM fact_sales WHERE ...",
                    }
                ],
            },
        }
    ],
    "pagination": pagination(total=1),
}

# --- 9.9.2.4 dimensions ----------------------------------------------------

CONNECTED_SOURCE: dict[str, Any] = {
    "connection": "Production PostgreSQL",
    "db": "analytics_db",
    "schema": "public",
    "table": "dim_customer",
    "column": "customer_name",
}

DIMENSION_ROW: dict[str, Any] = {
    "id": "2000",
    "row_number": 1,
    "group": "Customer",
    "block": "Profile",
    "dimension_name": "Customer name",
    "dimension_description": "Full customer name",
    "original_source_type": None,
    "original_source": None,
    "original_object": None,
    "dimension_group": "Customers",
    "display_data_type": "Text",
    "source_data_type": "VARCHAR(255)",
    "dimension_type": "Primary",
    "formula": None,
    "connected_source": CONNECTED_SOURCE,
    "comment": None,
    "value_options": None,
    "status": "Active",
    # Reference columns come back as localized labels, never as booleans.
    "relevance": "Да",
    "required": "Да",
    "visibility": "Нет",
    "responsible_for_data": None,
}

DIMENSIONS_200: dict[str, Any] = {
    "dimensions": [DIMENSION_ROW],
    "pagination": pagination(total=1),
}

# --- 9.9.2.5 facts ---------------------------------------------------------

FACT_ROW: dict[str, Any] = {
    "id": "3000",
    "row_number": 1,
    "group": "Sales",
    "block": "Orders",
    "fact_name": "Order line",
    "fact_description": "An individual line item on a sales order",
    "original_source_type": None,
    "original_source": None,
    "original_object": None,
    "source_data_type": "DECIMAL(18,2)",
    "fact_type": "Primary",
    "formula": None,
    "connected_source": {
        "connection": "Production PostgreSQL",
        "db": "analytics_db",
        "schema": "public",
        "table": "fact_order_line",
        "column": "amount",
    },
    "report_for_verification": None,
    "comment": None,
    "status": None,
    "relevance": None,
    "required": None,
    "visibility": None,
    "responsible_for_data": None,
}

FACTS_200: dict[str, Any] = {"facts": [FACT_ROW], "pagination": pagination(total=1)}

# --- 9.9.2.7 / 9.9.2.8 dimension groups ------------------------------------

DIMENSION_GROUP_PK: dict[str, Any] = {
    "connection": "Production PostgreSQL",
    "db": "analytics_db",
    "schema": "public",
    "table": "dim_customer",
    "column": "customer_id",
}

DIMENSION_GROUPS_200: dict[str, Any] = {
    "dimension_groups": [
        {
            "id": "1204",
            "name": "Calendar",
            "description": "Date hierarchy",
            "primary_key": DIMENSION_GROUP_PK,
            "related_fact_tables": ["6784"],
        }
    ],
    "pagination": pagination(total=1),
}

DIMENSION_GROUP_DETAIL_200: dict[str, Any] = {
    "id": "1204",
    "name": "Calendar",
    "description": "Date hierarchy",
    "primary_key": DIMENSION_GROUP_PK,
    "dimensions": [
        {
            "id": "33929",
            "name": "Year",
            "description": "Year of the period",
            "level": 1,
            "display_data_type": "Number",
            "physical_column": "year",
        }
    ],
    "related_fact_tables": [
        {
            "fact_table_id": "6784",
            "fact_table_name": "Sales and refunds",
            "foreign_key_column": "date_id",
        }
    ],
}

# --- 9.9.2.9 / 9.9.2.10 fact tables ----------------------------------------

FACT_TABLES_200: dict[str, Any] = {
    "fact_tables": [
        {
            "id": "6784",
            "name": "Sales and refunds",
            "description": "Fact table with sales and refunds",
            "owner": "Алёна Зубакова",
            "created_at": "2026-05-21T13:23:10.621Z",
            "measures_count": 12,
            "dimensions_count": 8,
            "facts_count": 3,
            "verification_filters_count": 1,
            "related_dimension_groups_count": 2,
        }
    ],
    "pagination": pagination(total=1),
}

FACT_TABLE_DETAIL_200: dict[str, Any] = {
    "id": "6784",
    "name": "Sales and refunds",
    "description": None,
    "owner": "Алёна Зубакова",
    "created_at": "2026-05-21T13:23:10.621Z",
    "measures": [
        {
            "id": "1000",
            "name": "Total revenue",
            "description": None,
            "formula": None,
            "display_data_type": "Number",
            # Fact table details use raw slugs, unlike the RMD listings.
            "measure_type": "base",
        }
    ],
    "dimensions": [
        {
            "id": "2000",
            "name": "Customer name",
            "dimension_type": "primary",
            "physical_column": "customer_name",
            "is_from_dimension_group": True,
            "dimension_group_id": "1204",
        }
    ],
    "facts": [{"id": "3000", "name": "Order line", "fact_type": "primary"}],
    "dimension_groups": [
        {
            "id": "1204",
            "name": "Calendar",
            "primary_key": DIMENSION_GROUP_PK,
            "foreign_key": {
                "connection": "Production PostgreSQL",
                "db": "analytics_db",
                "schema": "public",
                "table": "fact_order_line",
                "column": "date_id",
            },
        }
    ],
    "verification_filters": [
        {
            "id": "77",
            "name": "Positive amounts",
            "description": None,
            "conditions": "[Order line] > 0",
            "is_valid": True,
        }
    ],
}

FACT_TABLE_DETAIL_WITH_DEPS_200: dict[str, Any] = {
    **FACT_TABLE_DETAIL_200,
    "measures": [
        {
            **FACT_TABLE_DETAIL_200["measures"][0],
            "dependencies": [
                {"id": "3000", "name": "Order line", "type": "fact", "dependencies": []}
            ],
        }
    ],
}

# --- 9.9.2.11 / 9.9.2.12 relationships -------------------------------------

RELATIONSHIP_ROW: dict[str, Any] = {
    "id": "501",
    "source_fact_table": {"id": "6784", "name": "Sales and refunds"},
    "target_dimension_group": {"id": "1204", "name": "Calendar"},
    "foreign_key": {
        "connection": "Production PostgreSQL",
        "db": "analytics_db",
        "schema": "public",
        "table": "fact_order_line",
        "column": "date_id",
    },
    "primary_key": DIMENSION_GROUP_PK,
    # v2 returns the raw slug; v1 returned a localized label.
    "relationship_type": "many_to_one",
}

RELATIONSHIPS_200: dict[str, Any] = {
    "relationships": [RELATIONSHIP_ROW],
    "pagination": pagination(total=1),
}

RELATIONSHIP_DETAIL_200: dict[str, Any] = RELATIONSHIP_ROW

# --- 9.9.2.6 consolidated RMD export ---------------------------------------

RMD_EXPORT_200: dict[str, Any] = {
    "project": {"id": "12", "name": "Sales Analytics", "description": "Production warehouse"},
    "version": {"id": "33", "name": "Q4 2025", "is_global": True},
    "measures": [MEASURE_ROW],
    "dimensions": [DIMENSION_ROW],
    "facts": [FACT_ROW],
    "dimension_groups": DIMENSION_GROUPS_200["dimension_groups"],
    "fact_tables": FACT_TABLES_200["fact_tables"],
    "relationships": [RELATIONSHIP_ROW],
    "exported_at": "2026-05-29T08:00:00.000Z",
}

# --- 9.9.8 data marts ------------------------------------------------------

DATA_MARTS_200: dict[str, Any] = {
    "data_marts": [
        {
            "id": "9666",
            "name": "DF Fashion retail sales only",
            "description": "Витрина с продажами без планов",
            "owner": "Алёна Зубакова",
            "created_at": "2026-05-21T13:23:10.621Z",
            "type": "С группировкой",
            "merge_type": None,
            "source_fact_table_count": 1,
            "has_physical_view": False,
        }
    ],
    "pagination": pagination(total=2),
}

DATA_MART_DETAIL_200: dict[str, Any] = {
    "id": "9667",
    "name": "DF Fashion retail sales and plans",
    "description": "Объединенная витрина с продажами и планами",
    "owner": "Алёна Зубакова",
    "created_at": "2026-05-21T13:23:10.621Z",
    "type": "С группировкой",
    "merge_type": "join",
    "source_fact_tables": [
        {"id": "6784", "name": "Sales and refunds", "description": "Fact table"}
    ],
    "selected_measures": [
        {
            "instance_id": "155341",
            "measure_id": "33540",
            "measure_name": "Items Gross, count",
            "description": "Количество уникальных проданных позиций",
            "formula": "COUNTDISTINCT({[operation_id]=1} [Receipt position])",
            "data_type": "Number",
            "display_name": "Items Gross, count",
            "aggregation_configuration": {"type": "default", "group_by_fields": []},
            "source_fact_table_id": "6784",
        }
    ],
    "selected_facts": [
        {
            "fact_id": "611",
            "fact_name": "Order line",
            "description": None,
            "data_type": "Number",
            "display_name": "Order line",
            "include_in_result": True,
            "filter_condition": None,
            "source_fact_table_id": "6784",
        }
    ],
    "selected_dimensions": [
        {
            "dimension_id": "33929",
            "dimension_name": "Year",
            "description": "Год периода в диапазоне фильтра",
            "data_type": "Number",
            "display_name": "Year",
            "include_in_result": True,
            "filter_condition": "[Year] >= 2020",
            "source_fact_table_id": "6785",
            "source_dimension_group_id": "1204",
            "source_dimension_group_name": "Calendar",
        }
    ],
    # The embedded physical view has no `connection` key — only the /view endpoint does.
    "physical_view": {
        "exists": False,
        "type": None,
        "database": None,
        "schema": None,
        "name": None,
        "created_at": None,
        "status": None,
        "is_stale": None,
        "last_refresh_at": None,
    },
}

DATA_MART_DETAIL_PIVOT_200: dict[str, Any] = {
    **DATA_MART_DETAIL_200,
    "type": "С группировкой и сверткой",
    "selected_measure_attributes": [
        {"attribute_id": "18", "attribute_name": "Measure name"},
        {"attribute_id": "24", "attribute_name": "Measure description"},
    ],
}

PHYSICAL_VIEW_EXISTS_200: dict[str, Any] = {
    "exists": True,
    "type": "Материализованное представление",
    "database": "clickhouse",
    "schema": "dataforge_test",
    "name": "materialized_view_6839_datamart_DF Fashion retail sales only",
    "created_at": "2026-03-17T12:44:45.000Z",
    "status": "active",
    "is_stale": False,
    "last_refresh_at": "2026-08-30T03:00:12.000Z",
    "connection": {"id": "3160", "name": "Click", "db_type": "clickhouse"},
}

PHYSICAL_VIEW_ABSENT_200: dict[str, Any] = {
    "exists": False,
    "type": None,
    "database": None,
    "schema": None,
    "name": None,
    "created_at": None,
    "status": None,
    "is_stale": None,
    "last_refresh_at": None,
    "connection": None,
}

GENERATE_SQL_OK_200: dict[str, Any] = {
    "sql_script": "SELECT ... FROM ... GROUP BY ... LIMIT 100 OFFSET 0",
    "target_db_type": "clickhouse",
    "validation_errors": [],
}

# Generation failure is still HTTP 200 — that is what distinguishes it from a 404.
GENERATE_SQL_FAILED_200: dict[str, Any] = {
    "sql_script": "",
    "target_db_type": None,
    "validation_errors": [
        {
            "code": "SQL_GENERATION_FAILED",
            "message": 'Внешний ключ не настроен для группы измерений "География"',
        }
    ],
}

# --- 9.9.9 connections -----------------------------------------------------

CONNECTIONS_200: dict[str, Any] = {
    "connections": [
        {
            "id": "3821",
            "name": "Production PostgreSQL",
            "db_type": "postgresql",
            "host": "db.production.company.com",
            "port": 5432,
            "database": "analytics_db",
            "schema": "public",
            "username": "analytics_user",
            "status": "active",
            "last_updated_at": "2026-05-21T13:23:07.188Z",
        }
    ],
    "pagination": pagination(total=1),
}

CONNECTION_DETAIL_200: dict[str, Any] = {
    **CONNECTIONS_200["connections"][0],
    "db_tables": [{"name": "fact_sales"}, {"name": "dim_customer"}],
}

CONNECTION_DETAIL_WITH_SCHEMA_200: dict[str, Any] = {
    **CONNECTIONS_200["connections"][0],
    "db_schema": {
        "connection": "Production PostgreSQL",
        "tables": [
            {
                "table_name": "fact_sales",
                "schema": "public",
                "columns": [
                    {"column_name": "amount", "data_type": "numeric"},
                    {"column_name": "date_id", "data_type": "integer"},
                ],
            }
        ],
    },
}

CONNECTION_SCHEMA_200: dict[str, Any] = {
    "id": "3821",
    "name": "Production PostgreSQL",
    "db_type": "postgresql",
    "last_updated_at": "2026-05-21T13:23:07.188Z",
    "schema": CONNECTION_DETAIL_WITH_SCHEMA_200["db_schema"],
}

# --- 9.9.7 project access --------------------------------------------------

PROJECT_ACCESS_200: list[dict[str, Any]] = [
    {
        "id": 7,
        "first_name": "Pavel",
        "last_name": "Shalavin",
        "email": "pavel@example.com",
        "isOwner": True,
        "globalRole": "Администратор",
        "projectRole": "Разработчик",
    }
]

# --- 9.9.11 Git connections ------------------------------------------------

GIT_CONNECTION: dict[str, Any] = {
    "id": "17",
    "name": "Config repository",
    "platform": "gitlab",
    "repository_url": "https://gitlab.example.com/analytics/dataforge-config.git",
    "branch": "main",
    "path": "/sales",
    "status": "active",
    "last_used": "2026-05-05T08:30:00.000Z",
    "created_at": "2026-04-01T10:00:00.000Z",
    "created_by": "admin@example.com",
    "shared": False,
    "default": True,
}

# The listing key is hyphenated in the wire format.
GIT_CONNECTIONS_200: dict[str, Any] = {
    "git-connections": [GIT_CONNECTION],
    "pagination": pagination(total=1, page_size=20),
}

GIT_CONNECTION_TEST_200: dict[str, Any] = {
    "git-connection_id": "17",
    "status": "success",
    "tests": {
        "repository_reachable": True,
        "authentication_valid": True,
        "branch_exists": True,
        "write_permission": True,
        "path_accessible": True,
    },
    "details": {"last_commit": "3f2a9c1"},
}

GIT_CONNECTION_TEST_FAILED_200: dict[str, Any] = {
    **GIT_CONNECTION_TEST_200,
    "status": "failed",
    "tests": {**GIT_CONNECTION_TEST_200["tests"], "write_permission": False},
}

# --- write responses (9.9.6) ----------------------------------------------

MEASURE_CREATED_201: dict[str, Any] = {
    **MEASURE_ROW,
    "timestamp": "2026-05-05T08:30:00.120Z",
}

BULK_PARTIAL_207: dict[str, Any] = {
    "timestamp": "2026-05-05T08:30:00.120Z",
    "succeeded": [MEASURE_ROW],
    "failed": [
        {
            "index": 1,
            "error": {
                "code": "duplicate_name",
                "message": "Показатель с таким именем уже существует",
                "details": [{"field": "measure_name", "code": "invalid_value"}],
            },
        }
    ],
}

ASSIGN_PARTIAL_207: dict[str, Any] = {
    "timestamp": "2026-05-05T08:30:00.120Z",
    "succeeded": [{"id": "501"}],
    "failed": [
        {
            "index": 1,
            "id": "502",
            "error": {
                "code": "constraint_violation",
                "message": "Элемент уже назначен",
                "details": [],
            },
        }
    ],
}

EXPORT_GIT_200: dict[str, Any] = {
    "success": True,
    "commit_hash": "3f2a9c1e7b0d4a6f8c2e1b9d7a5c3e1f0b8d6a4c",
    "repository_url": "https://gitlab.example.com/analytics/dataforge-config.git",
    "branch": "main",
    "path": "/sales",
    "files_created": 128,
    "timestamp": "2026-05-05T08:30:00.120Z",
    "connection_id": None,
}

EXPORT_FILE_200: dict[str, Any] = {
    "download_url": "https://storage.example.com/exports/...?signature=...",
    "file_name": "Sales Analytics_Q4 2025.dfexport.zip",
    "file_size": 48213,
    "expires_at": "2026-05-05T09:30:00.000Z",
}

IMPORT_VALIDATE_200: dict[str, Any] = {
    "valid": True,
    "errors": [],
    "warnings": [],
    "summary": {"measures": 42, "dimensions": 18, "facts": 6},
    "schema_version": "1.0",
}

IMPORT_PREVIEW_200: dict[str, Any] = {
    "preview_id": "0b1d2c3e-4f5a-6789-abcd-ef0123456789",
    "summary": {"measures": {"added": 3, "modified": 5, "deleted": 0, "total": 45}},
    "conflicts": [],
    "conflict_resolution_required": False,
}

IMPORT_GIT_200: dict[str, Any] = {
    "success": True,
    "import_id": "7c0e4b2a-1d3f-4e5a-9b8c-6d7e8f9a0b1c",
    "target_project_id": "12",
    "target_version_id": "35",
    "target_version_name": "staging_4711",
    "summary": {"measures": {"added": 3, "modified": 5, "deleted": 0, "total": 45}},
    "conflicts": [],
    "conflict_resolution_required": False,
}

SUCCESS_FLAG: dict[str, Any] = {"success": True}

# --- error envelopes (9.9.4, 9.11) -----------------------------------------


def error_envelope(
    message: str,
    original: str,
    status: int,
    code: str,
    details: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "message": message,
        "originalMessage": original,
        "statusCode": status,
        "error": "HttpException",
        "code": code,
        "details": details or [],
    }


ERR_404_DATA_MART = error_envelope(
    "Data mart not found",
    "DF_API.DATA_MART_NOT_FOUND",
    404,
    "data_mart_not_found",
    [{"field": "data_mart_id", "code": "data_mart_not_found"}],
)

ERR_404_PROJECT = error_envelope(
    "Project not found", "DF_API.PROJECT_NOT_FOUND", 404, "project_not_found"
)

ERR_400_INVALID_MERGE_TYPE = error_envelope(
    "Некорректное значение фильтра merge_type",
    "DF_API.INVALID_MERGE_TYPE",
    400,
    "invalid_merge_type",
    [{"field": "merge_type", "code": "invalid_value"}],
)

ERR_400_VALIDATION_FAILED = error_envelope(
    "Body does not match the schema",
    "DF_API.VALIDATION_FAILED",
    400,
    "validation_failed",
    [{"field": "measures.1.measure_type", "code": "invalid_value"}],
)

ERR_403_WRITE_ACCESS_DENIED = error_envelope(
    "Write access denied", "DF_API.WRITE_ACCESS_DENIED", 403, "write_access_denied"
)

ERR_409_DUPLICATE_NAME = error_envelope(
    "A measure with this name already exists",
    "DF_API.DUPLICATE_NAME",
    409,
    "duplicate_name",
    [{"field": "measure_name", "code": "invalid_value"}],
)

ERR_409_IDEMPOTENCY_IN_PROGRESS = error_envelope(
    "A request with the same Idempotency-Key is still running",
    "DF_API.IDEMPOTENCY_IN_PROGRESS",
    409,
    "idempotency_in_progress",
)

ERR_422_BULK_REJECTED = error_envelope(
    "No row was applied",
    "DF_API.BULK_REJECTED",
    422,
    "bulk_rejected",
    [{"field": "measures.0", "code": "invalid_value"}],
)

ERR_422_INVALID_FORMULA = error_envelope(
    "Formula could not be parsed",
    "DF_API.INVALID_FORMULA_SYNTAX",
    422,
    "invalid_formula_syntax",
    [{"field": "formula", "code": "invalid_value"}],
)

ERR_429_RATE_LIMIT = error_envelope(
    "Too many requests", "DF_API.RATE_LIMIT_EXCEEDED", 429, "rate_limit_exceeded"
)

ERR_401_INVALID_API_KEY = error_envelope(
    "Invalid API key", "DF_API.INVALID_API_KEY", 401, "invalid_api_key"
)
