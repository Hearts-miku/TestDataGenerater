"""MysqlWriteService — write DuckDB-generated data into a live MySQL database."""

from __future__ import annotations

from typing import Any

import pymysql
import pymysql.cursors

from app.core.registry import SchemaRegistry
from app.db.duckdb_client import DuckDBClient

_BATCH = 500

_MYSQL_TYPE: dict[str, str] = {
    "integer":  "BIGINT",
    "float":    "DOUBLE",
    "decimal":  "DECIMAL(18,4)",
    "string":   "VARCHAR(255)",
    "text":     "LONGTEXT",
    "boolean":  "TINYINT(1)",
    "date":     "DATE",
    "datetime": "DATETIME",
    "json":     "JSON",
    "enum":     "VARCHAR(255)",
    "unknown":  "TEXT",
}


def _make_conn(params: dict) -> pymysql.Connection:
    return pymysql.connect(
        host=params["host"],
        port=int(params.get("port", 3306)),
        database=params["database"],
        user=params["user"],
        password=params["password"],
        connect_timeout=8,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


class MysqlWriteService:
    def __init__(self, registry: SchemaRegistry, db: DuckDBClient) -> None:
        self._registry = registry
        self._db = db

    # ── Public API ────────────────────────────────────────────────────────────

    def ping(self, conn_params: dict) -> str:
        """Test connection. Returns server version string on success."""
        conn = _make_conn(conn_params)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION()")
                row = cur.fetchone()
                return row["VERSION()"] if row else "unknown"
        finally:
            conn.close()

    def write(
        self,
        schema_id: str,
        conn_params: dict,
        create_tables: bool = True,
        truncate_before_insert: bool = False,
    ) -> dict[str, Any]:
        schema = self._registry.require(schema_id)
        conn = _make_conn(conn_params)
        results: dict[str, dict] = {}

        try:
            with conn.cursor() as cur:
                order = [s.name for s in schema.generation_order] if schema.generation_order else [t.name for t in schema.tables]
                tbl_map = schema.tables_by_name

                for tbl_name in order:
                    tbl = tbl_map.get(tbl_name)
                    if tbl is None:
                        continue

                    try:
                        if create_tables:
                            self._create_table(cur, tbl)

                        if truncate_before_insert:
                            cur.execute(f"TRUNCATE TABLE `{tbl_name}`")

                        rows = self._db.query(f'SELECT * FROM "{tbl_name}"')
                        inserted = self._insert_rows(cur, tbl_name, rows)
                        conn.commit()
                        results[tbl_name] = {"inserted": inserted, "error": None}

                    except Exception as exc:
                        conn.rollback()
                        results[tbl_name] = {"inserted": 0, "error": str(exc)}

        finally:
            conn.close()

        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _create_table(self, cur: Any, tbl: Any) -> None:
        pk_names = [c.name for c in tbl.columns if c.primary_key]
        composite_pk = len(pk_names) > 1

        col_defs: list[str] = []
        for col in tbl.columns:
            dtype = _MYSQL_TYPE.get(col.type_category, "TEXT")
            if col.type_category == "decimal" and col.precision:
                dtype = f"DECIMAL({col.precision},{col.scale or 2})"
            elif col.type_category == "string" and col.length:
                dtype = f"VARCHAR({min(col.length, 16383)})"

            parts = [f"`{col.name}` {dtype}"]
            if not col.nullable:
                parts.append("NOT NULL")
            if col.primary_key and not composite_pk:
                parts.append("PRIMARY KEY")
            col_defs.append(" ".join(parts))

        if composite_pk:
            pk_clause = ", ".join(f"`{c}`" for c in pk_names)
            col_defs.append(f"PRIMARY KEY ({pk_clause})")

        ddl = (
            f"CREATE TABLE IF NOT EXISTS `{tbl.name}` "
            f"({', '.join(col_defs)}) "
            f"ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )
        cur.execute(ddl)

    def _insert_rows(self, cur: Any, tbl_name: str, rows: list[dict]) -> int:
        if not rows:
            return 0

        cols = list(rows[0].keys())
        col_str = ", ".join(f"`{c}`" for c in cols)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO `{tbl_name}` ({col_str}) VALUES ({placeholders})"

        total = 0
        for i in range(0, len(rows), _BATCH):
            batch = rows[i: i + _BATCH]
            values = [
                tuple(
                    int(v) if isinstance(v, bool) else v
                    for v in (row.get(c) for c in cols)
                )
                for row in batch
            ]
            cur.executemany(sql, values)
            total += len(batch)

        return total
