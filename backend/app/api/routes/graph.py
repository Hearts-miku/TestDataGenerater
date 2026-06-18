"""Graph API routes — schema info, stats, and Cypher query explorer."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.kuzu_client import KuzuClient
from app.dependencies import get_graph_db

router = APIRouter()


class CypherRequest(BaseModel):
    cypher: str


@router.get("/graph/schema")
async def graph_schema(
    graph_db: KuzuClient = Depends(get_graph_db),
) -> dict:
    return graph_db.get_schema()


@router.get("/graph/stats")
async def graph_stats(
    graph_db: KuzuClient = Depends(get_graph_db),
) -> dict:
    return graph_db.get_stats()


@router.post("/graph/cypher")
async def run_cypher(
    req: CypherRequest,
    graph_db: KuzuClient = Depends(get_graph_db),
) -> dict:
    if not req.cypher or not req.cypher.strip():
        raise HTTPException(400, "cypher query is required")
    try:
        rows = graph_db.query(req.cypher)
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except Exception as exc:
        raise HTTPException(422, f"Query error: {exc}")
    return {"rows": rows, "count": len(rows)}
