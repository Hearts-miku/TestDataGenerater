"""QueryService — read-only SQL queries via DuckDB."""

from __future__ import annotations

from typing import Any

from app.db.duckdb_client import DuckDBClient


class QueryService:
    def __init__(self, db: DuckDBClient) -> None:
        self._db = db

    def sql_query(self, sql: str) -> list[dict[str, Any]]:
        return self._db.query(sql)

    def get_tables(self) -> list[dict]:
        return self._db.get_tables()

    def get_er_schema(self) -> dict:
        return self._db.get_er_schema()
