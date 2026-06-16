"""
E2E：DDL 解析 API
验证 POST /api/parse 对各种 DDL 输入的解析结果是否符合预期。
"""

import pytest
from conftest import parse_ddl


class TestSimpleDDLParsing:
    def test_returns_table_list(self, client, ddl_simple_users):
        result = parse_ddl(client, ddl_simple_users)
        tables = result["tables"]
        assert len(tables) == 1
        assert tables[0]["name"] == "users"

    def test_columns_extracted(self, client, ddl_simple_users):
        result = parse_ddl(client, ddl_simple_users)
        cols = {c["name"]: c for c in result["tables"][0]["columns"]}
        assert "id" in cols
        assert "email" in cols
        assert cols["id"]["primary_key"] is True
        assert cols["email"]["nullable"] is False
        assert cols["email"]["unique"] is True

    def test_auto_increment_detected(self, client, ddl_simple_users):
        result = parse_ddl(client, ddl_simple_users)
        id_col = next(c for c in result["tables"][0]["columns"] if c["name"] == "id")
        assert id_col.get("auto_increment") is True


class TestEcommerceDDLParsing:
    def test_all_five_tables_parsed(self, client, ddl_ecommerce):
        result = parse_ddl(client, ddl_ecommerce)
        names = {t["name"] for t in result["tables"]}
        assert names == {"categories", "products", "users", "orders", "order_items"}

    def test_foreign_keys_extracted(self, client, ddl_ecommerce):
        result = parse_ddl(client, ddl_ecommerce)
        table_map = {t["name"]: t for t in result["tables"]}

        # products.category_id → categories.id
        fk = next(
            fk for fk in table_map["products"]["foreign_keys"]
            if fk["column"] == "category_id"
        )
        assert fk["ref_table"] == "categories"
        assert fk["ref_column"] == "id"

    def test_topological_order_correct(self, client, ddl_ecommerce):
        """order_items 必须排在 orders 和 products 之后。"""
        result = parse_ddl(client, ddl_ecommerce)
        order = [t["name"] for t in result["generation_order"]]
        assert order.index("order_items") > order.index("orders")
        assert order.index("order_items") > order.index("products")
        assert order.index("products") > order.index("categories")

    def test_enum_values_captured(self, client, ddl_ecommerce):
        result = parse_ddl(client, ddl_ecommerce)
        table_map = {t["name"]: t for t in result["tables"]}
        status_col = next(c for c in table_map["orders"]["columns"] if c["name"] == "status")
        assert set(status_col["enum_values"]) == {
            "pending", "paid", "shipped", "completed", "cancelled"
        }


class TestAllTypesDDLParsing:
    def test_numeric_types_recognised(self, client, ddl_all_types):
        result = parse_ddl(client, ddl_all_types)
        cols = {c["name"]: c for c in result["tables"][0]["columns"]}
        assert cols["col_tinyint"]["type_category"] == "integer"
        assert cols["col_decimal"]["type_category"] == "decimal"
        assert cols["col_double"]["type_category"] == "float"

    def test_string_types_recognised(self, client, ddl_all_types):
        result = parse_ddl(client, ddl_all_types)
        cols = {c["name"]: c for c in result["tables"][0]["columns"]}
        assert cols["col_varchar"]["type_category"] == "string"
        assert cols["col_text"]["type_category"] == "text"

    def test_temporal_types_recognised(self, client, ddl_all_types):
        result = parse_ddl(client, ddl_all_types)
        cols = {c["name"]: c for c in result["tables"][0]["columns"]}
        assert cols["col_date"]["type_category"] == "date"
        assert cols["col_datetime"]["type_category"] == "datetime"

    def test_nullable_flag_correct(self, client, ddl_all_types):
        result = parse_ddl(client, ddl_all_types)
        cols = {c["name"]: c for c in result["tables"][0]["columns"]}
        assert cols["col_nullable"]["nullable"] is True
        assert cols["col_not_null"]["nullable"] is False


class TestPostgreSQLDialect:
    def test_serial_primary_key(self, client, ddl_postgresql):
        result = parse_ddl(client, ddl_postgresql, dialect="postgresql")
        table_map = {t["name"]: t for t in result["tables"]}
        id_col = next(c for c in table_map["departments"]["columns"] if c["name"] == "id")
        assert id_col["primary_key"] is True
        assert id_col["auto_increment"] is True

    def test_inline_fk_reference(self, client, ddl_postgresql):
        result = parse_ddl(client, ddl_postgresql, dialect="postgresql")
        table_map = {t["name"]: t for t in result["tables"]}
        fk = next(
            fk for fk in table_map["employees"]["foreign_keys"]
            if fk["column"] == "department_id"
        )
        assert fk["ref_table"] == "departments"

    def test_composite_primary_key(self, client, ddl_postgresql):
        result = parse_ddl(client, ddl_postgresql, dialect="postgresql")
        table_map = {t["name"]: t for t in result["tables"]}
        pk_cols = [
            c["name"] for c in table_map["employee_projects"]["columns"]
            if c["primary_key"]
        ]
        assert set(pk_cols) == {"employee_id", "project_id"}


class TestParseErrorHandling:
    def test_invalid_sql_returns_422(self, client):
        resp = client.post(
            "/api/parse",
            json={"source": "NOT VALID SQL @@@@", "type": "ddl", "dialect": "mysql"},
        )
        assert resp.status_code == 422

    def test_empty_input_returns_422(self, client):
        resp = client.post("/api/parse", json={"source": "", "type": "ddl"})
        assert resp.status_code == 422

    def test_unsupported_dialect_returns_422(self, client):
        resp = client.post(
            "/api/parse",
            json={"source": "CREATE TABLE t (id INT);", "type": "ddl", "dialect": "cobol"},
        )
        assert resp.status_code == 422
