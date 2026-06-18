"""Table-relationship management — AI inference, manual edits, Cypher export.

Relations are stored as the schema's foreign keys (so generation closes joins).
This router lets the UI:
  * POST /api/relations/infer    — AI/heuristic infer relations from DDL
  * POST /api/relations/import   — import relations from a Cypher schema graph
  * GET  /api/relations          — list current relations of a schema
  * PUT  /api/relations          — replace the schema's relations
  * GET  /api/relations/export   — download the relations as a Cypher graph
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.core.registry import SchemaRegistry
from app.core.relation_parser import Relation, parse_schema_graph, relations_to_cypher
from app.core.schema_merge import inject_relations, recompute_generation_order
from app.core.schema_model import ForeignKeyDef
from app.db.duckdb_client import DuckDBClient
from app.dependencies import get_db, get_registry

logger = logging.getLogger(__name__)
router = APIRouter()


class RelationItem(BaseModel):
    child_table: str
    child_col: str
    parent_table: str
    parent_col: str
    note: str = ""


class InferRequest(BaseModel):
    schema_id: str
    ai_enabled: bool = False
    llm_config: dict | None = None


class RelationsResponse(BaseModel):
    schema_id: str
    relations: list[RelationItem]
    ai_used: bool = False


class UpdateRequest(BaseModel):
    schema_id: str
    relations: list[RelationItem]


def _current_relations(schema) -> list[RelationItem]:
    items: list[RelationItem] = []
    for tbl in schema.tables:
        for fk in tbl.foreign_keys:
            items.append(RelationItem(
                child_table=tbl.name, child_col=fk.column,
                parent_table=fk.ref_table, parent_col=fk.ref_column,
            ))
    return items


def _apply_relations(schema, items: list[RelationItem], db: DuckDBClient) -> None:
    """Replace all foreign keys with the given relations, recompute order, rebuild tables."""
    for tbl in schema.tables:
        tbl.foreign_keys = []
    rels = [
        Relation(i.child_table, i.child_col, i.parent_table, i.parent_col)
        for i in items
    ]
    inject_relations(schema, rels)  # validates endpoints + recomputes order
    db.create_tables(schema)


@router.post("/relations/infer", response_model=RelationsResponse)
async def infer_relations_route(
    req: InferRequest,
    registry: SchemaRegistry = Depends(get_registry),
    db: DuckDBClient = Depends(get_db),
):
    try:
        schema = registry.require(req.schema_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))

    from app.ai.relation_infer import infer_relations

    llm = None
    ai_used = False
    if req.ai_enabled:
        try:
            from app.ai.llm_config import LLMConfig, build_llm
            from app.config import settings
            cfg = LLMConfig.from_dict(req.llm_config or {
                "base_url": settings.llm_base_url,
                "api_key": settings.llm_api_key,
                "model": settings.llm_model,
            })
            llm = build_llm(cfg)
            ai_used = True
        except Exception:
            logger.warning("LLM build failed; falling back to heuristic", exc_info=True)
            llm = None
            ai_used = False

    relations = infer_relations(schema, llm=llm)
    items = [
        RelationItem(child_table=r.child_table, child_col=r.child_col,
                     parent_table=r.parent_table, parent_col=r.parent_col)
        for r in relations
    ]
    # Persist the inferred relations so generation can use them immediately.
    _apply_relations(schema, items, db)
    return RelationsResponse(schema_id=schema.id, relations=items, ai_used=ai_used)


class ImportRequest(BaseModel):
    schema_id: str
    cypher: str
    replace: bool = False   # clear existing relations before importing


@router.post("/relations/import", response_model=RelationsResponse)
async def import_relations(
    req: ImportRequest,
    registry: SchemaRegistry = Depends(get_registry),
    db: DuckDBClient = Depends(get_db),
):
    """Import table relations from a Cypher schema graph (e.g. schema_graph.cypher).

    Parsed edges are matched against the current schema's tables/columns; only
    relations whose endpoints exist are kept. Merges with existing relations
    unless ``replace`` is set.
    """
    try:
        schema = registry.require(req.schema_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    if not req.cypher.strip():
        raise HTTPException(422, "cypher content is empty")

    parsed = parse_schema_graph(req.cypher)
    if not parsed:
        raise HTTPException(
            422,
            "未从 Cypher 中解析出表关系。请确认是 schema graph 格式"
            "（MATCH (a:Table {fqn}) ... MERGE (a)-[r]->(b) SET r.via = '...'）。",
        )

    existing = [] if req.replace else _current_relations(schema)
    imported = [
        RelationItem(child_table=r.child_table, child_col=r.child_col,
                     parent_table=r.parent_table, parent_col=r.parent_col)
        for r in parsed
    ]
    # Merge (existing first), de-duplicated by the 4-tuple.
    seen: set[tuple] = set()
    merged: list[RelationItem] = []
    for it in existing + imported:
        key = (it.child_table, it.child_col, it.parent_table, it.parent_col)
        if key not in seen:
            seen.add(key)
            merged.append(it)

    _apply_relations(schema, merged, db)
    kept = _current_relations(schema)
    return RelationsResponse(schema_id=schema.id, relations=kept, ai_used=False)


@router.get("/relations", response_model=RelationsResponse)
async def get_relations(
    schema_id: str,
    registry: SchemaRegistry = Depends(get_registry),
):
    try:
        schema = registry.require(schema_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    return RelationsResponse(schema_id=schema.id, relations=_current_relations(schema))


@router.put("/relations", response_model=RelationsResponse)
async def update_relations(
    req: UpdateRequest,
    registry: SchemaRegistry = Depends(get_registry),
    db: DuckDBClient = Depends(get_db),
):
    try:
        schema = registry.require(req.schema_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    _apply_relations(schema, req.relations, db)
    return RelationsResponse(schema_id=schema.id, relations=_current_relations(schema))


@router.get("/relations/export", response_class=PlainTextResponse)
async def export_relations(
    schema_id: str,
    registry: SchemaRegistry = Depends(get_registry),
):
    try:
        schema = registry.require(schema_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))

    rels = [
        Relation(t.name, fk.column, fk.ref_table, fk.ref_column)
        for t in schema.tables for fk in t.foreign_keys
    ]
    cypher = relations_to_cypher(rels)
    return PlainTextResponse(
        cypher,
        headers={"Content-Disposition": 'attachment; filename="schema_graph.cypher"'},
    )
