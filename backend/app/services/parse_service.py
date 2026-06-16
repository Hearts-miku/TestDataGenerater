"""ParseService — orchestrates DDL/Cypher parsing → schema registry → DuckDB."""

from __future__ import annotations

from app.core.ddl_parser import DDLParser
from app.core.registry import SchemaRegistry
from app.core.schema_model import RelationalSchemaModel
from app.db.duckdb_client import DuckDBClient


class ParseService:
    def __init__(self, registry: SchemaRegistry, db: DuckDBClient) -> None:
        self._registry = registry
        self._db = db
        self._ddl_parser = DDLParser()

    def parse_ddl(self, source: str, dialect: str = "mysql") -> RelationalSchemaModel:
        schema = self._ddl_parser.parse(source, dialect=dialect)
        self._registry.save(schema)
        self._db.create_tables(schema)
        return schema

    def parse_cypher(self, source: str) -> RelationalSchemaModel:
        # Phase 3 — stub returns empty graph schema for now
        from app.core.schema_model import RelationalSchemaModel
        schema = RelationalSchemaModel(schema_type="graph", dialect="cypher")
        self._registry.save(schema)
        return schema
