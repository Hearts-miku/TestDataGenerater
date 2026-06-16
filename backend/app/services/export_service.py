"""ExportService — reads DuckDB data and routes to the right exporter."""

from __future__ import annotations

from typing import Any

from app.core.registry import SchemaRegistry
from app.db.duckdb_client import DuckDBClient
from app.exporter.csv_exp import CSVExporter
from app.exporter.json_exp import JSONExporter
from app.exporter.sql import SQLExporter

_EXPORTERS = {"sql": SQLExporter, "csv": CSVExporter, "json": JSONExporter}


class ExportService:
    def __init__(self, registry: SchemaRegistry, db: DuckDBClient) -> None:
        self._registry = registry
        self._db = db

    def export(self, schema_id: str, fmt: str) -> Any:
        """Return exported bytes (csv) or str (sql/json). Raises KeyError / ValueError."""
        if fmt not in _EXPORTERS:
            raise ValueError(f"Unsupported format {fmt!r}. Choose from: {', '.join(_EXPORTERS)}")

        schema = self._registry.require(schema_id)  # KeyError → 404

        data: dict[str, list[dict]] = {}
        for tbl in schema.tables:
            try:
                data[tbl.name] = self._db.query(f'SELECT * FROM "{tbl.name}"')
            except Exception:
                data[tbl.name] = []

        return _EXPORTERS[fmt]().export(data)
