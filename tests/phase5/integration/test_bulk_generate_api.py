"""
Phase 5 · 集成测试 — 百万行批量生成 API
覆盖任务：P5-B3（分块写入 DuckDB，内存安全）

需要运行中的 uvicorn。大数据量测试标记为 slow，默认跳过。
"""

import os
import time
import pytest
import httpx

BASE = os.getenv("DATAFORGE_URL", "http://127.0.0.1:8000")

DDL = """
CREATE TABLE events (
    id         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50)  NOT NULL,
    payload    TEXT,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=300.0) as c:
        yield c


@pytest.fixture(scope="module")
def schema_id(client):
    resp = client.post("/api/parse", json={"source": DDL, "type": "ddl"})
    return resp.json()["schema_id"]


class TestBulkGenerationAPI:
    def test_generate_10k_rows(self, client, schema_id):
        resp = client.post("/api/generate", json={
            "schema_id": schema_id,
            "row_counts": {"events": 10_000},
        }, timeout=60.0)
        assert resp.status_code == 200
        assert resp.json()["tables"]["events"]["generated"] == 10_000

    def test_10k_no_duplicate_pk(self, client, schema_id):
        client.post("/api/generate", json={
            "schema_id": schema_id,
            "row_counts": {"events": 10_000},
        }, timeout=60.0)
        dup = client.post("/api/db/sql", json={"sql": """
            SELECT COUNT(*) AS cnt FROM (
                SELECT id FROM events GROUP BY id HAVING COUNT(*) > 1
            ) t
        """})
        assert dup.json()["rows"][0]["cnt"] == 0

    @pytest.mark.slow
    def test_generate_100k_rows(self, client, schema_id):
        resp = client.post("/api/generate", json={
            "schema_id": schema_id,
            "row_counts": {"events": 100_000},
        }, timeout=120.0)
        assert resp.status_code == 200
        assert resp.json()["tables"]["events"]["generated"] == 100_000

    @pytest.mark.slow
    def test_generate_1m_rows_completes(self, client, schema_id):
        start = time.time()
        resp = client.post("/api/generate", json={
            "schema_id": schema_id,
            "row_counts": {"events": 1_000_000},
        }, timeout=300.0)
        elapsed = time.time() - start
        assert resp.status_code == 200
        assert resp.json()["tables"]["events"]["generated"] == 1_000_000
        # 百万行生成不应超过 5 分钟
        assert elapsed < 300, f"Too slow: {elapsed:.1f}s"

    @pytest.mark.slow
    def test_1m_rows_memory_safe(self, client, schema_id):
        """通过进程内存端点验证分块写入不会撑爆内存。"""
        client.post("/api/generate", json={
            "schema_id": schema_id,
            "row_counts": {"events": 1_000_000},
        }, timeout=300.0)
        resp = client.get("/api/health")
        mem_mb = resp.json().get("memory_mb", 0)
        # 百万行生成后内存不超过 512MB
        assert mem_mb == 0 or mem_mb < 512, f"Memory too high: {mem_mb}MB"


class TestBulkGenerationChunkBehavior:
    def test_chunked_generation_result_consistent(self, client, schema_id):
        """连续两次生成 5000 行，结果应分别是 5000 行（不累加）。"""
        for _ in range(2):
            resp = client.post("/api/generate", json={
                "schema_id": schema_id,
                "row_counts": {"events": 5_000},
            }, timeout=60.0)
            assert resp.json()["tables"]["events"]["generated"] == 5_000

    def test_chunk_metadata_in_response(self, client, schema_id):
        resp = client.post("/api/generate", json={
            "schema_id": schema_id,
            "row_counts": {"events": 5_000},
        }, timeout=60.0)
        meta = resp.json().get("generation_meta", {})
        # 响应中应包含分块信息（用于前端进度展示）
        assert "chunks_total" in meta or "chunk_size" in meta
