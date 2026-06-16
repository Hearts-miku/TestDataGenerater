"""
Phase 1 · 集成测试 — /api/parse 与 /api/generate（同步模式）
覆盖任务：P1-B7

需要运行中的 uvicorn：uvicorn app.main:app --port 8000
"""

import os
import httpx
import pytest

BASE = os.getenv("DATAFORGE_URL", "http://127.0.0.1:8000")

SIMPLE_DDL = """
CREATE TABLE users (
    id       INT          NOT NULL AUTO_INCREMENT,
    email    VARCHAR(120) NOT NULL UNIQUE,
    username VARCHAR(50)  NOT NULL UNIQUE,
    PRIMARY KEY (id)
);
"""

MULTI_TABLE_DDL = """
CREATE TABLE categories (id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(80) NOT NULL UNIQUE);
CREATE TABLE products (
    id          INT            NOT NULL AUTO_INCREMENT PRIMARY KEY,
    category_id INT            NOT NULL,
    name        VARCHAR(200)   NOT NULL,
    price       DECIMAL(10,2)  NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
"""


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30.0) as c:
        yield c


# ── /api/health ───────────────────────────────────────────────────────────────

def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


# ── POST /api/parse ───────────────────────────────────────────────────────────

class TestParseEndpoint:
    def test_parse_simple_ddl_200(self, client):
        resp = client.post("/api/parse", json={"source": SIMPLE_DDL, "type": "ddl"})
        assert resp.status_code == 200

    def test_parse_returns_schema_id(self, client):
        resp = client.post("/api/parse", json={"source": SIMPLE_DDL, "type": "ddl"})
        assert "schema_id" in resp.json()
        assert resp.json()["schema_id"]  # non-empty

    def test_parse_returns_tables(self, client):
        resp = client.post("/api/parse", json={"source": SIMPLE_DDL, "type": "ddl"})
        assert len(resp.json()["tables"]) == 1
        assert resp.json()["tables"][0]["name"] == "users"

    def test_parse_returns_generation_order(self, client):
        resp = client.post("/api/parse", json={"source": MULTI_TABLE_DDL, "type": "ddl"})
        order = [t["name"] for t in resp.json()["generation_order"]]
        assert order.index("categories") < order.index("products")

    def test_parse_invalid_ddl_422(self, client):
        resp = client.post("/api/parse", json={"source": "GARBAGE @@", "type": "ddl"})
        assert resp.status_code == 422

    def test_parse_empty_source_422(self, client):
        resp = client.post("/api/parse", json={"source": "", "type": "ddl"})
        assert resp.status_code == 422

    def test_parse_missing_type_422(self, client):
        resp = client.post("/api/parse", json={"source": SIMPLE_DDL})
        assert resp.status_code == 422


# ── POST /api/generate ────────────────────────────────────────────────────────

class TestGenerateEndpoint:
    @pytest.fixture
    def schema_id(self, client):
        resp = client.post("/api/parse", json={"source": SIMPLE_DDL, "type": "ddl"})
        return resp.json()["schema_id"]

    @pytest.fixture
    def multi_schema_id(self, client):
        resp = client.post("/api/parse", json={"source": MULTI_TABLE_DDL, "type": "ddl"})
        return resp.json()["schema_id"]

    def test_generate_returns_200(self, client, schema_id):
        resp = client.post(
            "/api/generate",
            json={"schema_id": schema_id, "row_counts": {"users": 10}},
        )
        assert resp.status_code == 200

    def test_generated_count_matches_request(self, client, schema_id):
        resp = client.post(
            "/api/generate",
            json={"schema_id": schema_id, "row_counts": {"users": 25}},
        )
        assert resp.json()["tables"]["users"]["generated"] == 25

    def test_response_contains_ai_used_flag(self, client, schema_id):
        resp = client.post(
            "/api/generate",
            json={"schema_id": schema_id, "row_counts": {"users": 5}, "ai_enabled": False},
        )
        assert "ai_used" in resp.json()
        assert resp.json()["ai_used"] is False

    def test_multi_table_fk_respected(self, client, multi_schema_id):
        resp = client.post(
            "/api/generate",
            json={"schema_id": multi_schema_id, "row_counts": {"categories": 5, "products": 20}},
        )
        assert resp.status_code == 200
        # 验证 FK 约束（通过 SQL Explorer）
        sql_resp = client.post("/api/db/sql", json={"sql": """
            SELECT COUNT(*) AS cnt FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE c.id IS NULL
        """})
        assert sql_resp.json()["rows"][0]["cnt"] == 0

    def test_unknown_schema_id_404(self, client):
        resp = client.post(
            "/api/generate",
            json={"schema_id": "no-such-id", "row_counts": {"users": 5}},
        )
        assert resp.status_code == 404

    def test_zero_row_count_skips_table(self, client, schema_id):
        resp = client.post(
            "/api/generate",
            json={"schema_id": schema_id, "row_counts": {"users": 0}},
        )
        assert resp.json()["tables"]["users"]["generated"] == 0


# ── GET /api/db/tables ────────────────────────────────────────────────────────

class TestDBTablesEndpoint:
    def test_tables_endpoint_after_parse(self, client):
        client.post("/api/parse", json={"source": SIMPLE_DDL, "type": "ddl"})
        resp = client.get("/api/db/tables")
        assert resp.status_code == 200
        names = {t["name"] for t in resp.json()["tables"]}
        assert "users" in names

    def test_tables_have_column_info(self, client):
        client.post("/api/parse", json={"source": SIMPLE_DDL, "type": "ddl"})
        resp = client.get("/api/db/tables")
        users = next(t for t in resp.json()["tables"] if t["name"] == "users")
        col_names = {c["name"] for c in users["columns"]}
        assert {"id", "email", "username"}.issubset(col_names)
