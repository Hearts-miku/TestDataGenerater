"""
Phase 3 · 集成测试 — 图数据 API
覆盖任务：P3-B4 /api/parse(cypher)、P3-B5 /api/generate(graph)、P3-B6 图查询端点

需要运行中的 uvicorn。
"""

import os
import pytest
import httpx

BASE = os.getenv("DATAFORGE_URL", "http://127.0.0.1:8000")

SOCIAL_CYPHER = """
CREATE CONSTRAINT ON (u:User) ASSERT u.id IS UNIQUE;
CREATE CONSTRAINT ON (p:Post) ASSERT p.id IS UNIQUE;
CREATE CONSTRAINT ON (t:Tag)  ASSERT t.name IS UNIQUE;
// (:User {id: INT, username: STRING, email: STRING})
// (:Post {id: INT, content: STRING, likes: INT})
// (:Tag  {id: INT, name: STRING})
// (:User)-[:FOLLOWS {since: DATE}]->(:User)
// (:User)-[:AUTHORED]->(:Post)
// (:Post)-[:TAGGED_WITH]->(:Tag)
"""


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="module")
def schema_id(client):
    resp = client.post("/api/parse", json={"source": SOCIAL_CYPHER, "type": "cypher"})
    assert resp.status_code == 200, resp.text
    sid = resp.json()["schema_id"]
    gen = client.post("/api/generate", json={
        "schema_id": sid,
        "row_counts": {
            "User": 20, "Post": 40, "Tag": 10,
            "FOLLOWS": 30, "AUTHORED": 40, "TAGGED_WITH": 25,
        },
    })
    assert gen.status_code == 200
    return sid


class TestCypherParseAPI:
    def test_parse_cypher_returns_200(self, client):
        resp = client.post("/api/parse", json={"source": SOCIAL_CYPHER, "type": "cypher"})
        assert resp.status_code == 200

    def test_parse_returns_schema_id(self, client):
        resp = client.post("/api/parse", json={"source": SOCIAL_CYPHER, "type": "cypher"})
        assert resp.json().get("schema_id")

    def test_parse_returns_node_labels(self, client):
        resp = client.post("/api/parse", json={"source": SOCIAL_CYPHER, "type": "cypher"})
        labels = {n["label"] for n in resp.json()["nodes"]}
        assert {"User", "Post", "Tag"}.issubset(labels)

    def test_parse_returns_rel_types(self, client):
        resp = client.post("/api/parse", json={"source": SOCIAL_CYPHER, "type": "cypher"})
        types = {r["type"] for r in resp.json()["relationships"]}
        assert {"FOLLOWS", "AUTHORED", "TAGGED_WITH"}.issubset(types)

    def test_parse_nodes_before_rels_in_order(self, client):
        resp = client.post("/api/parse", json={"source": SOCIAL_CYPHER, "type": "cypher"})
        order = resp.json()["generation_order"]
        node_steps = [s["step"] for s in order if s["kind"] == "node"]
        rel_steps  = [s["step"] for s in order if s["kind"] == "relationship"]
        assert max(node_steps) < min(rel_steps)


class TestGraphGenerateAPI:
    def test_generate_returns_200(self, client, schema_id):
        resp = client.post("/api/generate", json={
            "schema_id": schema_id,
            "row_counts": {"User": 5, "Post": 10, "Tag": 3},
        })
        assert resp.status_code == 200

    def test_node_counts_in_response(self, client, schema_id):
        resp = client.post("/api/generate", json={
            "schema_id": schema_id,
            "row_counts": {"User": 10, "Post": 20, "Tag": 5},
        })
        tables = resp.json()["tables"]
        assert tables["User"]["generated"] == 10
        assert tables["Post"]["generated"] == 20

    def test_relationship_counts_in_response(self, client, schema_id):
        resp = client.post("/api/generate", json={
            "schema_id": schema_id,
            "row_counts": {"User": 10, "Post": 20, "Tag": 5, "AUTHORED": 20},
        })
        tables = resp.json()["tables"]
        assert tables["AUTHORED"]["generated"] == 20


class TestGraphQueryAPI:
    def test_schema_endpoint(self, client, schema_id):
        resp = client.get("/api/graph/schema")
        assert resp.status_code == 200
        labels = {n["label"] for n in resp.json()["nodes"]}
        assert "User" in labels

    def test_stats_endpoint(self, client, schema_id):
        resp = client.get("/api/graph/stats")
        assert resp.status_code == 200
        assert "node_counts" in resp.json()

    def test_cypher_match_query(self, client, schema_id):
        resp = client.post("/api/graph/cypher", json={
            "cypher": "MATCH (u:User) RETURN count(u) AS cnt"
        })
        assert resp.status_code == 200
        assert resp.json()["rows"][0]["cnt"] == 20

    def test_pattern_query(self, client, schema_id):
        resp = client.post("/api/graph/cypher", json={
            "cypher": "MATCH (u:User)-[:AUTHORED]->(p:Post) RETURN count(*) AS cnt"
        })
        assert resp.status_code == 200
        assert resp.json()["rows"][0]["cnt"] == 40

    def test_write_cypher_blocked(self, client, schema_id):
        resp = client.post("/api/graph/cypher", json={
            "cypher": "MATCH (n) DETACH DELETE n"
        })
        assert resp.status_code == 403
