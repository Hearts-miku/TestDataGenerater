"""MySQL write routes — test connection + bulk insert generated data."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_db, get_registry
from app.services.mysql_write_service import MysqlWriteService

router = APIRouter()


class ConnParams(BaseModel):
    host: str
    port: int = 3306
    database: str
    user: str
    password: str


class PingRequest(ConnParams):
    pass


class WriteRequest(ConnParams):
    schema_id: str
    create_tables: bool = True
    truncate_before_insert: bool = False


def _get_svc(
    registry=Depends(get_registry),
    db=Depends(get_db),
) -> MysqlWriteService:
    return MysqlWriteService(registry=registry, db=db)


@router.post("/mysql/ping")
async def mysql_ping(req: PingRequest, svc: MysqlWriteService = Depends(_get_svc)) -> dict:
    try:
        version = svc.ping(req.model_dump())
        return {"ok": True, "version": version}
    except Exception as exc:
        raise HTTPException(400, f"连接失败: {exc}")


@router.post("/mysql/write")
async def mysql_write(req: WriteRequest, svc: MysqlWriteService = Depends(_get_svc)) -> dict:
    conn_params = {k: v for k, v in req.model_dump().items() if k not in ("schema_id", "create_tables", "truncate_before_insert")}
    try:
        results = svc.write(
            schema_id=req.schema_id,
            conn_params=conn_params,
            create_tables=req.create_tables,
            truncate_before_insert=req.truncate_before_insert,
        )
    except KeyError as exc:
        raise HTTPException(404, f"Schema not found: {exc}")
    except Exception as exc:
        raise HTTPException(500, f"写入失败: {exc}")

    failed = [t for t, r in results.items() if r["error"]]
    return {
        "ok": len(failed) == 0,
        "tables": results,
        "failed_tables": failed,
    }
