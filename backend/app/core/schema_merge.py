"""Merge several DDL files into one schema and inject curated cross-table relations.

Doris/OLAP DDL has no FOREIGN KEY, and the real relationships span multiple files
(e.g. a credit-card table in EDWICL_DATA references the customer master in the same
schema, while label tables in RCLP_DATA also reference it). To generate join-consistent
data we must:

  1. Parse all DDL files into a single :class:`RelationalSchemaModel` (one table namespace).
  2. Inject the relations from the Cypher schema graph as :class:`ForeignKeyDef` edges,
     but only when both endpoints (table *and* column) actually exist.
  3. Recompute a FK-safe generation order so authority tables are generated first.
"""

from __future__ import annotations

from collections import defaultdict

from app.core.ddl_parser import DDLParser
from app.core.relation_parser import Relation
from app.core.schema_model import (
    ForeignKeyDef,
    GenerationStep,
    RelationalSchemaModel,
)


def merge_ddl_schemas(sources: list[str], dialect: str = "mysql") -> RelationalSchemaModel:
    """Parse and merge multiple DDL sources into a single schema.

    Tables are keyed by name; the first definition of a duplicate name wins.
    """
    parser = DDLParser()
    merged = RelationalSchemaModel(dialect=dialect)
    seen: set[str] = set()

    for src in sources:
        if not src or not src.strip():
            continue
        parsed = parser.parse(src, dialect=dialect)
        for tbl in parsed.tables:
            if tbl.name in seen:
                continue
            seen.add(tbl.name)
            merged.tables.append(tbl)

    recompute_generation_order(merged)
    return merged


def inject_relations(schema: RelationalSchemaModel, relations: list[Relation]) -> int:
    """Add curated relations as foreign keys where both endpoints exist.

    Returns the number of FK edges injected. After injection the generation order
    is recomputed so referenced (authority) tables come first.
    """
    by_name = schema.tables_by_name
    injected = 0

    for rel in relations:
        child = by_name.get(rel.child_table)
        parent = by_name.get(rel.parent_table)
        if child is None or parent is None:
            continue
        if child.column(rel.child_col) is None or parent.column(rel.parent_col) is None:
            continue
        # Skip a self-loop on the same column of the same table (no-op join).
        if child.name == parent.name and rel.child_col == rel.parent_col:
            continue
        # Avoid duplicate FK edges.
        if any(
            fk.column == rel.child_col
            and fk.ref_table == rel.parent_table
            and fk.ref_column == rel.parent_col
            for fk in child.foreign_keys
        ):
            continue
        child.foreign_keys.append(
            ForeignKeyDef(
                column=rel.child_col,
                ref_table=rel.parent_table,
                ref_column=rel.parent_col,
            )
        )
        injected += 1

    recompute_generation_order(schema)
    return injected


def recompute_generation_order(schema: RelationalSchemaModel) -> None:
    """Set schema.generation_order to a FK-safe topological order.

    Tolerates circular FK dependencies by breaking the cycle at the node with the
    fewest unresolved dependencies (instead of raising).
    """
    order = _robust_topological_order(schema)
    schema.generation_order = [
        GenerationStep(step=i, name=name, kind="table")
        for i, name in enumerate(order)
    ]


def _robust_topological_order(schema: RelationalSchemaModel) -> list[str]:
    """Kahn's algorithm; on a cycle, force-pick the lowest in-degree node."""
    tables = {t.name: t for t in schema.tables}
    deps: dict[str, set[str]] = {name: set() for name in tables}
    for name, tbl in tables.items():
        for fk in tbl.foreign_keys:
            if fk.ref_table in tables and fk.ref_table != name:
                deps[name].add(fk.ref_table)

    in_degree = {n: len(d) for n, d in deps.items()}
    result: list[str] = []
    remaining = set(tables)

    while remaining:
        ready = sorted(n for n in remaining if in_degree[n] == 0)
        if not ready:
            # Cycle: break it by force-resolving the lowest in-degree node.
            ready = [min(remaining, key=lambda n: (in_degree[n], n))]
        for node in ready:
            result.append(node)
            remaining.discard(node)
            for other in remaining:
                if node in deps[other]:
                    deps[other].discard(node)
                    in_degree[other] -= 1

    return result
