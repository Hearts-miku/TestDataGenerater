"""
E2E 测试公共 fixtures。

所有测试通过 HTTP 请求访问运行中的 DataForge 后端（127.0.0.1:8000），
而非直接调用内部模块，以保证真实的端到端路径。

前置条件：
    cd backend && uv run uvicorn app.main:app --port 8000
    或执行 scripts/start.ps1
"""

import os
import pathlib
import pytest
import httpx

BASE_URL = os.getenv("DATAFORGE_URL", "http://127.0.0.1:8000")
FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def client():
    """复用同一个 httpx 客户端，避免重复握手开销。"""
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def assert_server_running(client):
    """在所有测试开始前检查服务是否可达。"""
    try:
        resp = client.get("/api/health")
        assert resp.status_code == 200, f"Health check failed: {resp.text}"
    except httpx.ConnectError:
        pytest.exit(
            f"DataForge backend not reachable at {BASE_URL}. "
            "Run: cd backend && uv run uvicorn app.main:app --port 8000",
            returncode=1,
        )


# ── DDL 夹具读取 ──────────────────────────────────────────────────────────────

@pytest.fixture
def ddl_simple_users():
    return (FIXTURES / "ddl" / "simple_users.sql").read_text(encoding="utf-8")


@pytest.fixture
def ddl_ecommerce():
    return (FIXTURES / "ddl" / "ecommerce_schema.sql").read_text(encoding="utf-8")


@pytest.fixture
def ddl_all_types():
    return (FIXTURES / "ddl" / "all_types.sql").read_text(encoding="utf-8")


@pytest.fixture
def ddl_postgresql():
    return (FIXTURES / "ddl" / "postgresql_schema.sql").read_text(encoding="utf-8")


# ── Cypher 夹具读取 ───────────────────────────────────────────────────────────

@pytest.fixture
def cypher_social():
    return (FIXTURES / "cypher" / "social_network.cypher").read_text(encoding="utf-8")


@pytest.fixture
def cypher_knowledge():
    return (FIXTURES / "cypher" / "knowledge_graph.cypher").read_text(encoding="utf-8")


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

def parse_ddl(client: httpx.Client, ddl: str, dialect: str = "mysql") -> dict:
    resp = client.post("/api/parse", json={"source": ddl, "type": "ddl", "dialect": dialect})
    assert resp.status_code == 200, resp.text
    return resp.json()


def parse_cypher(client: httpx.Client, cypher: str) -> dict:
    resp = client.post("/api/parse", json={"source": cypher, "type": "cypher"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def generate(client: httpx.Client, schema_id: str, row_counts: dict, ai_enabled: bool = False) -> dict:
    resp = client.post(
        "/api/generate",
        json={"schema_id": schema_id, "row_counts": row_counts, "ai_enabled": ai_enabled},
        timeout=120.0,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def sql_query(client: httpx.Client, sql: str) -> dict:
    resp = client.post("/api/db/sql", json={"sql": sql})
    assert resp.status_code == 200, resp.text
    return resp.json()


def cypher_query(client: httpx.Client, cypher: str) -> dict:
    resp = client.post("/api/graph/cypher", json={"cypher": cypher})
    assert resp.status_code == 200, resp.text
    return resp.json()
