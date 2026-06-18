from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.services.export_service import ExportService
from app.dependencies import get_export_service

router = APIRouter()


class ExportRequest(BaseModel):
    schema_id: str
    format: Literal["sql", "csv", "json", "xlsx"]


_MEDIA: dict[str, str] = {
    "sql": "text/plain",
    "csv": "application/zip",
    "json": "application/json",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_FILENAME: dict[str, str] = {
    "sql": "export.sql",
    "csv": "export.zip",
    "json": "export.json",
    "xlsx": "export.xlsx",
}


@router.post("/export")
async def export_data(
    req: ExportRequest,
    svc: ExportService = Depends(get_export_service),
):
    try:
        result = svc.export(req.schema_id, req.format)
    except KeyError as exc:
        raise HTTPException(404, str(exc))

    body = result if isinstance(result, bytes) else result.encode("utf-8")
    return Response(
        content=body,
        media_type=_MEDIA[req.format],
        headers={"Content-Disposition": f'attachment; filename="{_FILENAME[req.format]}"'},
    )
