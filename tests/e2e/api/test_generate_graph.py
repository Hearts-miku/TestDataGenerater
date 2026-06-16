"""
E2E：图数据生成
验证 Cypher Schema → 节点/关系生成 → Kuzu 内容符合约束。
"""

import pytest
from conftest import parse_cypher, generate, cypher_query


class TestSocialNetworkGeneration:
    @pytest.fixture(autouse=True)
    def _generate(self, client, cypher_social):
        schema = parse_cypher(client, cypher_social)
        self.schema_id = schema["schema_id"]
        generate(client, self.schema_id, row_counts={
            "User": 50,
            "Post": 100,
            "Tag":  20,
            "FOLLOWS":     80,
            "AUTHORED":    100,
            "LIKED":       150,
            "TAGGED_WITH": 60,
        })

    def test_node_counts_correct(self, client):
        for label, expected in [("User", 50), ("Post", 100), ("Tag", 20)]:
            row = cypher_query(client, f"MATCH (n:{label}) RETURN count(n) AS cnt")["rows"][0]
            assert row["cnt"] == expected, f"{label}: expected {expected}"

    def test_relationship_counts_correct(self, client):
        for rel, expected in [
            ("FOLLOWS", 80), ("AUTHORED", 100), ("LIKED", 150), ("TAGGED_WITH", 60)
        ]:
            row = cypher_query(
                client, f"MATCH ()-[r:{rel}]->() RETURN count(r) AS cnt"
            )["rows"][0]
            assert row["cnt"] == expected

    def test_authored_endpoints_valid(self, client):
        """所有 AUTHORED 关系必须从 User 出发指向 Post。"""
        invalid = cypher_query(client, """
            MATCH (a)-[:AUTHORED]->(b)
            WHERE NOT (a:User AND b:Post)
            RETURN count(*) AS cnt
        """)["rows"][0]["cnt"]
        assert invalid == 0

    def test_user_unique_ids(self, client):
        total  = cypher_query(client, "MATCH (u:User) RETURN count(u) AS cnt")["rows"][0]["cnt"]
        unique = cypher_query(
            client, "MATCH (u:User) RETURN count(DISTINCT u.id) AS cnt"
        )["rows"][0]["cnt"]
        assert total == unique

    def test_tag_unique_names(self, client):
        total  = cypher_query(client, "MATCH (t:Tag) RETURN count(t) AS cnt")["rows"][0]["cnt"]
        unique = cypher_query(
            client, "MATCH (t:Tag) RETURN count(DISTINCT t.name) AS cnt"
        )["rows"][0]["cnt"]
        assert total == unique

    def test_follows_both_endpoints_are_users(self, client):
        invalid = cypher_query(client, """
            MATCH (a)-[:FOLLOWS]->(b)
            WHERE NOT (a:User AND b:User)
            RETURN count(*) AS cnt
        """)["rows"][0]["cnt"]
        assert invalid == 0


class TestKnowledgeGraphGeneration:
    @pytest.fixture(autouse=True)
    def _generate(self, client, cypher_knowledge):
        schema = parse_cypher(client, cypher_knowledge)
        self.schema_id = schema["schema_id"]
        generate(client, self.schema_id, row_counts={
            "Company":  15,
            "Person":   40,
            "Product":  30,
            "Location": 10,
            "WORKS_AT":       35,
            "LOCATED_IN":     15,
            "PRODUCES":       25,
            "MANAGES":        20,
            "PARTNERS_WITH":  8,
        })

    def test_self_referencing_manages_valid(self, client):
        """MANAGES 的两端必须都是 Person。"""
        invalid = cypher_query(client, """
            MATCH (a)-[:MANAGES]->(b)
            WHERE NOT (a:Person AND b:Person)
            RETURN count(*) AS cnt
        """)["rows"][0]["cnt"]
        assert invalid == 0

    def test_works_at_endpoints(self, client):
        invalid = cypher_query(client, """
            MATCH (p)-[:WORKS_AT]->(c)
            WHERE NOT (p:Person AND c:Company)
            RETURN count(*) AS cnt
        """)["rows"][0]["cnt"]
        assert invalid == 0

    def test_located_in_endpoints(self, client):
        invalid = cypher_query(client, """
            MATCH (c)-[:LOCATED_IN]->(l)
            WHERE NOT (c:Company AND l:Location)
            RETURN count(*) AS cnt
        """)["rows"][0]["cnt"]
        assert invalid == 0

    def test_works_at_has_required_properties(self, client):
        """WORKS_AT 关系必须包含 start_date 和 position 属性。"""
        missing = cypher_query(client, """
            MATCH ()-[r:WORKS_AT]->()
            WHERE r.start_date IS NULL OR r.position IS NULL
            RETURN count(r) AS cnt
        """)["rows"][0]["cnt"]
        assert missing == 0


class TestGraphGenerationEdgeCases:
    def test_no_relationships_generated_without_nodes(self, client, cypher_social):
        """只生成节点时，关系数量应为 0。"""
        schema = parse_cypher(client, cypher_social)
        generate(client, schema["schema_id"], row_counts={
            "User": 10, "Post": 0, "Tag": 0,
            "FOLLOWS": 5, "AUTHORED": 0, "LIKED": 0, "TAGGED_WITH": 0,
        })
        authored_cnt = cypher_query(
            client, "MATCH ()-[:AUTHORED]->() RETURN count(*) AS cnt"
        )["rows"][0]["cnt"]
        assert authored_cnt == 0

    def test_zero_row_count_skips_label(self, client, cypher_social):
        schema = parse_cypher(client, cypher_social)
        generate(client, schema["schema_id"], row_counts={
            "User": 0, "Post": 0, "Tag": 0,
        })
        user_cnt = cypher_query(
            client, "MATCH (u:User) RETURN count(u) AS cnt"
        )["rows"][0]["cnt"]
        assert user_cnt == 0
