"""GenerateService — runs the generation pipeline and writes to DuckDB."""

from __future__ import annotations

from typing import Any

from app.core.registry import SchemaRegistry
from app.db.duckdb_client import DuckDBClient
from app.generator.constraint import ConstraintSolver
from app.generator.strategies.rule_based import RuleBasedStrategy

_CHUNK_SIZE = 10_000


class GenerateService:
    def __init__(self, registry: SchemaRegistry, db: DuckDBClient) -> None:
        self._registry = registry
        self._db = db
        self._strategy = RuleBasedStrategy()

    def generate(
        self,
        schema_id: str,
        row_counts: dict[str, int],
        ai_enabled: bool = False,
    ) -> dict[str, Any]:
        schema = self._registry.require(schema_id)

        # Ensure DuckDB tables exist, then clear stale data before regenerating
        self._db.create_tables(schema)
        # Truncate in reverse topological order (referenced tables last)
        for step in reversed(schema.generation_order):
            if step.name in row_counts and row_counts[step.name] > 0:
                self._db.truncate_table(step.name)

        solver = ConstraintSolver(schema)

        total = sum(row_counts.values())
        chunks_total = max(1, (total + _CHUNK_SIZE - 1) // _CHUNK_SIZE)

        # Phase 1: rule-based only (AI path added in Phase 4)
        all_rows = self._strategy.generate(schema, row_counts, solver)

        tables_meta: dict[str, dict] = {}

        # Ensure every table in row_counts is represented in response
        for table_name, count in row_counts.items():
            if count <= 0:
                tables_meta[table_name] = {"generated": 0}
                continue

            rows = all_rows.get(table_name, [])
            # Chunk-write to DuckDB
            for i in range(0, max(len(rows), 1), _CHUNK_SIZE):
                chunk = rows[i: i + _CHUNK_SIZE]
                if chunk:
                    self._db.insert_rows(table_name, chunk)
            tables_meta[table_name] = {"generated": len(rows)}

        return {
            "schema_id": schema_id,
            "tables": tables_meta,
            "ai_used": False,
            "generation_meta": {
                "chunk_size": _CHUNK_SIZE,
                "chunks_total": chunks_total,
            },
        }
