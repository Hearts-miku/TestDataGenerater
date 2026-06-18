"""AI configuration routes — test LLM connectivity."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class LLMConfigRequest(BaseModel):
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.7


@router.post("/ai/test-llm")
async def test_llm(req: LLMConfigRequest) -> dict:
    """Validate LLM config and do a quick connectivity probe."""
    from app.ai.llm_config import LLMConfig, is_llm_reachable

    try:
        cfg = LLMConfig(
            base_url=req.base_url,
            api_key=req.api_key,
            model=req.model,
            temperature=req.temperature,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    reachable = is_llm_reachable(cfg.base_url)
    return {
        "ok": reachable,
        "base_url": cfg.base_url,
        "model": cfg.model,
        "reachable": reachable,
    }
