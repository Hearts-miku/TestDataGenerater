from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.query_service import QueryService
from app.dependencies import get_query_service

router = APIRouter()


class SQLRequest(BaseModel):
    sql: str


@router.post("/db/sql")
async def execute_sql(
    req: SQLRequest,
    svc: QueryService = Depends(get_query_service),
):
    try:
        rows = svc.sql_query(req.sql)
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except Exception as exc:
        raise HTTPException(400, str(exc))
    return {"rows": rows, "count": len(rows)}


@router.get("/db/tables")
async def list_tables(svc: QueryService = Depends(get_query_service)):
    return {"tables": svc.get_tables()}


@router.get("/db/er-schema")
async def er_schema(svc: QueryService = Depends(get_query_service)):
    return svc.get_er_schema()
