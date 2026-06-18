"""AI seed inference — the LLM layer of the hybrid generation strategy.

For each table we make **one** LLM call that, given the column names, types and
Chinese comments, returns a per-column generation *spec*. Faker then expands
those specs into as many rows as needed. This keeps cost flat (one call per
table, regardless of row count) while making categorical/enum/domain columns
far more realistic than blind Faker.

Spec shape (matches ``rule_based._spec_to_rule``)::

    {
      "kind": "enum",    "enum": ["正常", "冻结", "销户"],
      "kind": "pool",    "pool": ["招银理财", "中信保诚", ...],
      "kind": "pattern", "pattern": "62########", "prefix": "",
      "kind": "faker",   "faker": "cn_name"
    }

The whole layer degrades gracefully: any LLM/parse failure for a table simply
yields no specs for it, and the rule-based layer (relations + zh comments)
takes over.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.schema_model import RelationalSchemaModel, TableDef

logger = logging.getLogger(__name__)

# Faker tags the LLM is allowed to choose (must exist in rules._generate_by_rule).
_ALLOWED_FAKER = {
    "cn_name", "cn_company", "cn_org_name", "cn_id_card", "cn_bankcard",
    "cn_phone", "cn_city", "cn_address", "cn_word", "cn_money", "cn_rate",
    "cn_date_int", "email", "datetime", "date_of_birth", "random_int",
}

_SYSTEM = (
    "你是中国银行业测试数据生成专家。根据表结构（列名、类型、中文注释）为每一列"
    "推断最合适的生成规范，使数据贴近真实业务语义。只输出 JSON，不要解释。"
)


def _table_prompt(domain: str, tbl: TableDef) -> str:
    cols = []
    for c in tbl.columns:
        cols.append(
            f"  - {c.name} | type={c.type_category} | comment={c.comment or '(无)'}"
        )
    col_block = "\n".join(cols)
    return (
        f"业务域: {domain}\n"
        f"表: {tbl.name}\n"
        f"列:\n{col_block}\n\n"
        "为需要语义增强的列输出 JSON 对象，键为列名，值为生成规范。仅包含分类/枚举/"
        "领域取值/特定格式的列；纯随机或已可由注释推断的列可省略。规范格式之一：\n"
        '  {"kind":"enum","enum":["正常","冻结"]}\n'
        '  {"kind":"pool","pool":["招银理财","中信理财"]}\n'
        '  {"kind":"pattern","pattern":"62########","prefix":""}\n'
        f'  {{"kind":"faker","faker":"<one of {sorted(_ALLOWED_FAKER)}>"}}\n'
        "pattern 中 # 表示随机数字，? 表示随机字母。只输出 JSON。"
    )


def _clean_json(raw: str) -> str:
    """Strip markdown fences and isolate the JSON object."""
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s.strip("`")
        if s.startswith("json"):
            s = s[4:]
    start, end = s.find("{"), s.rfind("}")
    return s[start : end + 1] if start != -1 and end != -1 else s


def _validate_spec(spec: Any) -> Optional[dict]:
    if not isinstance(spec, dict):
        return None
    kind = spec.get("kind")
    if kind == "enum" and isinstance(spec.get("enum"), list) and spec["enum"]:
        return {"kind": "enum", "enum": spec["enum"]}
    if kind == "pool" and isinstance(spec.get("pool"), list) and spec["pool"]:
        return {"kind": "pool", "pool": spec["pool"]}
    if kind == "pattern" and isinstance(spec.get("pattern"), str) and spec["pattern"]:
        return {"kind": "pattern", "pattern": spec["pattern"], "prefix": spec.get("prefix", "")}
    if kind == "faker" and spec.get("faker") in _ALLOWED_FAKER:
        return {"kind": "faker", "faker": spec["faker"]}
    return None


def infer_domain(llm: Any, schema: RelationalSchemaModel) -> str:
    """One short LLM call to name the business domain. Falls back to a default."""
    try:
        names = ", ".join(t.name for t in schema.tables[:20])
        resp = llm.invoke(
            "用一个简短的中文短语描述以下数据库表所属的业务域，只回短语：\n" + names
        )
        return (resp.content or "").strip() or "零售银行客户数据"
    except Exception:
        logger.debug("infer_domain failed; using default")
        return "零售银行客户数据"


def infer_field_specs(
    llm: Any,
    schema: RelationalSchemaModel,
    table_names: list[str],
    domain: str = "零售银行客户数据",
) -> dict[str, dict]:
    """Return {"table.column": spec} for the given tables. Degrades to {} on failure."""
    specs: dict[str, dict] = {}
    by_name = schema.tables_by_name
    for tname in table_names:
        tbl = by_name.get(tname)
        if tbl is None:
            continue
        try:
            resp = llm.invoke(_SYSTEM + "\n\n" + _table_prompt(domain, tbl))
            parsed = json.loads(_clean_json(resp.content or ""))
            if not isinstance(parsed, dict):
                continue
            valid_cols = {c.name for c in tbl.columns}
            for col_name, spec in parsed.items():
                if col_name not in valid_cols:
                    continue
                clean = _validate_spec(spec)
                if clean:
                    specs[f"{tname}.{col_name}"] = clean
        except Exception:
            logger.debug("infer_field_specs failed for table %s — skipping", tname)
            continue
    return specs
