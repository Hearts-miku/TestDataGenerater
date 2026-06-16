"""
E2E：Cypher Schema 解析 API
验证 POST /api/parse 对 Cypher 输入的解析结果。
"""

import pytest
from conftest import parse_cypher


class TestSocialNetworkCypherParsing:
    def test_node_labels_extracted(self, client, cypher_social):
        result = parse_cypher(client, cypher_social)
        labels = {n["label"] for n in result["nodes"]}
        assert labels == {"User", "Post", "Tag"}

    def test_relationship_types_extracted(self, client, cypher_social):
        result = parse_cypher(client, cypher_social)
        rel_types = {r["type"] for r in result["relationships"]}
        assert rel_types == {"FOLLOWS", "AUTHORED", "LIKED", "TAGGED_WITH"}

    def test_relationship_direction_correct(self, client, cypher_social):
        result = parse_cypher(client, cypher_social)
        rel_map = {r["type"]: r for r in result["relationships"]}
        authored = rel_map["AUTHORED"]
        assert authored["from_label"] == "User"
        assert authored["to_label"] == "Post"

    def test_unique_constraints_captured(self, client, cypher_social):
        result = parse_cypher(client, cypher_social)
        node_map = {n["label"]: n for n in result["nodes"]}
        assert "id" in node_map["User"]["unique_properties"]
        assert "name" in node_map["Tag"]["unique_properties"]

    def test_relationship_properties_captured(self, client, cypher_social):
        result = parse_cypher(client, cypher_social)
        rel_map = {r["type"]: r for r in result["relationships"]}
        follows_props = {p["name"] for p in rel_map["FOLLOWS"]["properties"]}
        assert "since" in follows_props


class TestKnowledgeGraphParsing:
    def test_four_node_types(self, client, cypher_knowledge):
        result = parse_cypher(client, cypher_knowledge)
        labels = {n["label"] for n in result["nodes"]}
        assert labels == {"Company", "Person", "Product", "Location"}

    def test_self_referencing_relationship(self, client, cypher_knowledge):
        """(:Person)-[:MANAGES]->(:Person) 自引用必须正确识别。"""
        result = parse_cypher(client, cypher_knowledge)
        rel_map = {r["type"]: r for r in result["relationships"]}
        manages = rel_map["MANAGES"]
        assert manages["from_label"] == "Person"
        assert manages["to_label"] == "Person"

    def test_generation_order_nodes_before_rels(self, client, cypher_knowledge):
        """所有节点生成顺序先于关系。"""
        result = parse_cypher(client, cypher_knowledge)
        node_steps = [s["step"] for s in result["generation_order"] if s["kind"] == "node"]
        rel_steps  = [s["step"] for s in result["generation_order"] if s["kind"] == "relationship"]
        assert max(node_steps) < min(rel_steps)


class TestCypherParseErrors:
    def test_malformed_cypher_returns_422(self, client):
        resp = client.post(
            "/api/parse",
            json={"source": "(:Broken ->", "type": "cypher"},
        )
        assert resp.status_code == 422

    def test_relationship_without_nodes_returns_422(self, client):
        resp = client.post(
            "/api/parse",
            json={"source": "-[:ORPHAN]->", "type": "cypher"},
        )
        assert resp.status_code == 422
