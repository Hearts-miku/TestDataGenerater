"""ParseService — orchestrates DDL/Cypher parsing → schema registry → DuckDB."""

from __future__ import annotations

from app.core.cypher_parser import CypherParser
from app.core.ddl_parser import DDLParser
from app.core.registry import SchemaRegistry
from app.core.schema_model import RelationalSchemaModel
from app.db.duckdb_client import DuckDBClient


class ParseService:
    def __init__(self, registry: SchemaRegistry, db: DuckDBClient) -> None:
        self._registry = registry
        self._db = db
        self._ddl_parser = DDLParser()
        self._cypher_parser = CypherParser()

    def parse_ddl(
        self,
        source: str,
        dialect: str = "mysql",
        relation_graph: str | None = None,
    ) -> RelationalSchemaModel:
        schema = self._ddl_parser.parse(source, dialect=dialect)
        if relation_graph and relation_graph.strip():
            from app.core.relation_parser import parse_schema_graph
            from app.core.schema_merge import inject_relations
            inject_relations(schema, parse_schema_graph(relation_graph))
        self._registry.save(schema)
        self._db.create_tables(schema)
        return schema

    def parse_ddl_files(
        self,
        sources: list[str],
        dialect: str = "mysql",
        relation_graph: str | None = None,
    ) -> RelationalSchemaModel:
        """Merge multiple DDL files into one schema and (optionally) inject the
        cross-table relations described by a Cypher schema graph.

        This is what powers join-consistent generation across files that have no
        explicit FOREIGN KEY (Doris/OLAP): the curated graph supplies the edges.
        """
        from app.core.relation_parser import parse_schema_graph
        from app.core.schema_merge import inject_relations, merge_ddl_schemas

        schema = merge_ddl_schemas(sources, dialect=dialect)
        if relation_graph:
            relations = parse_schema_graph(relation_graph)
            inject_relations(schema, relations)
        self._registry.save(schema)
        self._db.create_tables(schema)
        return schema

    def parse_cypher(self, source: str) -> RelationalSchemaModel:
        schema = self._cypher_parser.parse(source)
        self._registry.save(schema)
        return schema
