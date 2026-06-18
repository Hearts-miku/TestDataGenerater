"""Custom generation rules — natural-language translation + persistence.

  * POST /api/rules/translate — NL text → per-column specs (preview, not saved)
  * GET  /api/rules           — current custom rules of a schema
  * PUT  /api/rules           — replace a schema's custom rules
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.registry import SchemaRegistry
from app.dependencies import get_registry

logger = logging.getLogger(__name__)
router = APIRouter()


class TranslateRequest(BaseModel):
    schema_id: str
    text: str
    llm_config: dict | None = None


class FromSamplesRequest(BaseModel):
    schema_id: str
    source_type: str            # "sql" | "csv"
    content: str
    table: str | None = None    # required for CSV (no table name in the data)


class SpecsResponse(BaseModel):
    schema_id: str
    field_specs: dict[str, dict]


class UpdateRulesRequest(BaseModel):
    schema_id: str
    field_specs: dict[str, dict]


@router.post("/rules/translate", response_model=SpecsResponse)
async def translate_rules_route(
    req: TranslateRequest,
    registry: SchemaRegistry = Depends(get_registry),
):
    try:
        schema = registry.require(req.schema_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    if not req.text.strip():
        raise HTTPException(422, "rule text is empty")

    try:
        from app.ai.custom_rule import translate_rules
        from app.ai.llm_config import LLMConfig, build_llm
        from app.config import settings

        cfg = LLMConfig.from_dict(req.llm_config or {
            "base_url": settings.llm_base_url,
            "api_key": settings.llm_api_key,
            "model": settings.llm_model,
        })
        llm = build_llm(cfg)
    except Exception as exc:
        raise HTTPException(
            400,
            f"自然语言规则解析需要配置可用的 LLM（AI 配置）：{exc}",
        )

    try:
        specs = translate_rules(llm, schema, req.text)
    except Exception as exc:
        logger.warning("rule translation failed", exc_info=True)
        raise HTTPException(502, f"规则解析失败：{exc}")

    return SpecsResponse(schema_id=schema.id, field_specs=specs)


@router.post("/rules/from-samples", response_model=SpecsResponse)
async def rules_from_samples(
    req: FromSamplesRequest,
    registry: SchemaRegistry = Depends(get_registry),
):
    """Infer per-column rules from sample data (INSERT SQL or CSV). No LLM needed."""
    try:
        schema = registry.require(req.schema_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    if not req.content.strip():
        raise HTTPException(422, "样例数据为空")

    from app.ai.custom_rule import validate_specs
    from app.generator.sample_infer import infer_specs_from_csv, infer_specs_from_insert

    stype = req.source_type.lower()
    try:
        if stype == "sql":
            specs = infer_specs_from_insert(schema, req.content)
        elif stype == "csv":
            if not req.table:
                raise HTTPException(422, "CSV 需要指定目标表（table）")
            specs = infer_specs_from_csv(schema, req.table, req.content)
        else:
            raise HTTPException(422, f"未知的样例类型：{req.source_type!r}（应为 sql 或 csv）")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("sample inference failed", exc_info=True)
        raise HTTPException(502, f"样例识别失败：{exc}")

    if not specs:
        raise HTTPException(
            422,
            "未能从样例中识别出字段规则。请确认表名/列名与当前 schema 匹配，且每列至少有 2 行样例。",
        )
    return SpecsResponse(schema_id=schema.id, field_specs=validate_specs(schema, specs))


@router.get("/rules", response_model=SpecsResponse)
async def get_rules(
    schema_id: str,
    registry: SchemaRegistry = Depends(get_registry),
):
    try:
        schema = registry.require(schema_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    return SpecsResponse(schema_id=schema.id, field_specs=dict(schema.field_specs or {}))


@router.put("/rules", response_model=SpecsResponse)
async def update_rules(
    req: UpdateRulesRequest,
    registry: SchemaRegistry = Depends(get_registry),
):
    try:
        schema = registry.require(req.schema_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc))

    from app.ai.custom_rule import validate_specs

    schema.field_specs = validate_specs(schema, req.field_specs)
    return SpecsResponse(schema_id=schema.id, field_specs=schema.field_specs)
