"""POST /api/reset — drop all DuckDB tables and clear the schema registry."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.registry import SchemaRegistry
from app.db.duckdb_client import DuckDBClient
from app.dependencies import get_db, get_registry

router = APIRouter()


class ResetRequest(BaseModel):
    schema_id: str | None = None


@router.post("/reset")
async def reset_data(
    req: ResetRequest,
    db: DuckDBClient = Depends(get_db),
    registry: SchemaRegistry = Depends(get_registry),
) -> dict:
    db.reset()
    if req.schema_id:
        registry.delete(req.schema_id)
    else:
        for sid in list(registry.list_ids()):
            registry.delete(sid)
    return {"ok": True, "message": "All data cleared"}
