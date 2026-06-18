"""Infer per-column generation rules from sample data.

Given real/sample rows — as INSERT statements or CSV — this statistically infers
a generation spec per column (the same spec shape produced by the natural-language
translator, see ``rule_based._spec_to_rule``). Data-driven, no LLM required.

Inference per column (first match wins):
  * integers, low cardinality (≤6 distinct)        → enum
  * integers, fixed length ≥11 (card/phone-like)   → pattern of '#'
  * integers                                       → int_range(min, max)
  * decimals                                       → decimal_range(min, max, decimals)
  * dates (YYYY-MM-DD[ HH:MM:SS], YYYY/MM/DD)       → date_range(min, max)
  * text, low cardinality (<distinct than rows)    → enum
  * text, moderate cardinality (≤50 distinct)      → pool (sample values)
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from typing import Any, Optional

import sqlglot
import sqlglot.expressions as exp

from app.core.schema_model import RelationalSchemaModel

_INT_RE = re.compile(r"^-?\d+$")
_NULL_TOKENS = {"", "null", "none", "\\n"}
_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d")


def _clean(values: list[Any]) -> list[str]:
    out: list[str] = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s.lower() in _NULL_TOKENS:
            continue
        out.append(s)
    return out


def _is_int(s: str) -> bool:
    return bool(_INT_RE.match(s))


def _is_float(s: str) -> bool:
    if _is_int(s):
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


def _decimals(s: str) -> int:
    return len(s.split(".", 1)[1]) if "." in s else 0


def _parse_date(s: str) -> Optional[datetime]:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def infer_column_spec(values: list[Any]) -> Optional[dict]:
    """Infer a generation spec from a column's sample values, or None."""
    vals = _clean(values)
    if len(vals) < 2:
        return None
    distinct = set(vals)
    n = len(vals)

    # All integers
    if all(_is_int(s) for s in vals):
        lens = {len(s.lstrip("-")) for s in vals}
        if len(distinct) <= 6 and len(distinct) < n:
            return {"kind": "enum", "enum": sorted(distinct, key=lambda x: int(x))}
        if len(lens) == 1 and next(iter(lens)) >= 11:
            return {"kind": "pattern", "pattern": "#" * next(iter(lens))}
        ints = [int(s) for s in vals]
        return {"kind": "int_range", "min": min(ints), "max": max(ints)}

    # All decimals
    if all(_is_float(s) or _is_int(s) for s in vals) and any(_is_float(s) for s in vals):
        fs = [float(s) for s in vals]
        decimals = max(_decimals(s) for s in vals)
        return {"kind": "decimal_range", "min": min(fs), "max": max(fs), "decimals": decimals}

    # All dates
    parsed = [_parse_date(s) for s in vals]
    if all(d is not None for d in parsed):
        ds = [d for d in parsed if d is not None]
        return {
            "kind": "date_range",
            "start": min(ds).date().isoformat(),
            "end": max(ds).date().isoformat(),
        }

    # Text: low cardinality → enum, moderate → pool
    if len(distinct) <= 12 and len(distinct) < n:
        return {"kind": "enum", "enum": sorted(distinct)}
    if len(distinct) <= 50:
        return {"kind": "pool", "pool": sorted(distinct)[:50]}
    return None


# ── Input parsers ──────────────────────────────────────────────────────────────

def _literal_value(node: Any) -> Any:
    if isinstance(node, exp.Null):
        return None
    if isinstance(node, exp.Literal):
        return node.this
    if isinstance(node, exp.Boolean):
        return node.this
    if isinstance(node, exp.Neg):
        inner = _literal_value(node.this)
        return f"-{inner}" if inner is not None else None
    return node.sql() if hasattr(node, "sql") else str(node)


def parse_insert_sql(sql: str, dialect: str = "mysql") -> dict[str, dict]:
    """Parse INSERT statements → {table: {"columns": [...], "rows": [[...], ...]}}."""
    result: dict[str, dict] = {}
    glot = {"mysql": "mysql", "postgresql": "postgres", "postgres": "postgres"}.get(
        dialect.lower(), "mysql"
    )
    try:
        statements = sqlglot.parse(sql, dialect=glot, error_level=sqlglot.ErrorLevel.IGNORE)
    except Exception:
        statements = []

    for stmt in statements:
        if not isinstance(stmt, exp.Insert):
            continue
        target = stmt.this
        columns: list[str] = []
        if isinstance(target, exp.Schema):
            table = target.this.name
            columns = [c.name for c in target.expressions]
        elif isinstance(target, exp.Table):
            table = target.name
        else:
            continue

        values_expr = stmt.expression
        rows: list[list[Any]] = []
        if isinstance(values_expr, exp.Values):
            for tup in values_expr.expressions:
                cells = tup.expressions if isinstance(tup, exp.Tuple) else [tup]
                rows.append([_literal_value(c) for c in cells])
        if not rows:
            continue

        entry = result.setdefault(table, {"columns": columns, "rows": []})
        if not entry["columns"] and columns:
            entry["columns"] = columns
        entry["rows"].extend(rows)

    return result


def parse_csv(text: str) -> dict:
    """Parse CSV text → {"columns": [...], "rows": [[...], ...]}."""
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if r]
    if len(rows) < 2:
        return {"columns": [], "rows": []}
    header = [h.strip().lstrip("﻿") for h in rows[0]]
    return {"columns": header, "rows": rows[1:]}


# ── Public: schema-aware inference ──────────────────────────────────────────────

def _infer_table(
    schema: RelationalSchemaModel,
    table: str,
    columns: list[str],
    rows: list[list[Any]],
) -> dict[str, dict]:
    tbl = schema.tables_by_name.get(table)
    if tbl is None or not rows:
        return {}
    cols = columns or [c.name for c in tbl.columns]
    specs: dict[str, dict] = {}
    for ci, col in enumerate(cols):
        if tbl.column(col) is None:
            continue
        values = [row[ci] for row in rows if ci < len(row)]
        spec = infer_column_spec(values)
        if spec:
            specs[f"{table}.{col}"] = spec
    return specs


def infer_specs_from_insert(schema: RelationalSchemaModel, sql: str) -> dict[str, dict]:
    parsed = parse_insert_sql(sql, dialect=schema.dialect)
    specs: dict[str, dict] = {}
    for table, data in parsed.items():
        specs.update(_infer_table(schema, table, data["columns"], data["rows"]))
    return specs


def infer_specs_from_csv(
    schema: RelationalSchemaModel, table: str, text: str
) -> dict[str, dict]:
    data = parse_csv(text)
    return _infer_table(schema, table, data["columns"], data["rows"])
