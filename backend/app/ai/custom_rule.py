"""Natural-language → structured generation rules.

Lets users describe data-generation rules in plain language, e.g.::

    "年龄在18到60之间；手机号138开头；状态只能是正常/冻结/销户；
     开户日期在2020到2024年之间；金额保留两位小数，最大五万"

The LLM maps that text onto per-column specs keyed by ``"table.column"``,
which the rule-based generator applies with the highest priority (see
``rule_based._spec_to_rule`` for the supported spec kinds).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.schema_model import RelationalSchemaModel

logger = logging.getLogger(__name__)

# Faker tags the LLM may pick (must exist in rules._generate_by_rule).
_ALLOWED_FAKER = {
    "cn_name", "cn_company", "cn_org_name", "cn_id_card", "cn_bankcard",
    "cn_phone", "cn_city", "cn_address", "cn_word", "cn_money", "cn_rate",
    "cn_date_int", "email", "datetime", "date_of_birth", "random_int", "uuid4",
}

_SYSTEM = (
    "你是测试数据生成规则助手。把用户的自然语言规则翻译成结构化 JSON 规则，"
    "应用到指定的表.列。只输出 JSON 对象，不要解释。"
)


def _column_keys(schema: RelationalSchemaModel) -> set[str]:
    return {f"{t.name}.{c.name}" for t in schema.tables for c in t.columns}


def _column_signature(schema: RelationalSchemaModel, max_chars: int = 8000) -> str:
    lines: list[str] = []
    for t in schema.tables:
        for c in t.columns:
            note = f" | {c.comment}" if c.comment else ""
            lines.append(f"{t.name}.{c.name} ({c.type_category}){note}")
    text = "\n".join(lines)
    return text[:max_chars]


def validate_spec(spec: Any) -> Optional[dict]:
    """Return a cleaned spec dict, or None if it is malformed."""
    if not isinstance(spec, dict):
        return None
    kind = spec.get("kind")
    if kind == "enum" and isinstance(spec.get("enum"), list) and spec["enum"]:
        return {"kind": "enum", "enum": [str(v) for v in spec["enum"]]}
    if kind == "pool" and isinstance(spec.get("pool"), list) and spec["pool"]:
        return {"kind": "pool", "pool": [str(v) for v in spec["pool"]]}
    if kind == "pattern" and isinstance(spec.get("pattern"), str) and spec["pattern"]:
        return {"kind": "pattern", "pattern": spec["pattern"], "prefix": str(spec.get("prefix", ""))}
    if kind == "int_range":
        return _num_spec("int_range", spec)
    if kind == "decimal_range":
        out = _num_spec("decimal_range", spec)
        if out is not None:
            out["decimals"] = int(spec.get("decimals", 2))
        return out
    if kind == "date_range":
        s, e = spec.get("start"), spec.get("end")
        if isinstance(s, str) and isinstance(e, str):
            return {"kind": "date_range", "start": s, "end": e}
        return None
    if kind == "faker" and spec.get("faker") in _ALLOWED_FAKER:
        return {"kind": "faker", "faker": spec["faker"]}
    return None


def _num_spec(kind: str, spec: dict) -> Optional[dict]:
    try:
        lo = float(spec["min"]) if spec.get("min") is not None else None
        hi = float(spec["max"]) if spec.get("max") is not None else None
    except (TypeError, ValueError):
        return None
    if lo is None and hi is None:
        return None
    return {"kind": kind, "min": lo, "max": hi}


def validate_specs(schema: RelationalSchemaModel, raw: dict) -> dict[str, dict]:
    """Keep only specs whose column exists and whose shape is valid."""
    valid_keys = _column_keys(schema)
    out: dict[str, dict] = {}
    for key, spec in (raw or {}).items():
        if key not in valid_keys:
            continue
        clean = validate_spec(spec)
        if clean:
            out[key] = clean
    return out


def translate_rules(
    llm: Any,
    schema: RelationalSchemaModel,
    text: str,
) -> dict[str, dict]:
    """Translate a natural-language rule description into validated column specs."""
    prompt = (
        _SYSTEM + "\n\n可用列（表.列 (类型) | 注释）：\n" + _column_signature(schema)
        + "\n\n用户规则：\n" + text.strip()
        + "\n\n输出 JSON 对象，键为 \"表.列\"，值为规则。规则类型："
        '\n  {"kind":"enum","enum":["正常","冻结"]}'
        '\n  {"kind":"pool","pool":["招银理财","中信理财"]}'
        '\n  {"kind":"pattern","pattern":"138########","prefix":""}  (# 数字, ? 字母)'
        '\n  {"kind":"int_range","min":18,"max":60}'
        '\n  {"kind":"decimal_range","min":0,"max":50000,"decimals":2}'
        '\n  {"kind":"date_range","start":"2020-01-01","end":"2024-12-31"}'
        f'\n  {{"kind":"faker","faker":"<{sorted(_ALLOWED_FAKER)}>"}}'
        "\n只为用户明确提到的列输出，列名必须来自上面的清单。只输出 JSON。"
    )
    resp = llm.invoke(prompt)
    raw = (resp.content or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("LLM did not return a JSON object")
    parsed = json.loads(raw[start : end + 1])
    return validate_specs(schema, parsed)
