"""LangGraph pipeline nodes — SchemaContext, RuleInference, BatchGen, Validation."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.pipeline import GraphState
from app.core.schema_model import RelationalSchemaModel

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _schema_summary(schema: RelationalSchemaModel) -> str:
    lines: list[str] = []
    for tbl in schema.tables:
        cols = ", ".join(
            f"{c.name}({c.type_category}{'*' if c.unique else ''}{'!' if not c.nullable else ''})"
            for c in tbl.columns
        )
        lines.append(f"  Table {tbl.name}: [{cols}]")
    return "\n".join(lines)


def _faker_fallback(schema: RelationalSchemaModel, row_counts: dict[str, int]) -> dict[str, list[dict]]:
    """Generate data using the existing rule-based Faker strategy."""
    from app.generator.constraint import ConstraintSolver
    from app.generator.strategies.rule_based import RuleBasedStrategy

    solver = ConstraintSolver(schema)
    strategy = RuleBasedStrategy()
    return strategy.generate(schema, row_counts, solver)


# ── Node 1: SchemaContext ─────────────────────────────────────────────────────

class SchemaContextNode:
    """Ask LLM to identify the domain context from schema structure."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    def run(self, state: GraphState) -> dict:
        schema = state["schema_model"]
        summary = _schema_summary(schema)
        prompt = (
            f"You are a domain expert. Given the following database schema, "
            f"describe in one short phrase (e.g. '用户管理系统', 'e-commerce') "
            f"what business domain this schema represents.\n\n"
            f"Schema:\n{summary}\n\n"
            f"Domain:"
        )
        response = self._llm.invoke(prompt)
        domain_context = response.content.strip()
        return {"domain_context": domain_context}


# ── Node 2: RuleInference ─────────────────────────────────────────────────────

class RuleInferenceNode:
    """Ask LLM to infer best Faker/generation rule tags for each field."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    def run(self, state: GraphState) -> dict:
        schema = state["schema_model"]
        domain = state.get("domain_context", "")
        summary = _schema_summary(schema)

        prompt = (
            f"Domain: {domain}\n"
            f"Schema:\n{summary}\n\n"
            f"For each column, suggest a Faker generation tag. "
            f"Reply with a JSON object where keys are 'table.column' and values are "
            f'objects like {{"tag": "email"}}. '
            f"Available tags: email, user_name, first_name, last_name, phone_number, "
            f"city, address, url, text, sentence, uuid4, random_int, pyfloat, date_of_birth, "
            f"date_time, company, job. "
            f"Reply with JSON only, no markdown."
        )

        try:
            response = self._llm.invoke(prompt)
            raw = response.content.strip()
            rules: dict[str, Any] = json.loads(raw)
            # Normalise: keep only keys that contain a dot
            field_rules = {k: v for k, v in rules.items() if "." in k}
        except Exception:
            logger.debug("RuleInferenceNode: LLM returned invalid JSON — using empty rules")
            field_rules = {}

        return {"field_rules": field_rules}


# ── Node 3: BatchGeneration ───────────────────────────────────────────────────

class BatchGenerationNode:
    """Ask LLM to generate rows per table; falls back to Faker on any error."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    def run(self, state: GraphState) -> dict:
        schema = state["schema_model"]
        row_counts: dict[str, int] = state.get("row_counts", {})
        field_rules: dict[str, Any] = state.get("field_rules", {})
        domain = state.get("domain_context", "")
        tables_by_name = schema.tables_by_name

        generated_batches: dict[str, list[dict]] = {}
        ai_used = False

        for table_name, count in row_counts.items():
            tbl = tables_by_name.get(table_name)
            if tbl is None or count <= 0:
                generated_batches[table_name] = []
                continue

            col_names = [c.name for c in tbl.columns]
            col_desc = ", ".join(
                f"{c.name}({c.type_category})"
                for c in tbl.columns
            )
            rules_for_table = {
                k.split(".", 1)[1]: v
                for k, v in field_rules.items()
                if k.startswith(f"{table_name}.")
            }

            prompt = (
                f"Domain: {domain}\n"
                f"Generate exactly {count} JSON rows for table '{table_name}'.\n"
                f"Columns: {col_desc}\n"
                f"Field hints: {json.dumps(rules_for_table)}\n"
                f"Reply with a JSON array of {count} objects with keys: "
                f"{col_names}. No markdown, just the JSON array."
            )

            try:
                response = self._llm.invoke(prompt)
                raw = response.content.strip()
                rows: list[dict] = json.loads(raw)
                if not isinstance(rows, list):
                    raise ValueError("LLM did not return a list")
                generated_batches[table_name] = rows
                ai_used = True
            except Exception:
                logger.debug("BatchGenerationNode: LLM failed for %s — using Faker", table_name)
                fallback = _faker_fallback(schema, {table_name: count})
                generated_batches[table_name] = fallback.get(table_name, [])

        return {"generated_batches": generated_batches, "ai_used": ai_used}


# ── Node 4: Validation ────────────────────────────────────────────────────────

class ValidationNode:
    """Validate generated batches against schema constraints; increments retry_count on failure."""

    def run(self, state: GraphState) -> dict:
        schema = state["schema_model"]
        batches: dict[str, list[dict]] = state.get("generated_batches", {})
        tables_by_name = schema.tables_by_name
        errors: list[str] = []

        for table_name, rows in batches.items():
            tbl = tables_by_name.get(table_name)
            if tbl is None:
                continue

            for col in tbl.columns:
                values = [row.get(col.name) for row in rows]

                # NOT NULL check
                if not col.nullable:
                    null_positions = [i for i, v in enumerate(values) if v is None]
                    for pos in null_positions:
                        errors.append(
                            f"{table_name}.{col.name}: row {pos} violates NOT NULL constraint"
                        )

                # UNIQUE check
                if col.unique or col.primary_key:
                    non_null = [v for v in values if v is not None]
                    if len(non_null) != len(set(non_null)):
                        errors.append(
                            f"{table_name}.{col.name}: duplicate values violate UNIQUE constraint"
                        )

        retry_count = state.get("retry_count", 0)
        if errors:
            retry_count += 1

        return {"validation_errors": errors, "retry_count": retry_count}
