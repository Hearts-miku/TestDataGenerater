"""
E2E：DuckDB SQL Explorer API
验证 POST /api/db/sql 与 GET /api/db/tables 端点的功能与安全性。
"""

import pytest
from conftest import parse_ddl, generate, sql_query


@pytest.fixture(autouse=True)
def _seed_ecommerce(client, ddl_ecommerce):
    """所有用例共用一次电商数据生成结果。"""
    schema = parse_ddl(client, ddl_ecommerce)
    generate(client, schema["schema_id"], row_counts={
        "categories": 5, "products": 20,
        "users": 10, "orders": 25, "order_items": 60,
    })


class TestTableListEndpoint:
    def test_all_tables_listed(self, client):
        resp = client.get("/api/db/tables")
        assert resp.status_code == 200
        names = {t["name"] for t in resp.json()["tables"]}
        assert {"categories", "products", "users", "orders", "order_items"}.issubset(names)

    def test_table_entry_has_columns(self, client):
        resp = client.get("/api/db/tables")
        users_table = next(t for t in resp.json()["tables"] if t["name"] == "users")
        col_names = {c["name"] for c in users_table["columns"]}
        assert {"id", "email", "username"}.issubset(col_names)

    def test_er_schema_endpoint_returns_fk_info(self, client):
        resp = client.get("/api/db/er-schema")
        assert resp.status_code == 200
        fks = resp.json()["foreign_keys"]
        fk_pairs = {(fk["from_table"], fk["to_table"]) for fk in fks}
        assert ("products", "categories") in fk_pairs
        assert ("orders", "users") in fk_pairs


class TestSQLQueryExecution:
    def test_simple_select(self, client):
        result = sql_query(client, "SELECT COUNT(*) AS cnt FROM users")
        assert result["rows"][0]["cnt"] == 10

    def test_join_query(self, client):
        result = sql_query(client, """
            SELECT u.username, COUNT(o.id) AS order_count
            FROM users u
            LEFT JOIN orders o ON o.user_id = u.id
            GROUP BY u.username
            ORDER BY order_count DESC
            LIMIT 5
        """)
        assert len(result["rows"]) <= 5
        assert all("username" in r and "order_count" in r for r in result["rows"])

    def test_aggregation_query(self, client):
        result = sql_query(client, """
            SELECT status, COUNT(*) AS cnt, AVG(total_amount) AS avg_amount
            FROM orders
            GROUP BY status
        """)
        assert len(result["rows"]) >= 1
        statuses = {r["status"] for r in result["rows"]}
        assert statuses.issubset({"pending", "paid", "shipped", "completed", "cancelled"})

    def test_subquery(self, client):
        result = sql_query(client, """
            SELECT p.name, p.price
            FROM products p
            WHERE p.price > (SELECT AVG(price) FROM products)
            ORDER BY p.price DESC
        """)
        assert isinstance(result["rows"], list)

    def test_result_includes_column_metadata(self, client):
        result = sql_query(client, "SELECT id, email FROM users LIMIT 1")
        assert "columns" in result
        col_names = [c["name"] for c in result["columns"]]
        assert "id" in col_names
        assert "email" in col_names

    def test_empty_result_set(self, client):
        result = sql_query(client, "SELECT * FROM users WHERE id = -9999")
        assert result["rows"] == []
        assert result["row_count"] == 0


class TestSQLQuerySecurity:
    def test_drop_table_blocked(self, client):
        resp = client.post("/api/db/sql", json={"sql": "DROP TABLE users"})
        assert resp.status_code == 403

    def test_delete_blocked(self, client):
        resp = client.post("/api/db/sql", json={"sql": "DELETE FROM users"})
        assert resp.status_code == 403

    def test_insert_blocked(self, client):
        resp = client.post(
            "/api/db/sql",
            json={"sql": "INSERT INTO users (email, username) VALUES ('x@x.com', 'x')"},
        )
        assert resp.status_code == 403

    def test_syntax_error_returns_400(self, client):
        resp = client.post("/api/db/sql", json={"sql": "SELECT * FORM users"})
        assert resp.status_code == 400
        assert "error" in resp.json()
