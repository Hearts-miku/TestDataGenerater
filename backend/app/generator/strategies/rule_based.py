"""Rule-based generation strategy — Faker + semantic inference + constraint solving."""

from __future__ import annotations

import random
from typing import Any

from app.core.schema_model import RelationalSchemaModel, TableDef
from app.generator.constraint import ConstraintSolver
from app.generator.rules import FakerRuleEngine, Rule, _generate_by_rule


class RuleBasedStrategy:
    def __init__(self, locale: str = "en_US") -> None:
        self._engine = FakerRuleEngine(locale=locale)

    def generate(
        self,
        schema: RelationalSchemaModel,
        row_counts: dict[str, int],
        solver: ConstraintSolver | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        if solver is None:
            solver = ConstraintSolver(schema)

        tables_by_name = schema.tables_by_name

        # Determine generation order from schema's generation_order
        ordered = [s.name for s in schema.generation_order if s.name in row_counts]
        # Add any table in row_counts but not in the order list
        for t in row_counts:
            if t not in ordered and t in tables_by_name:
                ordered.append(t)

        result: dict[str, list[dict[str, Any]]] = {}
        unique_trackers: dict[str, dict[str, set]] = {}

        for table_name in ordered:
            if table_name not in tables_by_name:
                continue
            count = row_counts.get(table_name, 0)
            if count <= 0:
                continue

            tbl = tables_by_name[table_name]
            unique_trackers[table_name] = {}
            rows = self._generate_table(tbl, count, solver, unique_trackers[table_name])
            result[table_name] = rows

            # Register PKs for FK consumers
            for pk_col in tbl.primary_key:
                pk_values = [r[pk_col] for r in rows if pk_col in r and r[pk_col] is not None]
                if pk_values:
                    solver.register_pk(table_name, pk_values)

        return result

    def _generate_table(
        self,
        tbl: TableDef,
        count: int,
        solver: ConstraintSolver,
        unique_pools: dict[str, set],
    ) -> list[dict[str, Any]]:
        fk_map = {fk.column: fk for fk in tbl.foreign_keys}
        engine = self._engine
        pk_counters: dict[str, int] = {}

        for col in tbl.columns:
            if col.auto_increment:
                pk_counters[col.name] = 1
            if col.unique or col.primary_key:
                unique_pools.setdefault(col.name, set())

        rows: list[dict[str, Any]] = []

        for _ in range(count):
            row: dict[str, Any] = {}
            for col in tbl.columns:
                if col.auto_increment:
                    row[col.name] = pk_counters[col.name]
                    pk_counters[col.name] += 1

                elif col.name in fk_map:
                    fk = fk_map[col.name]
                    pool_size = solver.pk_pool_size(fk.ref_table)
                    if pool_size > 0:
                        row[col.name] = solver.sample_fk(fk.ref_table, n=1)[0]
                    else:
                        row[col.name] = None

                else:
                    rule = engine.infer_rule(col.name, col.type_category)
                    # Propagate column constraints into the rule
                    rule.nullable = col.nullable
                    rule.null_rate = 0.05 if col.nullable else 0.0
                    if col.enum_values and rule.tag == "enum":
                        rule.enum_values = col.enum_values
                    if col.length and rule.tag == "pystr":
                        rule.max_chars = col.length
                    if col.precision and rule.tag in ("decimal", "price"):
                        rule.precision = col.precision
                        rule.scale = col.scale or 2

                    val = engine.generate(rule)

                    # UNIQUE / PRIMARY KEY enforcement
                    if col.unique or col.primary_key:
                        pool = unique_pools.setdefault(col.name, set())
                        attempts = 0
                        while val in pool and attempts < 500:
                            val = engine.generate(rule)
                            attempts += 1
                        if val not in pool:
                            pool.add(val)

                    # NOT NULL fallback
                    if not col.nullable and val is None:
                        rule2 = Rule(tag=rule.tag, nullable=False, null_rate=0.0,
                                     enum_values=rule.enum_values,
                                     precision=rule.precision, scale=rule.scale,
                                     max_chars=rule.max_chars)
                        val = _generate_by_rule(engine._faker, rule2)
                        if val is None:
                            val = _null_fallback(col)

                    row[col.name] = val

            rows.append(row)

        return rows


def _null_fallback(col) -> Any:
    match col.type_category:
        case "integer":   return 0
        case "float":     return 0.0
        case "decimal":   return 0.0
        case "string":    return "N/A"
        case "text":      return ""
        case "boolean":   return False
        case "date":      return "2000-01-01"
        case "datetime":  return "2000-01-01 00:00:00"
        case _:           return ""
