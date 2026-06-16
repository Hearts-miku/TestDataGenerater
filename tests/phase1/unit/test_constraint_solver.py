"""
Phase 1 · 单元测试 — 约束解决器 & 拓扑排序
覆盖任务：P1-B3（拓扑排序）+ P1-B5（PK池、FK采样、UNIQUE去重）

测试对象：backend/app/generator/constraint.py :: ConstraintSolver
"""

import pytest
from app.generator.constraint import ConstraintSolver
from app.core.schema_model import (
    RelationalSchemaModel, TableDef, ColumnDef, ForeignKeyDef
)


def make_table(name: str, cols: list[ColumnDef], fks: list[ForeignKeyDef] | None = None) -> TableDef:
    return TableDef(name=name, columns=cols, foreign_keys=fks or [])


# ── 拓扑排序 ──────────────────────────────────────────────────────────────────

class TestTopologicalSort:
    def test_independent_tables_any_order(self):
        tables = [
            make_table("a", [ColumnDef(name="id", type_category="integer", primary_key=True)]),
            make_table("b", [ColumnDef(name="id", type_category="integer", primary_key=True)]),
        ]
        solver = ConstraintSolver(RelationalSchemaModel(tables=tables))
        order = solver.topological_order()
        assert set(order) == {"a", "b"}

    def test_single_fk_dependency(self):
        parent = make_table("parent", [ColumnDef(name="id", type_category="integer", primary_key=True)])
        child = make_table(
            "child",
            [ColumnDef(name="id", type_category="integer", primary_key=True),
             ColumnDef(name="parent_id", type_category="integer")],
            [ForeignKeyDef(column="parent_id", ref_table="parent", ref_column="id")],
        )
        solver = ConstraintSolver(RelationalSchemaModel(tables=[child, parent]))
        order = solver.topological_order()
        assert order.index("parent") < order.index("child")

    def test_chain_dependency(self):
        a = make_table("a", [ColumnDef(name="id", type_category="integer", primary_key=True)])
        b = make_table(
            "b",
            [ColumnDef(name="id", type_category="integer", primary_key=True),
             ColumnDef(name="a_id", type_category="integer")],
            [ForeignKeyDef(column="a_id", ref_table="a", ref_column="id")],
        )
        c = make_table(
            "c",
            [ColumnDef(name="id", type_category="integer", primary_key=True),
             ColumnDef(name="b_id", type_category="integer")],
            [ForeignKeyDef(column="b_id", ref_table="b", ref_column="id")],
        )
        solver = ConstraintSolver(RelationalSchemaModel(tables=[c, a, b]))
        order = solver.topological_order()
        assert order.index("a") < order.index("b") < order.index("c")

    def test_diamond_dependency(self):
        a = make_table("a", [ColumnDef(name="id", type_category="integer", primary_key=True)])
        b = make_table("b",
            [ColumnDef(name="id", type_category="integer", primary_key=True),
             ColumnDef(name="a_id", type_category="integer")],
            [ForeignKeyDef(column="a_id", ref_table="a", ref_column="id")])
        c = make_table("c",
            [ColumnDef(name="id", type_category="integer", primary_key=True),
             ColumnDef(name="a_id", type_category="integer")],
            [ForeignKeyDef(column="a_id", ref_table="a", ref_column="id")])
        d = make_table("d",
            [ColumnDef(name="id", type_category="integer", primary_key=True),
             ColumnDef(name="b_id", type_category="integer"),
             ColumnDef(name="c_id", type_category="integer")],
            [ForeignKeyDef(column="b_id", ref_table="b", ref_column="id"),
             ForeignKeyDef(column="c_id", ref_table="c", ref_column="id")])
        solver = ConstraintSolver(RelationalSchemaModel(tables=[d, b, c, a]))
        order = solver.topological_order()
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_circular_fk_raises(self):
        a = make_table("a",
            [ColumnDef(name="id", type_category="integer", primary_key=True),
             ColumnDef(name="b_id", type_category="integer")],
            [ForeignKeyDef(column="b_id", ref_table="b", ref_column="id")])
        b = make_table("b",
            [ColumnDef(name="id", type_category="integer", primary_key=True),
             ColumnDef(name="a_id", type_category="integer")],
            [ForeignKeyDef(column="a_id", ref_table="a", ref_column="id")])
        solver = ConstraintSolver(RelationalSchemaModel(tables=[a, b]))
        with pytest.raises(ValueError, match="circular"):
            solver.topological_order()


# ── PK 池 ─────────────────────────────────────────────────────────────────────

class TestPKPool:
    def test_register_and_sample_pk(self):
        solver = ConstraintSolver(RelationalSchemaModel(tables=[]))
        solver.register_pk("users", [1, 2, 3, 4, 5])
        sampled = solver.sample_fk("users", n=3)
        assert len(sampled) == 3
        assert all(v in {1, 2, 3, 4, 5} for v in sampled)

    def test_sample_fk_from_empty_pool_raises(self):
        solver = ConstraintSolver(RelationalSchemaModel(tables=[]))
        with pytest.raises(ValueError, match="no rows"):
            solver.sample_fk("empty_table", n=1)

    def test_pk_pool_accumulates_across_batches(self):
        solver = ConstraintSolver(RelationalSchemaModel(tables=[]))
        solver.register_pk("t", [1, 2, 3])
        solver.register_pk("t", [4, 5, 6])
        assert solver.pk_pool_size("t") == 6


# ── UNIQUE 去重 ───────────────────────────────────────────────────────────────

class TestUniquenessEnforcement:
    def test_deduplicate_removes_duplicates(self):
        solver = ConstraintSolver(RelationalSchemaModel(tables=[]))
        batch = [
            {"id": 1, "email": "a@a.com"},
            {"id": 2, "email": "a@a.com"},  # 重复 email
            {"id": 3, "email": "b@b.com"},
        ]
        unique_cols = ["email"]
        result = solver.deduplicate(batch, unique_cols, existing_seen=set())
        emails = [r["email"] for r in result]
        assert len(emails) == len(set(emails))

    def test_deduplicate_respects_existing_seen(self):
        solver = ConstraintSolver(RelationalSchemaModel(tables=[]))
        batch = [{"id": 1, "email": "seen@a.com"}]
        result = solver.deduplicate(
            batch, unique_cols=["email"],
            existing_seen={"seen@a.com"},
        )
        assert result == []

    def test_not_null_fills_missing(self):
        solver = ConstraintSolver(RelationalSchemaModel(tables=[]))
        batch = [{"id": 1, "name": None}, {"id": 2, "name": "Alice"}]
        filled = solver.fill_not_null(batch, not_null_cols=["name"], fallback="__DEFAULT__")
        assert filled[0]["name"] == "__DEFAULT__"
        assert filled[1]["name"] == "Alice"
