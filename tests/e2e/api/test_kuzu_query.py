"""
E2E：Kuzu Cypher Explorer API
验证 POST /api/graph/cypher、GET /api/graph/schema、GET /api/graph/stats 端点。
"""

import pytest
from conftest import parse_cypher, generate, cypher_query


@pytest.fixture(autouse=True)
def _seed_social(client, cypher_social):
    schema = parse_cypher(client, cypher_social)
    generate(client, schema["schema_id"], row_counts={
        "User": 30, "Post": 60, "Tag": 10,
        "FOLLOWS": 50, "AUTHORED": 60, "LIKED": 80, "TAGGED_WITH": 40,
    })


class TestGraphSchemaEndpoint:
    def test_schema_lists_node_labels(self, client):
        resp = client.get("/api/graph/schema")
        assert resp.status_code == 200
        labels = {n["label"] for n in resp.json()["nodes"]}
        assert {"User", "Post", "Tag"}.issubset(labels)

    def test_schema_lists_relationship_types(self, client):
        resp = client.get("/api/graph/schema")
        rel_types = {r["type"] for r in resp.json()["relationships"]}
        assert {"FOLLOWS", "AUTHORED", "LIKED", "TAGGED_WITH"}.issubset(rel_types)

    def test_schema_includes_property_types(self, client):
        resp = client.get("/api/graph/schema")
        node_map = {n["label"]: n for n in resp.json()["nodes"]}
        user_props = {p["name"]: p["type"] for p in node_map["User"]["properties"]}
        assert "id" in user_props
        assert "email" in user_props


class TestGraphStatsEndpoint:
    def test_node_counts_in_stats(self, client):
        resp = client.get("/api/graph/stats")
        assert resp.status_code == 200
        node_counts = resp.json()["node_counts"]
        assert node_counts.get("User") == 30
        assert node_counts.get("Post") == 60
        assert node_counts.get("Tag") == 10

    def test_relationship_counts_in_stats(self, client):
        resp = client.get("/api/graph/stats")
        rel_counts = resp.json()["relationship_counts"]
        assert rel_counts.get("FOLLOWS") == 50
        assert rel_counts.get("AUTHORED") == 60


class TestCypherQueryExecution:
    def test_basic_match(self, client):
        result = cypher_query(client, "MATCH (u:User) RETURN count(u) AS cnt")
        assert result["rows"][0]["cnt"] == 30

    def test_pattern_match_with_relationship(self, client):
        result = cypher_query(client, """
            MATCH (u:User)-[:AUTHORED]->(p:Post)
            RETURN u.username AS author, count(p) AS post_count
            ORDER BY post_count DESC
            LIMIT 5
        """)
        assert len(result["rows"]) <= 5
        assert all("author" in r and "post_count" in r for r in result["rows"])

    def test_multi_hop_path(self, client):
        """两跳路径：User → Post → Tag"""
        result = cypher_query(client, """
            MATCH (u:User)-[:AUTHORED]->(p:Post)-[:TAGGED_WITH]->(t:Tag)
            RETURN u.username AS author, t.name AS tag, count(p) AS posts
            LIMIT 10
        """)
        assert isinstance(result["rows"], list)

    def test_where_filter(self, client):
        result = cypher_query(client, """
            MATCH (p:Post)
            WHERE p.likes > 0
            RETURN count(p) AS cnt
        """)
        assert result["rows"][0]["cnt"] >= 0

    def test_shortest_path_query(self, client):
        result = cypher_query(client, """
            MATCH p = shortestPath((a:User)-[:FOLLOWS*]-(b:User))
            WHERE a.id <> b.id
            RETURN length(p) AS hops
            LIMIT 1
        """)
        assert isinstance(result["rows"], list)

    def test_empty_result_for_nonexistent_label(self, client):
        result = cypher_query(client, "MATCH (n:NonExistent) RETURN count(n) AS cnt")
        assert result["rows"][0]["cnt"] == 0

    def test_result_includes_column_metadata(self, client):
        result = cypher_query(client, "MATCH (u:User) RETURN u.id AS id, u.email AS email LIMIT 1")
        assert "columns" in result
        col_names = [c["name"] for c in result["columns"]]
        assert "id" in col_names and "email" in col_names


class TestCypherQuerySecurity:
    def test_create_node_blocked(self, client):
        resp = client.post(
            "/api/graph/cypher",
            json={"cypher": "CREATE (n:Injected {id: 999})"},
        )
        assert resp.status_code == 403

    def test_delete_blocked(self, client):
        resp = client.post(
            "/api/graph/cypher",
            json={"cypher": "MATCH (n) DETACH DELETE n"},
        )
        assert resp.status_code == 403

    def test_syntax_error_returns_400(self, client):
        resp = client.post(
            "/api/graph/cypher",
            json={"cypher": "MATCH (n RETURN n"},
        )
        assert resp.status_code == 400
