"""
Phase 1 · 集成测试 — DuckDB 客户端
覆盖任务：P1-B6（建表、批量写入、SQL 查询直通）

测试对象：backend/app/db/duckdb_client.py :: DuckDBClient
使用临时内存数据库，无需运行中的服务。
"""

import pytest
from app.db.duckdb_client import DuckDBClient
from app.core.schema_model import (
    RelationalSchemaModel, TableDef, ColumnDef, ForeignKeyDef
)


@pytest.fixture
def client():
    """每个测试函数使用独立的内存数据库。"""
    c = DuckDBClient(":memory:")
    yield c
    c.close()


def simple_schema() -> RelationalSchemaModel:
    return RelationalSchemaModel(tables=[
        TableDef(
            name="users",
            columns=[
                ColumnDef(name="id",       type_category="integer", primary_key=True),
                ColumnDef(name="email",    type_category="string",  nullable=False, unique=True, length=120),
                ColumnDef(name="username", type_category="string",  nullable=False, unique=True, length=50),
                ColumnDef(name="age",      type_category="integer", nullable=True),
            ],
        )
    ])


def ecommerce_schema() -> RelationalSchemaModel:
    return RelationalSchemaModel(tables=[
        TableDef(
            name="categories",
            columns=[
                ColumnDef(name="id",   type_category="integer", primary_key=True),
                ColumnDef(name="name", type_category="string",  nullable=False),
            ],
        ),
        TableDef(
            name="products",
            columns=[
                ColumnDef(name="id",          type_category="integer", primary_key=True),
                ColumnDef(name="category_id", type_category="integer", nullable=False),
                ColumnDef(name="name",        type_category="string",  nullable=False),
                ColumnDef(name="price",       type_category="decimal", nullable=False),
            ],
            foreign_keys=[
                ForeignKeyDef(column="category_id", ref_table="categories", ref_column="id")
            ],
        ),
    ])


# ── DDL 建表 ──────────────────────────────────────────────────────────────────

class TestTableCreation:
    def test_create_tables_from_schema(self, client):
        client.create_tables(simple_schema())
        tables = client.list_tables()
        assert "users" in tables

    def test_created_table_has_correct_columns(self, client):
        client.create_tables(simple_schema())
        cols = {c["name"] for c in client.describe_table("users")}
        assert cols == {"id", "email", "username", "age"}

    def test_create_multiple_tables(self, client):
        client.create_tables(ecommerce_schema())
        tables = set(client.list_tables())
        assert {"categories", "products"}.issubset(tables)

    def test_idempotent_create(self, client):
        client.create_tables(simple_schema())
        client.create_tables(simple_schema())  # 第二次不应抛出
        assert "users" in client.list_tables()

    def test_reset_clears_all_tables(self, client):
        client.create_tables(simple_schema())
        client.reset()
        assert "users" not in client.list_tables()


# ── 数据写入 ──────────────────────────────────────────────────────────────────

class TestDataInsertion:
    def test_insert_rows(self, client):
        client.create_tables(simple_schema())
        rows = [
            {"id": 1, "email": "a@a.com", "username": "alice", "age": 30},
            {"id": 2, "email": "b@b.com", "username": "bob",   "age": None},
        ]
        client.insert_rows("users", rows)
        count = client.query("SELECT COUNT(*) AS cnt FROM users")
        assert count[0]["cnt"] == 2

    def test_insert_empty_rows_no_error(self, client):
        client.create_tables(simple_schema())
        client.insert_rows("users", [])  # 不应抛出

    def test_insert_large_batch(self, client):
        client.create_tables(simple_schema())
        rows = [{"id": i, "email": f"u{i}@x.com", "username": f"user{i}", "age": i % 80}
                for i in range(1, 10_001)]
        client.insert_rows("users", rows)
        count = client.query("SELECT COUNT(*) AS cnt FROM users")[0]["cnt"]
        assert count == 10_000

    def test_null_inserted_correctly(self, client):
        client.create_tables(simple_schema())
        client.insert_rows("users", [
            {"id": 1, "email": "x@x.com", "username": "x", "age": None}
        ])
        row = client.query("SELECT age FROM users LIMIT 1")[0]
        assert row["age"] is None


# ── SQL 查询 ──────────────────────────────────────────────────────────────────

class TestSQLQuery:
    @pytest.fixture(autouse=True)
    def _seed(self, client):
        client.create_tables(simple_schema())
        client.insert_rows("users", [
            {"id": i, "email": f"u{i}@x.com", "username": f"user{i}", "age": 20 + i}
            for i in range(1, 11)
        ])

    def test_select_all(self, client):
        rows = client.query("SELECT * FROM users")
        assert len(rows) == 10

    def test_where_clause(self, client):
        rows = client.query("SELECT * FROM users WHERE age > 25")
        assert all(r["age"] > 25 for r in rows)

    def test_count_aggregation(self, client):
        result = client.query("SELECT COUNT(*) AS cnt FROM users")
        assert result[0]["cnt"] == 10

    def test_query_returns_dict_list(self, client):
        rows = client.query("SELECT id, email FROM users LIMIT 1")
        assert isinstance(rows, list)
        assert isinstance(rows[0], dict)
        assert "id" in rows[0] and "email" in rows[0]

    def test_write_query_blocked(self, client):
        with pytest.raises(PermissionError):
            client.query("DELETE FROM users")

    def test_drop_table_blocked(self, client):
        with pytest.raises(PermissionError):
            client.query("DROP TABLE users")

    def test_empty_result(self, client):
        rows = client.query("SELECT * FROM users WHERE id = -9999")
        assert rows == []


# ── Schema 元数据 ─────────────────────────────────────────────────────────────

class TestSchemaMetadata:
    def test_list_tables_with_columns(self, client):
        client.create_tables(ecommerce_schema())
        meta = client.get_er_schema()
        table_names = {t["name"] for t in meta["tables"]}
        assert {"categories", "products"}.issubset(table_names)

    def test_er_schema_includes_fk(self, client):
        client.create_tables(ecommerce_schema())
        meta = client.get_er_schema()
        fk_pairs = {(fk["from_table"], fk["to_table"]) for fk in meta["foreign_keys"]}
        assert ("products", "categories") in fk_pairs
