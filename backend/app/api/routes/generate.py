from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.generate_service import GenerateService
from app.dependencies import get_generate_service

router = APIRouter()


class GenerateRequest(BaseModel):
    schema_id: str
    row_counts: dict[str, int]
    ai_enabled: bool = False
    llm_config: dict | None = None   # {base_url, api_key, model} — overrides settings


@router.post("/generate")
async def generate_data(
    req: GenerateRequest,
    svc: GenerateService = Depends(get_generate_service),
):
    try:
        result = svc.generate(
            schema_id=req.schema_id,
            row_counts=req.row_counts,
            ai_enabled=req.ai_enabled,
            llm_config=req.llm_config,
        )
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(500, str(exc))

    return result
