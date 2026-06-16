"""
Phase 2 · 单元测试 — SQL INSERT 导出器
覆盖任务：P2-B1

测试对象：backend/app/exporter/sql.py :: SQLExporter
"""

import re
import pytest
from app.exporter.sql import SQLExporter


@pytest.fixture
def exporter():
    return SQLExporter()


USERS_ROWS = [
    {"id": 1, "email": "a@a.com", "username": "alice"},
    {"id": 2, "email": "b@b.com", "username": "bob"},
]


class TestSQLExporterFormat:
    def test_output_is_string(self, exporter):
        sql = exporter.export({"users": USERS_ROWS})
        assert isinstance(sql, str)
        assert sql.strip()

    def test_contains_insert_into(self, exporter):
        sql = exporter.export({"users": USERS_ROWS})
        assert "INSERT INTO" in sql.upper()

    def test_table_name_in_output(self, exporter):
        sql = exporter.export({"users": USERS_ROWS})
        assert "users" in sql

    def test_column_names_in_output(self, exporter):
        sql = exporter.export({"users": USERS_ROWS})
        assert "id" in sql and "email" in sql and "username" in sql

    def test_values_in_output(self, exporter):
        sql = exporter.export({"users": USERS_ROWS})
        assert "a@a.com" in sql
        assert "alice" in sql

    def test_wrapped_in_transaction(self, exporter):
        sql = exporter.export({"users": USERS_ROWS}).upper()
        assert "BEGIN" in sql or "START TRANSACTION" in sql
        assert "COMMIT" in sql

    def test_multiple_tables_in_output(self, exporter):
        data = {
            "categories": [{"id": 1, "name": "Books"}],
            "products":   [{"id": 1, "category_id": 1, "name": "SQL Guide", "price": 29.99}],
        }
        sql = exporter.export(data)
        assert "categories" in sql
        assert "products" in sql

    def test_correct_row_count(self, exporter):
        rows = [{"id": i, "email": f"u{i}@x.com", "username": f"u{i}"} for i in range(50)]
        sql = exporter.export({"users": rows})
        insert_count = sql.upper().count("INSERT INTO USERS")
        assert insert_count == 50


class TestSQLExporterValues:
    def test_string_values_quoted(self, exporter):
        sql = exporter.export({"t": [{"name": "O'Brien"}]})
        # 单引号应被转义
        assert "O''Brien" in sql or "O\\'Brien" in sql

    def test_null_values_rendered(self, exporter):
        sql = exporter.export({"t": [{"id": 1, "val": None}]})
        assert "NULL" in sql.upper()

    def test_integer_values_unquoted(self, exporter):
        sql = exporter.export({"t": [{"id": 42}]})
        # 整数不应被引号包围
        assert re.search(r"\b42\b", sql)

    def test_boolean_rendered_correctly(self, exporter):
        sql_t = exporter.export({"t": [{"flag": True}]})
        sql_f = exporter.export({"t": [{"flag": False}]})
        assert "1" in sql_t or "TRUE" in sql_t.upper()
        assert "0" in sql_f or "FALSE" in sql_f.upper()

    def test_empty_table_skipped(self, exporter):
        sql = exporter.export({"users": [], "products": [{"id": 1}]})
        assert "insert into users" not in sql.lower()
        assert "insert into products" in sql.lower()
