"""
Phase 3 · 集成测试 — Kuzu 客户端
覆盖任务：P3-B3（建图、写入、Cypher 查询）

使用临时目录，测试后清理。
"""

import tempfile
import shutil
import pytest
from app.db.kuzu_client import KuzuClient
from app.core.schema_model import (
    GraphSchemaModel, NodeDef, RelDef, PropertyDef
)


@pytest.fixture
def client():
    tmp = tempfile.mkdtemp()
    c = KuzuClient(tmp)
    yield c
    c.close()
    shutil.rmtree(tmp, ignore_errors=True)


def social_schema() -> GraphSchemaModel:
    return GraphSchemaModel(
        nodes=[
            NodeDef(label="User", properties=[
                PropertyDef(name="id",       type_category="integer"),
                PropertyDef(name="username", type_category="string"),
                PropertyDef(name="email",    type_category="string"),
            ], unique_properties=["id"]),
            NodeDef(label="Post", properties=[
                PropertyDef(name="id",      type_category="integer"),
                PropertyDef(name="content", type_category="string"),
            ], unique_properties=["id"]),
        ],
        relationships=[
            RelDef(type="AUTHORED", from_label="User", to_label="Post", properties=[]),
        ],
    )


class TestGraphCreation:
    def test_create_node_tables(self, client):
        client.create_graph(social_schema())
        schema = client.get_schema()
        labels = {n["label"] for n in schema["nodes"]}
        assert "User" in labels and "Post" in labels

    def test_create_relationship_table(self, client):
        client.create_graph(social_schema())
        schema = client.get_schema()
        rel_types = {r["type"] for r in schema["relationships"]}
        assert "AUTHORED" in rel_types

    def test_idempotent_create(self, client):
        client.create_graph(social_schema())
        client.create_graph(social_schema())  # 不应抛出
        schema = client.get_schema()
        assert len(schema["nodes"]) >= 2

    def test_reset_clears_graph(self, client):
        client.create_graph(social_schema())
        client.reset()
        schema = client.get_schema()
        assert len(schema["nodes"]) == 0


class TestNodeInsertion:
    @pytest.fixture(autouse=True)
    def _setup(self, client):
        client.create_graph(social_schema())

    def test_insert_nodes(self, client):
        client.insert_nodes("User", [
            {"id": 1, "username": "alice", "email": "a@a.com"},
            {"id": 2, "username": "bob",   "email": "b@b.com"},
        ])
        result = client.query("MATCH (u:User) RETURN count(u) AS cnt")
        assert result[0]["cnt"] == 2

    def test_insert_zero_nodes(self, client):
        client.insert_nodes("User", [])
        result = client.query("MATCH (u:User) RETURN count(u) AS cnt")
        assert result[0]["cnt"] == 0

    def test_large_node_batch(self, client):
        rows = [{"id": i, "username": f"u{i}", "email": f"u{i}@x.com"} for i in range(500)]
        client.insert_nodes("User", rows)
        result = client.query("MATCH (u:User) RETURN count(u) AS cnt")
        assert result[0]["cnt"] == 500


class TestRelationshipInsertion:
    @pytest.fixture(autouse=True)
    def _seed(self, client):
        client.create_graph(social_schema())
        client.insert_nodes("User", [
            {"id": 1, "username": "alice", "email": "a@a.com"},
            {"id": 2, "username": "bob",   "email": "b@b.com"},
        ])
        client.insert_nodes("Post", [
            {"id": 10, "content": "Hello"},
            {"id": 11, "content": "World"},
        ])

    def test_insert_relationships(self, client):
        client.insert_rels("AUTHORED", [
            {"from_id": 1, "to_id": 10},
            {"from_id": 2, "to_id": 11},
        ])
        result = client.query("MATCH ()-[r:AUTHORED]->() RETURN count(r) AS cnt")
        assert result[0]["cnt"] == 2

    def test_relationship_endpoints_correct(self, client):
        client.insert_rels("AUTHORED", [{"from_id": 1, "to_id": 10}])
        result = client.query("""
            MATCH (u:User)-[:AUTHORED]->(p:Post)
            WHERE u.id = 1
            RETURN p.id AS pid
        """)
        assert result[0]["pid"] == 10


class TestCypherQuery:
    @pytest.fixture(autouse=True)
    def _seed(self, client):
        client.create_graph(social_schema())
        client.insert_nodes("User", [
            {"id": i, "username": f"u{i}", "email": f"u{i}@x.com"} for i in range(1, 6)
        ])
        client.insert_nodes("Post", [
            {"id": i, "content": f"post {i}"} for i in range(101, 111)
        ])
        client.insert_rels("AUTHORED", [{"from_id": i, "to_id": 100 + i} for i in range(1, 6)])

    def test_count_query(self, client):
        result = client.query("MATCH (u:User) RETURN count(u) AS cnt")
        assert result[0]["cnt"] == 5

    def test_where_filter(self, client):
        result = client.query("MATCH (u:User) WHERE u.id > 3 RETURN count(u) AS cnt")
        assert result[0]["cnt"] == 2

    def test_match_with_relationship(self, client):
        result = client.query("""
            MATCH (u:User)-[:AUTHORED]->(p:Post)
            RETURN u.username AS author, p.id AS post_id
            ORDER BY u.id
        """)
        assert len(result) == 5
        assert result[0]["author"] == "u1"

    def test_write_query_blocked(self, client):
        with pytest.raises(PermissionError):
            client.query("MATCH (n) DETACH DELETE n")

    def test_create_blocked(self, client):
        with pytest.raises(PermissionError):
            client.query("CREATE (n:Injected {id: 999})")

    def test_nonexistent_label_returns_zero(self, client):
        result = client.query("MATCH (n:Ghost) RETURN count(n) AS cnt")
        assert result[0]["cnt"] == 0
