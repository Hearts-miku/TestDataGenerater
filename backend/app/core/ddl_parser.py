"""DDL parser — wraps sqlglot, outputs RelationalSchemaModel."""

from __future__ import annotations

import re
from typing import Optional

import sqlglot
import sqlglot.expressions as exp

from app.core.schema_model import (
    ColumnDef,
    ForeignKeyDef,
    GenerationStep,
    RelationalSchemaModel,
    TableDef,
)

_DIALECT_MAP = {
    "mysql":      "mysql",
    "postgresql": "postgres",
    "postgres":   "postgres",
    "sqlite":     "sqlite",
    "bigquery":   "bigquery",
    "tsql":       "tsql",
    "sqlserver":  "tsql",
    "oracle":     "oracle",
}
_SUPPORTED = set(_DIALECT_MAP)


# Doris model-key clause: DUPLICATE/UNIQUE/AGGREGATE KEY(col, ...)
_DORIS_KEY_RE = re.compile(
    r'(?:DUPLICATE|UNIQUE|AGGREGATE)\s+KEY\s*\(([^)]*)\)', re.IGNORECASE
)


def _preprocess_doris(sql: str) -> tuple[str, dict[str, list[str]]]:
    """Strip Apache Doris / StarRocks table options that sqlglot cannot parse,
    and extract each table's model-key columns for use as a primary key.

    Doris CREATE TABLE has extra clauses after the column-definition block:
      DUPLICATE KEY / AGGREGATE KEY / UNIQUE KEY (model keys, not a real PK)
      PARTITION BY RANGE(col) (PARTITION p VALUES [(...), (...)), ...)
      DISTRIBUTED BY HASH(col) BUCKETS N
      PROPERTIES (...)
    These use syntax that confuses sqlglot and cause the whole statement to
    fall back to a Command node (no columns extracted).

    Strategy: for each CREATE TABLE, locate the *outer* closing ) using
    paren-depth tracking (so nested parens in types/strings are safe), then
    discard everything between that ) and the trailing ; — keeping only the
    column-definition block. Before discarding, pull the model-key columns out
    of that tail so callers can surface them as the table's primary key.

    Returns the cleaned SQL plus ``{table_name: [key_col, ...]}``.
    """
    out: list[str] = []
    keys: dict[str, list[str]] = {}
    pos = 0

    for m in re.finditer(r'CREATE\s+TABLE\s+', sql, re.IGNORECASE):
        out.append(sql[pos:m.start()])
        pos = m.start()

        open_paren = sql.find('(', m.end())
        if open_paren == -1:
            break

        # Table name sits between "CREATE TABLE " and the opening paren.
        name_part = sql[m.end():open_paren].strip()
        tbl_name = name_part.split('.')[-1].strip().strip('`').strip()

        depth = 0
        i = open_paren
        close_paren = open_paren
        while i < len(sql):
            ch = sql[i]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    close_paren = i
                    break
            elif ch in ("'", '"', '`'):
                quote = ch
                i += 1
                while i < len(sql):
                    if sql[i] == '\\':
                        i += 1
                    elif sql[i] == quote:
                        break
                    i += 1
            i += 1

        # Keep everything up to and including the column-list closing paren
        out.append(sql[pos:close_paren + 1])
        # Skip the Doris-specific tail (up to and including the next ;)
        next_semi = sql.find(';', close_paren)
        tail = sql[close_paren + 1:next_semi if next_semi != -1 else len(sql)]

        km = _DORIS_KEY_RE.search(tail)
        if km and tbl_name:
            cols = [c.strip().strip('`').strip() for c in km.group(1).split(',')]
            cols = [c for c in cols if c]
            if cols:
                keys[tbl_name] = cols

        pos = next_semi + 1 if next_semi != -1 else len(sql)
        out.append(';')

    out.append(sql[pos:])
    return ''.join(out), keys


def _map_type(raw: str) -> str:
    # Strip length/precision and MySQL modifiers (UNSIGNED, ZEROFILL, etc.)
    r = raw.upper().split("(")[0].strip()
    r = re.sub(r"\b(UNSIGNED|ZEROFILL|SIGNED)\b", "", r).strip()
    if r in {"INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "MEDIUMINT",
             "INT2", "INT4", "INT8"}:
        return "integer"
    if r in {"SERIAL", "BIGSERIAL", "SMALLSERIAL"}:
        return "integer"
    if r in {"FLOAT", "REAL", "DOUBLE", "DOUBLE PRECISION", "FLOAT4", "FLOAT8"}:
        return "float"
    if r in {"DECIMAL", "NUMERIC", "MONEY", "SMALLMONEY", "NUMBER"}:
        return "decimal"
    if r in {"CHAR", "VARCHAR", "NCHAR", "NVARCHAR", "CHARACTER VARYING",
             "CHARACTER", "BPCHAR", "CITEXT", "STRING",
             "VARCHAR2", "NVARCHAR2"}:
        return "string"
    if r in {"TEXT", "TINYTEXT", "MEDIUMTEXT", "LONGTEXT", "CLOB", "NTEXT"}:
        return "text"
    if r in {"BOOLEAN", "BOOL", "BIT"}:
        return "boolean"
    if r == "DATE":
        return "date"
    if r in {"DATETIME", "TIMESTAMP", "TIMESTAMP WITHOUT TIME ZONE",
             "TIMESTAMP WITH TIME ZONE", "TIMESTAMPTZ", "DATETIME2",
             "SMALLDATETIME"}:
        return "datetime"
    if r in {"JSON", "JSONB"}:
        return "json"
    if r == "ENUM":
        return "enum"
    return "unknown"


