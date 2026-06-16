"""DuckDB client — Phase 1 relational store."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import duckdb

from app.core.schema_model import RelationalSchemaModel

_WRITE_PATTERN = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|REPLACE|MERGE|COPY)\b",
    re.IGNORECASE,
)

_TYPE_MAP: dict[str, str] = {
    "integer":  "BIGINT",
    "float":    "DOUBLE",
    "decimal":  "DECIMAL",
    "string":   "VARCHAR",
    "text":     "TEXT",
    "boolean":  "BOOLEAN",
    "date":     "DATE",
    "datetime": "TIMESTAMP",
    "json":     "TEXT",
    "enum":     "VARCHAR",
    "unknown":  "TEXT",
}


class DuckDBClient:
    def __init__(self, path: str = ":memory:") -> None:
        self._path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(path)
        # FK metadata cache (DuckDB doesn't persist FK constraints)
        self._fk_meta: list[dict] = []

    # ── Schema management ──────────────────────────────────────────────────

    def create_tables(self, schema: RelationalSchemaModel) -> None:
        """Create tables in topological/definition order (idempotent)."""
        # Build FK metadata for ER schema
        for tbl in schema.tables:
            for fk in tbl.foreign_keys:
                entry = {"from_table": tbl.name, "from_col": fk.column,
                         "to_table": fk.ref_table, "to_col": fk.ref_column}
                if entry not in self._fk_meta:
                    self._fk_meta.append(entry)

        order_names = [s.name for s in schema.generation_order] if schema.generation_order else [t.name for t in schema.tables]
        tables_by_name = schema.tables_by_name

        for table_name in order_names:
            if table_name not in tables_by_name:
                continue
            tbl = tables_by_name[table_name]
            col_defs = []
            for col in tbl.columns:
                dtype = _TYPE_MAP.get(col.type_category, "TEXT")
                if col.type_category == "decimal" and col.precision:
                    scale = col.scale or 2
                    dtype = f"DECIMAL({col.precision},{scale})"
                elif col.type_category == "string" and col.length:
                    dtype = f"VARCHAR({col.length})"

                parts = [f'"{col.name}" {dtype}']
                if not col.nullable and not col.primary_key:
                    parts.append("NOT NULL")
                if col.primary_key:
                    parts.append("PRIMARY KEY")
                col_defs.append(" ".join(parts))

            ddl = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(col_defs)})'
            self._conn.execute(ddl)

    def truncate_table(self, table_name: str) -> None:
        """Delete all rows from a table (preserves schema)."""
        existing = self._conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema='main' AND table_name=?",
            [table_name],
        ).fetchone()
        if existing:
            self._conn.execute(f'DELETE FROM "{table_name}"')

    def reset(self) -> None:
        """Drop all user tables and FK cache."""
        tables = self._conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        for (tname,) in reversed(tables):
            self._conn.execute(f'DROP TABLE IF EXISTS "{tname}"')
        self._fk_meta.clear()

    # ── Data operations ────────────────────────────────────────────────────

    def insert_rows(self, table: str, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        cols = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_str = ", ".join(f'"{c}"' for c in cols)
        values = [[row.get(c) for c in cols] for row in rows]
        self._conn.executemany(
            f'INSERT INTO "{table}" ({col_str}) VALUES ({placeholders})', values
        )
        return len(rows)

    # ── Query ──────────────────────────────────────────────────────────────

    def query(self, sql: str, params: list | None = None) -> list[dict[str, Any]]:
        if _WRITE_PATTERN.match(sql.strip()):
            raise PermissionError(
                f"Write operations are not allowed in the SQL Explorer: {sql[:80]}"
            )
        rel = self._conn.execute(sql, params or [])
        cols = [d[0] for d in rel.description]
        return [dict(zip(cols, row)) for row in rel.fetchall()]

    # ── Metadata ───────────────────────────────────────────────────────────

    def list_tables(self) -> list[str]:
        """Return list of table names in the main schema."""
        rows = self._conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='main' ORDER BY table_name"
        ).fetchall()
        return [r[0] for r in rows]

    def describe_table(self, table_name: str) -> list[dict]:
        """Return column info for a table."""
        rows = self._conn.execute(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema='main' AND table_name=? "
            "ORDER BY ordinal_position",
            [table_name],
        ).fetchall()
        return [{"name": c, "type": t, "nullable": n == "YES"} for c, t, n in rows]

    def get_tables(self) -> list[dict]:
        """Return all tables with column details."""
        result = []
        for tname in self.list_tables():
            result.append({"name": tname, "columns": self.describe_table(tname)})
        return result

    def get_er_schema(self) -> dict:
        """Return ER metadata: tables + FK relationships."""
        return {
            "tables": self.get_tables(),
            "foreign_keys": list(self._fk_meta),
        }

    def close(self) -> None:
        self._conn.close()
