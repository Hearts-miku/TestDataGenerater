"""GenerateService — runs the generation pipeline and writes to DuckDB or KuzuClient."""

from __future__ import annotations

from typing import Any

from app.core.registry import SchemaRegistry
from app.db.duckdb_client import DuckDBClient
from app.db.kuzu_client import KuzuClient
from app.generator.constraint import ConstraintSolver
from app.generator.strategies.rule_based import RuleBasedStrategy

_CHUNK_SIZE = 10_000


class GenerateService:
    def __init__(self, registry: SchemaRegistry, db: DuckDBClient, graph_db: KuzuClient | None = None) -> None:
        self._registry = registry
        self._db = db
        self._graph_db = graph_db
        self._strategy = RuleBasedStrategy(locale="zh_CN")

    def generate(
        self,
        schema_id: str,
        row_counts: dict[str, int],
        ai_enabled: bool = False,
        llm_config: dict | None = None,
    ) -> dict[str, Any]:
        schema = self._registry.require(schema_id)

        if schema.schema_type == "graph":
            if self._graph_db is None:
                raise RuntimeError("graph_db not configured")
            from app.services.graph_generate_service import GraphGenerateService
            svc = GraphGenerateService(self._registry, self._graph_db)
            return svc.generate(schema_id, row_counts)

        # Ensure DuckDB tables exist, then clear stale data before regenerating
        self._db.create_tables(schema)
        # Truncate in reverse topological order (referenced tables last)
        for step in reversed(schema.generation_order):
            if step.name in row_counts and row_counts[step.name] > 0:
                self._db.truncate_table(step.name)

        # ConstraintSolver derives shared-key relations from the schema's FKs
        # (including any injected from the curated schema graph).
        solver = ConstraintSolver(schema)

        # Optional AI seed pass: one LLM call per table → per-column generation
        # specs that enrich the rule-based layer. Degrades to {} on any failure.
        ai_specs, ai_used = self._maybe_ai_specs(
            schema, list(row_counts), ai_enabled, llm_config
        )
        # User-defined custom rules (from natural language) override AI specs.
        custom_specs = dict(getattr(schema, "field_specs", {}) or {})
        field_specs = {**ai_specs, **custom_specs}
        strategy = (
            RuleBasedStrategy(locale="zh_CN", field_specs=field_specs)
            if field_specs
            else self._strategy
        )

        total = sum(row_counts.values())
        chunks_total = max(1, (total + _CHUNK_SIZE - 1) // _CHUNK_SIZE)

        all_rows = strategy.generate(schema, row_counts, solver)

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
            "ai_used": ai_used,
            "generation_meta": {
                "chunk_size": _CHUNK_SIZE,
                "chunks_total": chunks_total,
                "ai_specs": len(field_specs),
            },
        }

    def _maybe_ai_specs(
        self,
        schema,
        table_names: list[str],
        ai_enabled: bool,
        llm_config: dict | None,
    ) -> tuple[dict[str, dict], bool]:
        """Run the AI seed pass if enabled and configured. Never raises."""
        if not ai_enabled:
            return {}, False
        try:
            from app.ai.llm_config import LLMConfig, build_llm
            from app.ai.seed import infer_domain, infer_field_specs
            from app.config import settings

            cfg_dict = llm_config or {
                "base_url": settings.llm_base_url,
                "api_key": settings.llm_api_key,
                "model": settings.llm_model,
            }
            cfg = LLMConfig.from_dict(cfg_dict)
            llm = build_llm(cfg)
            domain = infer_domain(llm, schema)
            specs = infer_field_specs(llm, schema, table_names, domain)
            return specs, bool(specs)
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "AI seed pass failed; falling back to rule-based generation",
                exc_info=True,
            )
            return {}, False
