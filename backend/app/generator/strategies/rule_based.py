"""Rule-based generation strategy.

Combines layers, in priority order, to produce realistic, join-consistent data:

  1. **Relation FK sampling** — if a column references an authority column
     (from the curated schema graph), its value is sampled from the parent's
     already-generated pool, guaranteeing the join closes.
  2. **AI field specs** — optional per-column generation specs inferred by the
     LLM seed pass (``field_specs["table.col"]``).
  3. **Chinese comment semantics** — banking-domain inference from the column's
     COMMENT (see ``semantic_zh``).
  4. **English name / type fallback** — the original Faker rule engine.
"""

from __future__ import annotations

from typing import Any, Optional

from app.core.schema_model import ColumnDef, RelationalSchemaModel, TableDef
from app.generator.constraint import ConstraintSolver
from app.generator.rules import FakerRuleEngine, Rule, _generate_by_rule
from app.generator.semantic_zh import infer_zh_rule


class RuleBasedStrategy:
    def __init__(
        self,
        locale: str = "zh_CN",
        field_specs: Optional[dict[str, dict]] = None,
    ) -> None:
        self._engine = FakerRuleEngine(locale=locale)
        # "table.column" -> AI-inferred spec dict
        self._field_specs = field_specs or {}

    def generate(
        self,
        schema: RelationalSchemaModel,
        row_counts: dict[str, int],
        solver: ConstraintSolver | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        if solver is None:
            solver = ConstraintSolver(schema)

        tables_by_name = schema.tables_by_name

        ordered = [s.name for s in schema.generation_order if s.name in row_counts]
        for t in row_counts:
            if t not in ordered and t in tables_by_name:
                ordered.append(t)

        result: dict[str, list[dict[str, Any]]] = {}

        for table_name in ordered:
            if table_name not in tables_by_name:
                continue
            count = row_counts.get(table_name, 0)
            if count <= 0:
                continue

            tbl = tables_by_name[table_name]
            rows = self._generate_table(tbl, count, solver)
            result[table_name] = rows

            # Register authority-column values so FK children can sample them.
            for col in tbl.columns:
                if solver.is_authority(table_name, col.name):
                    vals = [r[col.name] for r in rows if r.get(col.name) is not None]
                    if vals:
                        solver.register_values(table_name, col.name, vals)
            # Legacy single-table PK pool (kept for backward compat).
            for pk_col in tbl.primary_key:
                pk_vals = [r[pk_col] for r in rows if r.get(pk_col) is not None]
                if pk_vals:
                    solver.register_pk(table_name, pk_vals)

        return result

    # ── per-table generation ──────────────────────────────────────────────────

    def _generate_table(
        self,
        tbl: TableDef,
        count: int,
        solver: ConstraintSolver,
    ) -> list[dict[str, Any]]:
        engine = self._engine

        # Resolve a Rule per column once.
        col_rules: dict[str, Rule] = {
            col.name: self._resolve_rule(tbl.name, col) for col in tbl.columns
        }
        # Columns whose values must be unique within this table.
        unique_cols = {
            col.name
            for col in tbl.columns
            if col.unique or col.primary_key or solver.is_authority(tbl.name, col.name)
        }
        unique_pools: dict[str, set] = {c: set() for c in unique_cols}
        auto_counters: dict[str, int] = {
            col.name: 1 for col in tbl.columns if col.auto_increment
        }

        rows: list[dict[str, Any]] = []
        for _ in range(count):
            row: dict[str, Any] = {}
            for col in tbl.columns:
                name = col.name

                # 1) auto-increment
                if name in auto_counters:
                    row[name] = auto_counters[name]
                    auto_counters[name] += 1
                    continue

                # 2) relation FK → sample from parent authority pool
                target = solver.fk_target(tbl.name, name)
                if target is not None and solver.pool_size(*target) > 0:
                    row[name] = solver.sample_values(*target, n=1)[0]
                    continue

                # 3) generate by resolved rule
                rule = col_rules[name]
                val = engine.generate(rule)

                # uniqueness enforcement
                if name in unique_cols:
                    pool = unique_pools[name]
                    attempts = 0
                    while (val is None or val in pool) and attempts < 500:
                        val = engine.generate(rule)
                        attempts += 1
                    if val is not None:
                        pool.add(val)

                # NOT NULL fallback
                if not col.nullable and val is None:
                    val = _not_null_fallback(col, engine, rule)

                row[name] = val
            rows.append(row)

        return rows

    # ── rule resolution ─────────────────────────────────────────────────────────

    def _resolve_rule(self, table_name: str, col: ColumnDef) -> Rule:
        """Pick the best Rule for a column, then propagate column constraints."""
        rule: Optional[Rule] = None

        # 1) AI field spec
        spec = self._field_specs.get(f"{table_name}.{col.name}")
        if spec:
            rule = _spec_to_rule(spec)

        # 2) Chinese comment semantics
        if rule is None:
            rule = infer_zh_rule(col)

        # 3) English name / type fallback
        if rule is None:
            rule = self._engine.infer_rule(col.name, col.type_category)

        # Type-compatibility guard: a semantic/AI rule must not produce a value
        # that cannot be inserted into the column's SQL type. Numeric columns
        # must get numeric values; date/datetime columns must get temporal values.
        rule = _enforce_type(rule, col)

        # Propagate column-level constraints.
        rule.nullable = col.nullable
        rule.null_rate = 0.05 if col.nullable else 0.0
        if col.enum_values and rule.tag == "enum":
            rule.enum_values = col.enum_values
        if col.length and rule.tag == "pystr":
            rule.max_chars = col.length
        if rule.tag in ("decimal", "price", "cn_money"):
            if col.precision is not None:
                rule.precision = col.precision
            if col.scale is not None:
                rule.scale = col.scale
            elif rule.scale is None:
                rule.scale = 2
        return rule


# Tags whose generated value is numeric (safe for integer/float/decimal columns).
_NUMERIC_TAGS = {
    "random_int", "decimal", "price", "cn_money", "cn_rate", "cn_date_int",
    "pyfloat", "latitude", "longitude", "num_range",
}
# Tags whose generated value is a date/datetime (safe for date/datetime columns).
_TEMPORAL_TAGS = {"date_of_birth", "datetime", "date_range"}


def _enforce_type(rule: Rule, col: ColumnDef) -> Rule:
    """Ensure the rule produces a value compatible with the column's SQL type.

    A value_pool/pattern is assumed string-like. If the column is numeric or
    temporal and the rule would yield an incompatible value, replace it with a
    sensible type-driven default.
    """
    cat = col.type_category
    produces_numeric = (
        rule.tag in _NUMERIC_TAGS and not rule.value_pool and not rule.pattern
    )
    produces_temporal = (
        rule.tag in _TEMPORAL_TAGS and not rule.value_pool and not rule.pattern
    )

    if cat in ("integer", "float", "decimal"):
        if not produces_numeric:
            if cat == "integer":
                return Rule(tag="random_int", min_val=0, max_val=9_999_999)
            return Rule(tag="cn_money", scale=col.scale if col.scale is not None else 2)
    elif cat in ("date", "datetime"):
        if not produces_temporal:
            return Rule(tag="datetime" if cat == "datetime" else "date_of_birth")
    return rule


def _spec_to_rule(spec: dict) -> Rule:
    """Convert an AI-inferred or user-defined generation spec into a Rule."""
    kind = spec.get("kind", "faker")
    if kind == "pool" and spec.get("pool"):
        return Rule(tag="cn_word", value_pool=list(spec["pool"]))
    if kind == "enum" and spec.get("enum"):
        return Rule(tag="enum", enum_values=[str(v) for v in spec["enum"]])
    if kind == "pattern" and spec.get("pattern"):
        return Rule(tag=None, pattern=str(spec["pattern"]), prefix=str(spec.get("prefix", "")))  # type: ignore[arg-type]
    if kind == "int_range":
        return Rule(tag="num_range", min_val=spec.get("min"), max_val=spec.get("max"), scale=0)
    if kind == "decimal_range":
        return Rule(
            tag="num_range",
            min_val=spec.get("min"),
            max_val=spec.get("max"),
            scale=int(spec.get("decimals", 2)),
        )
    if kind == "date_range":
        return Rule(tag="date_range", date_start=spec.get("start"), date_end=spec.get("end"))
    if kind == "faker" and spec.get("faker"):
        return Rule(tag=str(spec["faker"]))
    return Rule(tag="cn_word")


def _not_null_fallback(col: ColumnDef, engine: FakerRuleEngine, rule: Rule) -> Any:
    """Produce a non-null value for a NOT NULL column whose rule returned None."""
    forced = Rule(
        tag=rule.tag, nullable=False, null_rate=0.0,
        enum_values=rule.enum_values, precision=rule.precision,
        scale=rule.scale, max_chars=rule.max_chars,
        value_pool=rule.value_pool, pattern=rule.pattern, prefix=rule.prefix,
    )
    val = _generate_by_rule(engine._faker, forced)
    if val is not None:
        return val
    match col.type_category:
        case "integer":           return 0
        case "float" | "decimal": return 0.0
        case "boolean":           return False
        case "date":              return "2000-01-01"
        case "datetime":          return "2000-01-01 00:00:00"
        case _:                   return "N/A"
