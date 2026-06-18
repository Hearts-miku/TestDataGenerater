"""DuckDB client — Phase 1 relational store."""

from __future__ import annotations

import csv
import os
import re
import tempfile
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
    "decimal":  "DOUBLE",
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

            pk_names = [c.name for c in tbl.columns if c.primary_key]
            composite_pk = len(pk_names) > 1

            col_defs = []
            for col in tbl.columns:
                # Use bare types (no precision/length) so the CSV reader never hits
                # a DECIMAL(p,s) or VARCHAR(n) overflow during bulk load.
                # DuckDB's bare DECIMAL/VARCHAR/TEXT accept any value.
                dtype = _TYPE_MAP.get(col.type_category, "TEXT")
                col_defs.append(f'"{col.name}" {dtype}')

            ddl = f'CREATE OR REPLACE TABLE "{table_name}" ({", ".join(col_defs)})'
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

    @staticmethod
    def _csv_val(v: Any) -> Any:
        """Sanitize values before writing to the temp CSV:
        - Large integer-valued floats → int (prevents scientific notation like 7.2e+19)
        - Strings with newlines → replace with space (prevents multi-line CSV rows that
          confuse DuckDB's read_csv_auto even when properly quoted)
        """
        if isinstance(v, float) and v.is_integer() and (v >= 1e15 or v <= -1e15):
            return int(v)
        if isinstance(v, str) and ('\n' in v or '\r' in v):
            return v.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
        return v

    def insert_rows(self, table: str, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        cols = list(rows[0].keys())
        col_str = ", ".join(f'"{c}"' for c in cols)
        # Write to a temp CSV file, then use DuckDB's vectorized CSV reader.
        # This is orders of magnitude faster than executemany row by row.
        fd, tmp_path = tempfile.mkstemp(suffix=".csv")
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(cols)
                for row in rows:
                    writer.writerow([self._csv_val(row.get(c)) for c in cols])
            safe = tmp_path.replace("\\", "/")
            self._conn.execute(
                f"INSERT INTO \"{table}\" ({col_str}) "
                f"SELECT * FROM read_csv_auto('{safe}', header=true, all_varchar=true)"
            )
        finally:
            os.unlink(tmp_path)
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
