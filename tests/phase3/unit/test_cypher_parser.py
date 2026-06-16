"""
Phase 3 · 单元测试 — Cypher Schema 解析器
覆盖任务：P3-B1（lark-parser 封装层）

测试对象：backend/app/core/cypher_parser.py :: CypherParser
"""

import pytest
from app.core.cypher_parser import CypherParser


@pytest.fixture
def parser():
    return CypherParser()


SOCIAL = """
CREATE CONSTRAINT ON (u:User) ASSERT u.id IS UNIQUE;
CREATE CONSTRAINT ON (p:Post) ASSERT p.id IS UNIQUE;
// (:User {id: INT, username: STRING, email: STRING})
// (:Post {id: INT, content: STRING, likes: INT})
// (:Tag  {id: INT, name: STRING})
// (:User)-[:FOLLOWS {since: DATE}]->(:User)
// (:User)-[:AUTHORED]->(:Post)
// (:Post)-[:TAGGED_WITH]->(:Tag)
"""


class TestNodeExtraction:
    def test_node_labels_extracted(self, parser):
        result = parser.parse(SOCIAL)
        labels = {n.label for n in result.nodes}
        assert "User" in labels and "Post" in labels and "Tag" in labels

    def test_node_properties_extracted(self, parser):
        result = parser.parse(SOCIAL)
        node_map = {n.label: n for n in result.nodes}
        user_props = {p.name for p in node_map["User"].properties}
        assert {"id", "username", "email"}.issubset(user_props)

    def test_property_types_mapped(self, parser):
        result = parser.parse(SOCIAL)
        node_map = {n.label: n for n in result.nodes}
        id_prop = next(p for p in node_map["User"].properties if p.name == "id")
        assert id_prop.type_category == "integer"

    def test_unique_constraint_captured(self, parser):
        result = parser.parse(SOCIAL)
        node_map = {n.label: n for n in result.nodes}
        assert "id" in node_map["User"].unique_properties
        assert "id" in node_map["Post"].unique_properties


class TestRelationshipExtraction:
    def test_relationship_types_extracted(self, parser):
        result = parser.parse(SOCIAL)
        types = {r.type for r in result.relationships}
        assert {"FOLLOWS", "AUTHORED", "TAGGED_WITH"}.issubset(types)

    def test_relationship_endpoints(self, parser):
        result = parser.parse(SOCIAL)
        rel_map = {r.type: r for r in result.relationships}
        assert rel_map["AUTHORED"].from_label == "User"
        assert rel_map["AUTHORED"].to_label == "Post"

    def test_relationship_properties(self, parser):
        result = parser.parse(SOCIAL)
        rel_map = {r.type: r for r in result.relationships}
        follows_props = {p.name for p in rel_map["FOLLOWS"].properties}
        assert "since" in follows_props

    def test_self_referencing_relationship(self, parser):
        cypher = "// (:Person)-[:MANAGES]->(:Person)"
        result = parser.parse(cypher)
        manages = next(r for r in result.relationships if r.type == "MANAGES")
        assert manages.from_label == "Person"
        assert manages.to_label == "Person"


class TestGenerationOrder:
    def test_nodes_before_relationships(self, parser):
        result = parser.parse(SOCIAL)
        node_steps = [s.step for s in result.generation_order if s.kind == "node"]
        rel_steps  = [s.step for s in result.generation_order if s.kind == "relationship"]
        assert max(node_steps) < min(rel_steps)

    def test_all_labels_in_order(self, parser):
        result = parser.parse(SOCIAL)
        labels_in_order = {s.name for s in result.generation_order if s.kind == "node"}
        assert {"User", "Post", "Tag"}.issubset(labels_in_order)


class TestParserErrors:
    def test_malformed_cypher_raises(self, parser):
        with pytest.raises(ValueError):
            parser.parse("(:Broken ->")

    def test_empty_input_raises(self, parser):
        with pytest.raises(ValueError, match="empty"):
            parser.parse("")

    def test_relationship_with_unknown_node_raises(self, parser):
        with pytest.raises(ValueError, match="undefined"):
            parser.parse("// (:Ghost)-[:HAUNTS]->(:House)")
