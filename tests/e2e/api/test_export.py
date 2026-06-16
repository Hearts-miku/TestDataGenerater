"""
E2E：导出格式验证
验证 POST /api/export 生成的各格式文件内容合法且数据完整。
"""

import csv
import json
import io
import zipfile
import pytest
from conftest import parse_ddl, generate


@pytest.fixture(scope="module")
def seeded_schema(client, ddl_ecommerce):
    """模块级别一次生成，所有导出测试复用。"""
    schema = parse_ddl(client, ddl_ecommerce)
    generate(client, schema["schema_id"], row_counts={
        "categories": 5, "products": 20,
        "users": 10, "orders": 25, "order_items": 60,
    })
    return schema["schema_id"]


class TestSQLExport:
    def test_response_content_type(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "sql"})
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"] or "application/sql" in resp.headers["content-type"]

    def test_contains_insert_statements(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "sql"})
        sql_text = resp.text
        assert "INSERT INTO" in sql_text.upper()

    def test_all_tables_present(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "sql"})
        sql_text = resp.text.upper()
        for table in ("CATEGORIES", "PRODUCTS", "USERS", "ORDERS", "ORDER_ITEMS"):
            assert table in sql_text, f"Missing INSERT for {table}"

    def test_transaction_wrapped(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "sql"})
        sql_text = resp.text.upper()
        assert "BEGIN" in sql_text or "START TRANSACTION" in sql_text
        assert "COMMIT" in sql_text

    def test_row_count_in_output(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "sql"})
        # 粗略验证：users 表 10 行应有 10 条 INSERT INTO users
        insert_count = resp.text.upper().count("INSERT INTO USERS")
        assert insert_count == 10


class TestCSVExport:
    def test_returns_zip_file(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "csv"})
        assert resp.status_code == 200
        assert "zip" in resp.headers["content-type"] or resp.headers.get("content-disposition", "").endswith(".zip")

    def test_zip_contains_all_tables(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "csv"})
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = {n.lower() for n in zf.namelist()}
        for table in ("categories.csv", "products.csv", "users.csv", "orders.csv", "order_items.csv"):
            assert table in names, f"Missing {table} in ZIP"

    def test_csv_parseable_and_row_count(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "csv"})
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            with zf.open("users.csv") as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
                rows = list(reader)
        assert len(rows) == 10
        assert "email" in rows[0]

    def test_csv_headers_match_schema(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "csv"})
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            with zf.open("orders.csv") as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
                headers = set(reader.fieldnames or [])
        assert {"id", "user_id", "status", "total_amount", "created_at"}.issubset(headers)


class TestJSONExport:
    def test_returns_valid_json(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_all_tables_in_json(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "json"})
        data = resp.json()
        for table in ("categories", "products", "users", "orders", "order_items"):
            assert table in data, f"Missing key: {table}"

    def test_row_counts_in_json(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "json"})
        data = resp.json()
        assert len(data["users"]) == 10
        assert len(data["products"]) == 20
        assert len(data["order_items"]) == 60

    def test_json_values_not_none_for_not_null_columns(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "json"})
        data = resp.json()
        for row in data["users"]:
            assert row["email"] is not None
            assert row["username"] is not None


class TestCypherExport:
    @pytest.fixture(scope="class")
    def cypher_schema(self, client, cypher_social):
        from conftest import parse_cypher
        schema = parse_cypher(client, cypher_social)
        generate(client, schema["schema_id"], row_counts={
            "User": 10, "Post": 20, "Tag": 5,
            "FOLLOWS": 15, "AUTHORED": 20, "LIKED": 25, "TAGGED_WITH": 10,
        })
        return schema["schema_id"]

    def test_returns_text_content(self, client, cypher_schema):
        resp = client.post("/api/export", json={"schema_id": cypher_schema, "format": "cypher"})
        assert resp.status_code == 200
        assert resp.text.strip() != ""

    def test_create_node_statements_present(self, client, cypher_schema):
        resp = client.post("/api/export", json={"schema_id": cypher_schema, "format": "cypher"})
        upper = resp.text.upper()
        assert "CREATE (:USER" in upper or "CREATE (n:User" in resp.text

    def test_create_rel_statements_present(self, client, cypher_schema):
        resp = client.post("/api/export", json={"schema_id": cypher_schema, "format": "cypher"})
        assert "MERGE" in resp.text.upper() or "CREATE" in resp.text.upper()

    def test_node_count_in_export(self, client, cypher_schema):
        resp = client.post("/api/export", json={"schema_id": cypher_schema, "format": "cypher"})
        user_creates = resp.text.count(":User")
        assert user_creates >= 10


class TestExcelExport:
    def test_returns_xlsx_content_type(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "xlsx"})
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert "spreadsheetml" in ct or "xlsx" in ct or resp.headers.get("content-disposition", "").endswith(".xlsx")

    def test_xlsx_is_valid_zip(self, client, seeded_schema):
        """xlsx 本质是 ZIP，能解压说明格式合法。"""
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "xlsx"})
        assert zipfile.is_zipfile(io.BytesIO(resp.content))


class TestExportErrors:
    def test_invalid_format_returns_422(self, client, seeded_schema):
        resp = client.post("/api/export", json={"schema_id": seeded_schema, "format": "parquet"})
        assert resp.status_code == 422

    def test_nonexistent_schema_id_returns_404(self, client):
        resp = client.post("/api/export", json={"schema_id": "nonexistent-id-xyz", "format": "json"})
        assert resp.status_code == 404