def _extract_length(dtype_str: str) -> Optional[int]:
    m = re.search(r"\((\d+)(?:,\s*\d+)?\)", dtype_str)
    return int(m.group(1)) if m else None


def _extract_precision_scale(dtype_str: str) -> tuple[Optional[int], Optional[int]]:
    m = re.search(r"\((\d+),\s*(\d+)\)", dtype_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\((\d+)\)", dtype_str)
    if m:
        return int(m.group(1)), None
    return None, None


def _unquote_default(sql_val: str) -> Any:
    """Strip surrounding quotes from a SQL default value string."""
    from typing import Any
    s = sql_val.strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s


class DDLParser:
    def parse(self, source: str, dialect: str = "mysql") -> RelationalSchemaModel:
        if not source or not source.strip():
            raise ValueError("empty DDL: no SQL statements provided")

        dialect = dialect.lower()
        if dialect not in _SUPPORTED:
            raise ValueError(
                f"Unsupported dialect: {dialect!r}. Supported: {sorted(_SUPPORTED)}"
            )

        glot_dialect = _DIALECT_MAP[dialect]

        source, doris_keys = _preprocess_doris(source)

        try:
            statements = sqlglot.parse(
                source, dialect=glot_dialect, error_level=sqlglot.ErrorLevel.WARN
            )
        except Exception as exc:
            raise ValueError(f"DDL parse error: {exc}") from exc

        tables: list[TableDef] = []
        table_names_seen: set[str] = set()

        for stmt in statements:
            if not isinstance(stmt, exp.Create):
                continue
            this = stmt.this
            if not isinstance(this, exp.Schema):
                continue

            table_name = this.this.name
            if table_name in table_names_seen:
                continue
            table_names_seen.add(table_name)

            columns: list[ColumnDef] = []
            pk_cols: list[str] = []
            fks: list[ForeignKeyDef] = []
            unique_constraints: list[list[str]] = []

            for expr in this.expressions:
                if isinstance(expr, exp.ColumnDef):
                    col = self._parse_column(expr, dialect=glot_dialect)
                    if col.primary_key and col.name not in pk_cols:
                        pk_cols.append(col.name)
                    if col.unique:
                        unique_constraints.append([col.name])
                    columns.append(col)

                elif isinstance(expr, exp.PrimaryKey):
                    pk_cols = [c.name for c in expr.expressions]
                    for col in columns:
                        if col.name in pk_cols:
                            col.primary_key = True

                elif isinstance(expr, exp.ForeignKey):
                    fk_cols = [c.name for c in expr.expressions]
                    ref = expr.args.get("reference")
                    if ref:
                        ref_tbl_expr = ref.this
                        ref_table = (
                            ref_tbl_expr.this.name
                            if hasattr(ref_tbl_expr, "this")
                            else str(ref_tbl_expr)
                        )
                        explicit_ref_cols = [c.name for c in ref.expressions] if ref.expressions else []
                        # If ref columns were not explicit, try to infer from ref table's PK
                        # (built so far) — fallback to fk_cols as last resort
                        if not explicit_ref_cols:
                            existing = next((t for t in tables if t.name == ref_table), None)
                            if existing and existing.primary_key:
                                explicit_ref_cols = existing.primary_key
                            else:
                                # Use fk_cols as placeholder; will be correct for self-ref
                                explicit_ref_cols = fk_cols
                        for fk_col, ref_col in zip(fk_cols, explicit_ref_cols):
                            fks.append(ForeignKeyDef(
                                column=fk_col,
                                ref_table=ref_table,
                                ref_column=ref_col,
                            ))

                elif isinstance(expr, exp.UniqueColumnConstraint):
                    # Table-level UNIQUE KEY — extract column names via .args['this']
                    schema_node = expr.args.get("this")
                    if schema_node and hasattr(schema_node, "expressions"):
                        cols = [c.name for c in schema_node.expressions if hasattr(c, "name")]
                        if cols:
                            unique_constraints.append(cols)

                elif isinstance(expr, exp.Constraint):
                    # Named constraint: CONSTRAINT name PRIMARY KEY (...) / UNIQUE (...)
                    for sub in expr.expressions:
                        if isinstance(sub, exp.PrimaryKey):
                            named_pk = [c.name for c in sub.expressions if hasattr(c, "name")]
                            if named_pk:
                                pk_cols = named_pk
                                for col in columns:
                                    if col.name in pk_cols:
                                        col.primary_key = True
                        elif isinstance(sub, exp.UniqueColumnConstraint):
                            # Named UNIQUE — columns may be in sub.args["this"] or sub.expressions
                            ucols: list[str] = []
                            inner = sub.args.get("this")
                            if inner and hasattr(inner, "expressions"):
                                ucols = [c.name for c in inner.expressions if hasattr(c, "name")]
                            elif hasattr(sub, "expressions"):
                                ucols = [c.name for c in sub.expressions if hasattr(c, "name")]
                            if ucols:
                                unique_constraints.append(ucols)
                                for col in columns:
                                    if col.name in ucols:
                                        col.unique = True

            # Doris/OLAP tables have no real PRIMARY KEY — fall back to the
            # DUPLICATE/UNIQUE/AGGREGATE KEY columns so the UI shows a key.
            # These are *sort* keys (not guaranteed unique), so we record them
            # on the table for display/metadata but do NOT set col.primary_key
            # (that would wrongly force per-column uniqueness on e.g. etl_dt).
            if not pk_cols and table_name in doris_keys:
                col_names = {c.name for c in columns}
                pk_cols = [c for c in doris_keys[table_name] if c in col_names]

            tables.append(TableDef(
                name=table_name,
                columns=columns,
                primary_key=pk_cols,
                foreign_keys=fks,
                unique_constraints=unique_constraints,
            ))

        if not tables:
            raise ValueError("empty DDL: no CREATE TABLE statements found")

        tables_dict = {t.name: t for t in tables}
        order = _topological_sort(tables_dict)
        steps = [GenerationStep(step=i, name=t, kind="table") for i, t in enumerate(order)]

        return RelationalSchemaModel(
            dialect=dialect,
            tables=tables,
            generation_order=steps,
            schema_type="relational",
        )

    def _parse_column(self, expr: exp.ColumnDef, dialect: str = "mysql") -> ColumnDef:
        name = expr.name
        dtype_expr = expr.args.get("kind")
        raw_type = dtype_expr.sql(dialect=dialect) if dtype_expr else "TEXT"
        type_cat = _map_type(raw_type)

        # SERIAL → auto_increment in PostgreSQL
        auto_increment = type_cat == "integer" and raw_type.upper().split("(")[0].strip() in {
            "SERIAL", "BIGSERIAL", "SMALLSERIAL"
        }

        nullable = True
        primary_key = False
        unique = False
        default = None
        enum_values: Optional[list[str]] = None
        length: Optional[int] = None
        precision: Optional[int] = None
        scale: Optional[int] = None
        comment = ""

        if type_cat == "string":
            length = _extract_length(raw_type)
        elif type_cat == "decimal":
            precision, scale = _extract_precision_scale(raw_type)
        elif type_cat == "enum" and dtype_expr and isinstance(dtype_expr, exp.DataType):
            enum_values = [
                lit.this.strip("'\"")
                for lit in dtype_expr.expressions
                if isinstance(lit, exp.Literal)
            ]

        for constraint in expr.constraints:
            ckind = constraint.args.get("kind")

            if isinstance(ckind, exp.NotNullColumnConstraint):
                nullable = False
            elif isinstance(ckind, exp.PrimaryKeyColumnConstraint):
                primary_key = True
                nullable = False
            elif isinstance(ckind, (exp.AutoIncrementColumnConstraint,
                                    exp.GeneratedAsIdentityColumnConstraint)):
                auto_increment = True
            elif isinstance(ckind, exp.UniqueColumnConstraint):
                unique = True
            elif isinstance(ckind, exp.DefaultColumnConstraint):
                raw_default = ckind.this.sql(dialect=dialect) if ckind.this else None
                default = _unquote_default(raw_default) if raw_default else None
            elif isinstance(ckind, exp.CommentColumnConstraint):
                comment = getattr(ckind.this, "name", "") or ""

        return ColumnDef(
            name=name,
            type_category=type_cat,
            raw_type=raw_type,
            nullable=nullable,
            primary_key=primary_key,
            auto_increment=auto_increment,
            unique=unique,
            default=default,
            length=length,
            precision=precision,
            scale=scale,
            enum_values=enum_values,
            comment=comment,
        )


def _topological_sort(tables: dict[str, TableDef]) -> list[str]:
    deps: dict[str, set[str]] = {name: set() for name in tables}
    for name, tbl in tables.items():
        for fk in tbl.foreign_keys:
            if fk.ref_table in tables and fk.ref_table != name:
                deps[name].add(fk.ref_table)

    in_degree = {n: len(d) for n, d in deps.items()}
    queue = sorted(n for n, d in in_degree.items() if d == 0)
    result: list[str] = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for name in sorted(tables.keys()):
            if node in deps[name]:
                deps[name].discard(node)
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    queue.append(name)

    if len(result) != len(tables):
        remaining = set(tables) - set(result)
        raise ValueError(f"Circular FK dependency detected: {remaining}")

    return result
