"""Constraint solver — FK pools, UNIQUE dedup, NOT NULL fill, topological order.

Beyond classic single-column PK→FK pools, this solver also tracks **shared key
pools** keyed by (table, column). This is what closes joins across Doris/OLAP
tables that have no explicit FOREIGN KEY: a curated set of ``Relation`` edges
(see ``app.core.relation_parser``) tells us that ``child.col`` must reference an
existing ``parent.col`` value. The parent (authority) column registers its
generated values; the child samples from that pool.
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from app.core.schema_model import RelationalSchemaModel, TableDef

if TYPE_CHECKING:
    from app.core.relation_parser import Relation


class ConstraintSolver:
    def __init__(
        self,
        schema: RelationalSchemaModel,
        relations: "list[Relation] | None" = None,
    ) -> None:
        self._schema = schema
        # pk_pool[table_name] = list of pk values (legacy single-table pool)
        self._pk_pool: dict[str, list[Any]] = defaultdict(list)
        # col_pool[(table, column)] = list of generated values for shared-key joins
        self._col_pool: dict[tuple[str, str], list[Any]] = defaultdict(list)

        # Build relation lookups: which child columns reference which authority column.
        # If no relations are given explicitly, derive them from the schema's
        # foreign keys (which include any injected from the curated schema graph).
        if relations is None:
            from app.core.relation_parser import Relation as _Rel
            relations = [
                _Rel(
                    child_table=t.name,
                    child_col=fk.column,
                    parent_table=fk.ref_table,
                    parent_col=fk.ref_column,
                )
                for t in schema.tables
                for fk in t.foreign_keys
            ]
        self._relations: list[Relation] = list(relations)
        raw_target: dict[tuple[str, str], tuple[str, str]] = {}
        for r in self._relations:
            # First relation wins if a child column appears in several edges.
            raw_target.setdefault(
                (r.child_table, r.child_col), (r.parent_table, r.parent_col)
            )

        # Resolve each FK target transitively to its ROOT authority. When
        # cust_no → other.cust_no → ... → C_PT_INDV_CUST_BASIC.party_id, every
        # customer reference ends up sampling from the same root pool, so all
        # joins close instead of fragmenting across intermediate tables.
        self._fk_target: dict[tuple[str, str], tuple[str, str]] = {}
        for child in raw_target:
            self._fk_target[child] = self._resolve_root(child, raw_target)

        self._authority_cols: set[tuple[str, str]] = set(self._fk_target.values())

    @staticmethod
    def _resolve_root(
        child: tuple[str, str],
        raw_target: dict[tuple[str, str], tuple[str, str]],
    ) -> tuple[str, str]:
        """Follow the FK chain to the ultimate authority, guarding against cycles."""
        seen = {child}
        target = raw_target[child]
        while target in raw_target and target not in seen:
            seen.add(target)
            target = raw_target[target]
        return target

    # ── Shared key pools (relation-driven joins) ──────────────────────────────

    def fk_target(self, table: str, column: str) -> tuple[str, str] | None:
        """If (table, column) references an authority column, return (parent_table, parent_col)."""
        return self._fk_target.get((table, column))

    def is_authority(self, table: str, column: str) -> bool:
        """True if (table, column) is referenced by at least one child column."""
        return (table, column) in self._authority_cols

    def register_values(self, table: str, column: str, values: list[Any]) -> None:
        """Record an authority column's generated values for child FK sampling."""
        self._col_pool[(table, column)].extend(v for v in values if v is not None)

    def sample_values(self, table: str, column: str, n: int = 1) -> list[Any]:
        """Sample n values from a (table, column) pool. Returns [None]*n if empty."""
        pool = self._col_pool.get((table, column))
        if not pool:
            return [None] * n
        return [random.choice(pool) for _ in range(n)]

    def pool_size(self, table: str, column: str) -> int:
        return len(self._col_pool.get((table, column), []))

    # ── Topological sort ──────────────────────────────────────────────────────

    def topological_order(self) -> list[str]:
        """Return table names in FK-safe generation order (raises ValueError on circular)."""
        tables_dict = {t.name: t for t in self._schema.tables}
        deps: dict[str, set[str]] = {name: set() for name in tables_dict}
        for name, tbl in tables_dict.items():
            for fk in tbl.foreign_keys:
                if fk.ref_table in tables_dict and fk.ref_table != name:
                    deps[name].add(fk.ref_table)

        in_degree = {n: len(d) for n, d in deps.items()}
        queue = sorted(n for n, d in in_degree.items() if d == 0)
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for name in sorted(tables_dict.keys()):
                if node in deps[name]:
                    deps[name].discard(node)
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(result) != len(tables_dict):
            remaining = set(tables_dict) - set(result)
            raise ValueError(f"circular FK dependency detected: {remaining}")

        return result

    # ── PK / FK pool ─────────────────────────────────────────────────────────

    def register_pk(self, table: str, values: list[Any]) -> None:
        """Add a batch of generated PK values to the pool for FK sampling."""
        self._pk_pool[table].extend(values)

    def sample_fk(self, ref_table: str, n: int = 1) -> list[Any]:
        """Sample n FK values from ref_table's pool. Raises if pool is empty."""
        pool = self._pk_pool.get(ref_table, [])
        if not pool:
            raise ValueError(
                f"FK reference pool for {ref_table!r} has no rows — "
                "generate the referenced table first."
            )
        return [random.choice(pool) for _ in range(n)]

    def pk_pool_size(self, table: str) -> int:
        return len(self._pk_pool.get(table, []))

    # ── UNIQUE / NOT NULL ─────────────────────────────────────────────────────

    def deduplicate(
        self,
        batch: list[dict[str, Any]],
        unique_cols: list[str],
        existing_seen: set | None = None,
    ) -> list[dict[str, Any]]:
        """Remove rows whose unique-column values have already been seen.

        existing_seen may contain either raw values (single-col shortcut)
        or tuples (multi-col key).  We normalise to tuples internally.
        """
        seen_tuples: set = set()
        if existing_seen:
            for v in existing_seen:
                seen_tuples.add(v if isinstance(v, tuple) else (v,))

        result = []
        for row in batch:
            key = tuple(row.get(c) for c in unique_cols)
            if key not in seen_tuples:
                seen_tuples.add(key)
                result.append(row)
        return result

    def fill_not_null(
        self,
        batch: list[dict[str, Any]],
        not_null_cols: list[str],
        fallback: Any = "",
    ) -> list[dict[str, Any]]:
        """Replace None values in not-null columns with fallback."""
        for row in batch:
            for col in not_null_cols:
                if row.get(col) is None:
                    row[col] = fallback
        return batch
