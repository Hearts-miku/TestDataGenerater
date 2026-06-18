"""GraphGenerateService — Faker-based generation for nodes and relationships."""

from __future__ import annotations

from typing import Any

from app.core.registry import SchemaRegistry
from app.core.schema_model import NodeDef, RelationshipDef
from app.db.kuzu_client import KuzuClient
from app.generator.graph_constraint import GraphConstraintSolver
from app.generator.rules import FakerRuleEngine

_CHUNK = 10_000


class GraphGenerateService:
    def __init__(self, registry: SchemaRegistry, graph_db: KuzuClient) -> None:
        self._registry = registry
        self._graph_db = graph_db
        self._engine = FakerRuleEngine()

    def generate(self, schema_id: str, row_counts: dict[str, int]) -> dict[str, Any]:
        schema = self._registry.require(schema_id)
        graph = schema.to_graph_schema()

        # Ensure graph tables exist and are cleared
        self._graph_db.create_graph(graph)
        for label in (n.label for n in graph.nodes):
            self._graph_db._nodes[label] = []
        for rel_type in (r.type for r in graph.relationships):
            self._graph_db._rels[rel_type] = []

        solver = GraphConstraintSolver(graph)
        tables_meta: dict[str, dict] = {}

        node_map = {n.label: n for n in graph.nodes}
        rel_map = {r.type: r for r in graph.relationships}

        # Process in generation order (nodes before rels)
        for step in solver.generation_order():
            name = step.name
            count = row_counts.get(name, 0)
            if count <= 0:
                tables_meta[name] = {"generated": 0}
                continue

            if step.kind == "node":
                node_def = node_map.get(name)
                if node_def is None:
                    continue
                rows = self._generate_nodes(node_def, count, solver)
                for i in range(0, len(rows), _CHUNK):
                    self._graph_db.insert_nodes(name, rows[i:i + _CHUNK])
                tables_meta[name] = {"generated": len(rows)}

                # Register IDs for relationship sampling
                id_prop = _find_id_prop(node_def)
                if id_prop:
                    ids = [r[id_prop] for r in rows if id_prop in r]
                    solver.register_node_ids(name, ids)
                else:
                    # Use sequential ints as synthetic IDs
                    solver.register_node_ids(name, list(range(len(rows))))

            elif step.kind == "relationship":
                rel_def = rel_map.get(name)
                if rel_def is None:
                    continue
                rows = self._generate_rels(rel_def, count, solver)
                for i in range(0, len(rows), _CHUNK):
                    self._graph_db.insert_rels(name, rows[i:i + _CHUNK])
                tables_meta[name] = {"generated": len(rows)}

        return {
            "schema_id": schema_id,
            "tables": tables_meta,
            "ai_used": False,
            "generation_meta": {"chunk_size": _CHUNK, "chunks_total": 1},
        }

    def _generate_nodes(
        self,
        node_def: NodeDef,
        count: int,
        solver: GraphConstraintSolver,
    ) -> list[dict[str, Any]]:
        unique_props = set(node_def.unique_properties)
        unique_pools: dict[str, set] = {p: set() for p in unique_props}
        rows: list[dict[str, Any]] = []
        counters: dict[str, int] = {}

        # Auto-increment integer IDs
        id_prop = _find_id_prop(node_def)
        if id_prop:
            counters[id_prop] = 1

        for _ in range(count):
            row: dict[str, Any] = {}
            for prop in node_def.properties:
                name = prop.name
                if name in counters:
                    row[name] = counters[name]
                    counters[name] += 1
                else:
                    rule = self._engine.infer_rule(name, prop.type_category)
                    rule.nullable = prop.nullable
                    rule.null_rate = 0.05 if prop.nullable else 0.0
                    val = self._engine.generate(rule)
                    if name in unique_props:
                        pool = unique_pools[name]
                        attempts = 0
                        while val in pool and attempts < 500:
                            val = self._engine.generate(rule)
                            attempts += 1
                        pool.add(val)
                    row[name] = val
            rows.append(row)

        if unique_props:
            rows = solver.deduplicate_nodes(rows, list(unique_props))
        return rows

    def _generate_rels(
        self,
        rel_def: RelationshipDef,
        count: int,
        solver: GraphConstraintSolver,
    ) -> list[dict[str, Any]]:
        seen: set[tuple] = set()
        rows: list[dict[str, Any]] = []
        max_attempts = count * 20

        for _ in range(max_attempts):
            if len(rows) >= count:
                break
            fid = solver.sample_node_ids(rel_def.from_label, 1)[0]
            tid = solver.sample_node_ids(rel_def.to_label, 1)[0]
            key = (fid, tid)
            if key in seen:
                continue
            seen.add(key)
            row: dict[str, Any] = {"from_id": fid, "to_id": tid}
            for prop in rel_def.properties:
                rule = self._engine.infer_rule(prop.name, prop.type_category)
                row[prop.name] = self._engine.generate(rule)
            rows.append(row)

        return rows


def _find_id_prop(node_def: NodeDef) -> str | None:
    """Return the name of an integer primary/unique property that looks like an ID."""
    for prop in node_def.properties:
        if prop.type_category == "integer" and prop.name.lower() in ("id", "node_id", "uid"):
            return prop.name
    return None
