"""Constraint solver — FK pools, UNIQUE dedup, NOT NULL fill, topological order."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from app.core.schema_model import RelationalSchemaModel, TableDef


class ConstraintSolver:
    def __init__(self, schema: RelationalSchemaModel) -> None:
        self._schema = schema
        # pk_pool[table_name] = list of pk values
        self._pk_pool: dict[str, list[Any]] = defaultdict(list)

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
