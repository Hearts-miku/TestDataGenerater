"""
Phase 2 · 集成测试 — POST /api/export
覆盖任务：P2-B5（需要运行中的服务 + 已生成数据）
"""

import csv
import io
import json
import zipfile
import os
import pytest
import httpx

BASE = os.getenv("DATAFORGE_URL", "http://127.0.0.1:8000")

DDL = """
CREATE TABLE categories (id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(80) NOT NULL UNIQUE);
CREATE TABLE products (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    name VARCHAR(200) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
"""


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="module")
def schema_id(client):
    resp = client.post("/api/parse", json={"source": DDL, "type": "ddl"})
    sid = resp.json()["schema_id"]
    client.post("/api/generate", json={
        "schema_id": sid,
        "row_counts": {"categories": 5, "products": 20},
    })
    return sid


class TestSQLExportAPI:
    def test_returns_200(self, client, schema_id):
        resp = client.post("/api/export", json={"schema_id": schema_id, "format": "sql"})
        assert resp.status_code == 200

    def test_content_type(self, client, schema_id):
        resp = client.post("/api/export", json={"schema_id": schema_id, "format": "sql"})
        ct = resp.headers.get("content-type", "")
        assert "text" in ct or "sql" in ct

    def test_contains_both_tables(self, client, schema_id):
        resp = client.post("/api/export", json={"schema_id": schema_id, "format": "sql"})
        upper = resp.text.upper()
        assert "CATEGORIES" in upper and "PRODUCTS" in upper

    def test_insert_count_categories(self, client, schema_id):
        resp = client.post("/api/export", json={"schema_id": schema_id, "format": "sql"})
        count = resp.text.upper().count("INSERT INTO CATEGORIES")
        assert count == 5


class TestCSVExportAPI:
    def test_returns_zip(self, client, schema_id):
        resp = client.post("/api/export", json={"schema_id": schema_id, "format": "csv"})
        assert resp.status_code == 200
        assert zipfile.is_zipfile(io.BytesIO(resp.content))

    def test_products_row_count(self, client, schema_id):
        resp = client.post("/api/export", json={"schema_id": schema_id, "format": "csv"})
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            with zf.open("products.csv") as f:
                rows = list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")))
        assert len(rows) == 20


class TestJSONExportAPI:
    def test_valid_json_response(self, client, schema_id):
        resp = client.post("/api/export", json={"schema_id": schema_id, "format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data and "products" in data

    def test_row_counts(self, client, schema_id):
        resp = client.post("/api/export", json={"schema_id": schema_id, "format": "json"})
        data = resp.json()
        assert len(data["categories"]) == 5
        assert len(data["products"]) == 20


class TestExportErrors:
    def test_invalid_format_422(self, client, schema_id):
        resp = client.post("/api/export", json={"schema_id": schema_id, "format": "xml"})
        assert resp.status_code == 422

    def test_nonexistent_schema_404(self, client):
        resp = client.post("/api/export", json={"schema_id": "bad-id", "format": "json"})
        assert resp.status_code == 404


class TestStaticFileServing:
    def test_root_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_assets_reachable(self, client):
        # 获取 index.html，提取第一个 JS 资源路径
        resp = client.get("/")
        import re
        match = re.search(r'src="(/assets/[^"]+\.js)"', resp.text)
        if match:
            asset_resp = client.get(match.group(1))
            assert asset_resp.status_code == 200
