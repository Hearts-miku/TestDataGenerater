"""AI-assisted table-relationship inference.

When the user supplies only DDL (no curated Cypher schema graph), this module
infers the cross-table reference relationships so generation can still close
joins. It works in two modes:

  * **LLM mode** — sends a compact schema signature (table names + key-like
    columns with their Chinese comments) to the LLM, which can spot relations
    even across differently-named columns (e.g. ``cust_no`` ↔ ``party_id``).
  * **Heuristic fallback** — when no LLM is configured, links same-named
    key-like columns shared by multiple tables, choosing an authority (parent)
    table per shared column.

Both modes return ``list[Relation]`` (child references parent).
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from typing import Any, Optional

from app.core.relation_parser import Relation
from app.core.schema_model import ColumnDef, RelationalSchemaModel, TableDef

logger = logging.getLogger(__name__)

# A column name / comment that looks like a join key.
_KEY_NAME_RE = re.compile(
    r"(_id$|^id$|_no$|_code$|_key$|_cd$|party|cust|acct|card|prod|org|agt|client)",
    re.I,
)
_KEY_COMMENT_RE = re.compile(r"(编号|编码|号$|号码|标识|代码|账号|帐号|卡号|客户|产品|机构|协议)")
# Columns that are clearly NOT join keys (timestamps, money, names, flags…).
_NONKEY_NAME_RE = re.compile(r"(stamp|_dt$|_date$|_time$|_nm$|name$|_amt$|_bal$|flag)", re.I)
_NONKEY_COMMENT_RE = re.compile(r"(时间|日期|时间戳|金额|余额|名称|地址|标志|状态|比例|利率)")

# Authority tables usually hold master/basic data.
_AUTHORITY_HINT_RE = re.compile(r"(BASIC|MASTER|MAIN|INFO|CUST|PARTY|_PT_)", re.I)


def _is_key_like(col: ColumnDef) -> bool:
    name, comment = col.name, col.comment or ""
    if _NONKEY_NAME_RE.search(name) or _NONKEY_COMMENT_RE.search(comment):
        return False
    return bool(_KEY_NAME_RE.search(name) or _KEY_COMMENT_RE.search(comment))


def _key_like_columns(tbl: TableDef) -> list[ColumnDef]:
    return [c for c in tbl.columns if _is_key_like(c)]


# ── Heuristic fallback ─────────────────────────────────────────────────────────

def _heuristic_relations(schema: RelationalSchemaModel) -> list[Relation]:
    total = len(schema.tables)
    col_owners: dict[str, list[str]] = defaultdict(list)
    for tbl in schema.tables:
        for col in _key_like_columns(tbl):
            col_owners[col.name].append(tbl.name)

    by_name = schema.tables_by_name
    relations: list[Relation] = []
    for col_name, tables in col_owners.items():
        if len(tables) < 2:
            continue
        # Skip ubiquitous dimension/partition columns (present in most tables,
        # e.g. org_no / branch code) — they are not entity foreign keys. The LLM
        # path is needed to relate those correctly; the heuristic stays precise.
        if total >= 4 and len(tables) > total * 0.5:
            continue
        parent = _pick_authority(col_name, tables, by_name)
        for t in tables:
            if t != parent:
                relations.append(Relation(t, col_name, parent, col_name))
    return relations


def _pick_authority(col_name: str, tables: list[str], by_name: dict[str, TableDef]) -> str:
    # Prefer a table where the shared column is part of its (model) primary key.
    pk_tables = [t for t in tables if col_name in by_name[t].primary_key]
    if pk_tables:
        tables = pk_tables
    hint = [t for t in tables if _AUTHORITY_HINT_RE.search(t)]
    if hint:
        return sorted(hint, key=len)[0]
    return sorted(tables, key=len)[0]


# ── LLM mode ───────────────────────────────────────────────────────────────────

def _schema_signature(schema: RelationalSchemaModel, max_cols: int = 20) -> str:
    lines: list[str] = []
    for tbl in schema.tables:
        keys = _key_like_columns(tbl)[:max_cols]
        if not keys:
            continue
        cols = ", ".join(f"{c.name}({c.comment})" if c.comment else c.name for c in keys)
        lines.append(f"{tbl.name}: {cols}")
    return "\n".join(lines)


_SYSTEM = (
    "你是数据库建模专家。根据多张表的列名和中文注释，识别表之间的引用关系"
    "（外键/共享键），包括跨表同义字段（例如 cust_no 与 party_id 都表示客户）。"
    "child 表引用 parent 表，parent 是主表/权威表（该列是其主键或唯一标识，如客户主表）。"
    "只输出 JSON 数组，不要解释。"
)


def _llm_relations(llm: Any, schema: RelationalSchemaModel) -> list[Relation]:
    signature = _schema_signature(schema)
    prompt = (
        _SYSTEM + "\n\n表与关键列：\n" + signature + "\n\n"
        "输出 JSON 数组，每个元素："
        '{"child_table":"","child_col":"","parent_table":"","parent_col":"","note":""}。'
        "只包含真正的引用关系，跳过纯维度/时间列。只输出 JSON。"
    )
    resp = llm.invoke(prompt)
    raw = (resp.content or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("LLM did not return a JSON array")
    items = json.loads(raw[start : end + 1])
    relations: list[Relation] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        ct, cc = it.get("child_table"), it.get("child_col")
        pt, pc = it.get("parent_table"), it.get("parent_col")
        if all(isinstance(v, str) and v for v in (ct, cc, pt, pc)):
            relations.append(Relation(ct, cc, pt, pc))
    return relations


# ── Public API ─────────────────────────────────────────────────────────────────

def infer_relations(
    schema: RelationalSchemaModel,
    llm: Optional[Any] = None,
) -> list[Relation]:
    """Infer child→parent relations. Uses the LLM when given; always validated
    against the schema (both endpoints must exist) and de-duplicated."""
    relations: list[Relation] = []
    if llm is not None:
        try:
            relations = _llm_relations(llm, schema)
        except Exception:
            logger.warning("LLM relation inference failed; using heuristic", exc_info=True)
            relations = []
    if not relations:
        relations = _heuristic_relations(schema)

    return _validate(schema, relations)


def _validate(schema: RelationalSchemaModel, relations: list[Relation]) -> list[Relation]:
    by_name = schema.tables_by_name
    seen: set[tuple[str, str, str, str]] = set()
    out: list[Relation] = []
    for r in relations:
        child, parent = by_name.get(r.child_table), by_name.get(r.parent_table)
        if child is None or parent is None:
            continue
        if child.column(r.child_col) is None or parent.column(r.parent_col) is None:
            continue
        if r.child_table == r.parent_table and r.child_col == r.parent_col:
            continue
        key = (r.child_table, r.child_col, r.parent_table, r.parent_col)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
