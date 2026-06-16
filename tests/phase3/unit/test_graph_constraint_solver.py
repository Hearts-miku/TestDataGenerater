"""
Phase 3 · 单元测试 — 图约束解决器
覆盖任务：P3-B2（节点/关系拓扑顺序 + 自引用处理）
"""

import pytest
from app.generator.graph_constraint import GraphConstraintSolver
from app.core.schema_model import (
    GraphSchemaModel, NodeDef, RelDef, PropertyDef
)


def node(label: str, props: list[str] | None = None) -> NodeDef:
    return NodeDef(
        label=label,
        properties=[PropertyDef(name=p, type_category="string") for p in (props or ["id"])],
        unique_properties=["id"],
    )


def rel(type_: str, from_: str, to_: str) -> RelDef:
    return RelDef(type=type_, from_label=from_, to_label=to_, properties=[])


class TestGraphGenerationOrder:
    def test_all_nodes_before_all_rels(self):
        schema = GraphSchemaModel(
            nodes=[node("A"), node("B")],
            relationships=[rel("CONNECTS", "A", "B")],
        )
        solver = GraphConstraintSolver(schema)
        order = solver.generation_order()
        node_steps = [s.step for s in order if s.kind == "node"]
        rel_steps  = [s.step for s in order if s.kind == "relationship"]
        assert max(node_steps) < min(rel_steps)

    def test_self_ref_rel_after_its_node(self):
        schema = GraphSchemaModel(
            nodes=[node("Person")],
            relationships=[rel("MANAGES", "Person", "Person")],
        )
        solver = GraphConstraintSolver(schema)
        order = solver.generation_order()
        person_step  = next(s.step for s in order if s.name == "Person")
        manages_step = next(s.step for s in order if s.name == "MANAGES")
        assert person_step < manages_step

    def test_multiple_rels_all_after_nodes(self):
        schema = GraphSchemaModel(
            nodes=[node("User"), node("Post"), node("Tag")],
            relationships=[
                rel("AUTHORED", "User", "Post"),
                rel("TAGGED_WITH", "Post", "Tag"),
                rel("FOLLOWS", "User", "User"),
            ],
        )
        solver = GraphConstraintSolver(schema)
        order = solver.generation_order()
        node_steps = [s.step for s in order if s.kind == "node"]
        rel_steps  = [s.step for s in order if s.kind == "relationship"]
        assert node_steps and rel_steps
        assert max(node_steps) < min(rel_steps)


class TestNodeIDPool:
    def test_register_and_sample(self):
        solver = GraphConstraintSolver(GraphSchemaModel(nodes=[], relationships=[]))
        solver.register_node_ids("User", [1, 2, 3, 4, 5])
        sample = solver.sample_node_ids("User", n=3)
        assert len(sample) == 3
        assert all(v in {1, 2, 3, 4, 5} for v in sample)

    def test_sample_from_empty_raises(self):
        solver = GraphConstraintSolver(GraphSchemaModel(nodes=[], relationships=[]))
        with pytest.raises(ValueError, match="no nodes"):
            solver.sample_node_ids("Ghost", n=1)

    def test_sample_allows_repetition_for_self_ref(self):
        solver = GraphConstraintSolver(GraphSchemaModel(nodes=[], relationships=[]))
        solver.register_node_ids("Person", [1, 2, 3])
        # 自引用：from 和 to 都从同一个池采样，允许不同的 id（不同节点间关系）
        froms = solver.sample_node_ids("Person", n=5)
        tos   = solver.sample_node_ids("Person", n=5)
        assert len(froms) == 5 and len(tos) == 5


class TestUniquenessInGraph:
    def test_unique_property_dedup(self):
        solver = GraphConstraintSolver(GraphSchemaModel(nodes=[], relationships=[]))
        batch = [
            {"id": 1, "name": "Alice"},
            {"id": 1, "name": "Duplicate"},  # 重复 id
            {"id": 2, "name": "Bob"},
        ]
        result = solver.deduplicate_nodes(batch, unique_props=["id"])
        ids = [r["id"] for r in result]
        assert len(ids) == len(set(ids))

    def test_duplicate_relationship_dedup(self):
        solver = GraphConstraintSolver(GraphSchemaModel(nodes=[], relationships=[]))
        rels = [
            {"from_id": 1, "to_id": 2},
            {"from_id": 1, "to_id": 2},  # 重复
            {"from_id": 1, "to_id": 3},
        ]
        result = solver.deduplicate_rels(rels, unique_on=["from_id", "to_id"])
        assert len(result) == 2
