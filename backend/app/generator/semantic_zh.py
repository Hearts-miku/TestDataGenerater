"""Chinese banking-domain semantic inference.

The DDL columns carry Chinese ``COMMENT`` strings (e.g. "信用卡卡号", "确认日期").
These are far stronger semantic hints than the English column names, so we map
them to realistic value generators *before* falling back to the generic
field-name rules in ``rules.py``.

Two banking conventions are handled specifically:
  * Dates are frequently stored as ``YYYYMMDD`` **integers/decimals**, not DATE.
    A column commented "日期" with a decimal/integer/string type becomes a
    YYYYMMDD int rather than random noise.
  * Money/amount columns get a realistic magnitude instead of the 10^(p-s)
    upper bound a bare DECIMAL(22,2) would otherwise produce.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable, Optional

from app.generator.rules import Rule

if TYPE_CHECKING:
    from app.core.schema_model import ColumnDef


def _money(col: "ColumnDef") -> Rule:
    return Rule(tag="cn_money", scale=col.scale if col.scale is not None else 2)


def _rate(_col: "ColumnDef") -> Rule:
    return Rule(tag="cn_rate")


def _date_like(col: "ColumnDef") -> Rule:
    if col.type_category == "date":
        return Rule(tag="date_of_birth")
    if col.type_category == "datetime":
        return Rule(tag="datetime")
    # decimal / integer / string storing YYYYMMDD
    return Rule(tag="cn_date_int")


def _time_like(col: "ColumnDef") -> Rule:
    if col.type_category == "date":
        return Rule(tag="date_of_birth")
    if col.type_category in ("integer", "float", "decimal"):
        # e.g. "时点值/时点数" — a point-in-time *value*, not a timestamp.
        return _money(col)
    # timestamps and string times → datetime
    return Rule(tag="datetime")


def _yn_flag(col: "ColumnDef") -> Rule:
    if col.enum_values:
        return Rule(tag="enum", enum_values=col.enum_values)
    return Rule(tag="enum", enum_values=["Y", "N"])


def _count_int(_col: "ColumnDef") -> Rule:
    return Rule(tag="random_int", min_val=0, max_val=9999)


def _num_id(default_len: int, cap: int = 19) -> Callable[["ColumnDef"], Rule]:
    """Factory: a numeric ID/account string, length bounded by the column length."""
    def factory(col: "ColumnDef") -> Rule:
        n = min(col.length or default_len, cap)
        # Leading non-zero digit so the value reads like a real ID.
        return Rule(tag=None, prefix="", pattern="#" * max(n, 4))  # type: ignore[arg-type]
    return factory


def _code(col: "ColumnDef") -> Rule:
    # Short alphanumeric code, length bounded by the declared column length.
    n = min(col.length or 6, 12)
    return Rule(tag=None, pattern="?" + "#" * max(n - 1, 2))  # type: ignore[arg-type]


# (comment_keyword, restrict_to_type_category | None, rule_factory)
# Order matters: most specific first.
_ZH_RULES: list[tuple[re.Pattern, Optional[str], Callable[["ColumnDef"], Rule]]] = [
    # Categorical fields first: a "状态/标签" qualifier makes the column a code
    # regardless of any 号/编号 substring (e.g. "客户号状态" is a status, not an ID).
    (re.compile(r"状态|标签|品种|档次|等级"),          None, _code),
    (re.compile(r"身份证|证件号|证件号码"),          None, lambda c: Rule(tag="cn_id_card")),
    (re.compile(r"卡号"),                            None, lambda c: Rule(tag="cn_bankcard")),
    (re.compile(r"账号|账户|帐号|帐户"),              None, _num_id(19)),
    (re.compile(r"手机|联系电话|电话号|手机号"),       None, lambda c: Rule(tag="cn_phone")),
    (re.compile(r"邮箱|电子邮件|email", re.I),        None, lambda c: Rule(tag="email")),
    (re.compile(r"机构名|网点名|支行名|分行名|银行名|机构名称"), None, lambda c: Rule(tag="cn_org_name")),
    (re.compile(r"公司名|企业名|单位名"),             None, lambda c: Rule(tag="cn_company")),
    # Person names: customer/employee Chinese or pinyin names.
    (re.compile(r"中文名|英文名|拼音|客户名|户名|姓名|联系人|经办人|员工名|客户.*名称"),
                                                     None, lambda c: Rule(tag="cn_name")),
    (re.compile(r"地址|住址|通讯地址"),               None, lambda c: Rule(tag="cn_address")),
    (re.compile(r"日期"),                            None, _date_like),
    (re.compile(r"时间|时点|时分"),                   None, _time_like),
    (re.compile(r"金额|余额|额度|份额|净值|市值|价格|费用|利息|收入|本金|资产|负债|成本|盈亏"),
                                                     None, _money),
    (re.compile(r"比例|利率|汇率|占比|百分比"),        None, _rate),
    (re.compile(r"标志|是否|标识"),                   None, _yn_flag),
    (re.compile(r"数量|笔数|次数|个数|人数|天数|月数|年限"), None, _count_int),
    # ID-like fields (only reached for authority/non-FK columns; FK children are
    # filled by relation sampling before semantic inference runs).
    (re.compile(r"客户编号|客户号|当事人标识|客户标识"), None, _num_id(12)),
    (re.compile(r"员工号|工号|职员号|柜员号"),          None, _num_id(10)),
    (re.compile(r"产品编号|产品代码|产品号"),          None, _code),
    (re.compile(r"机构编号|机构号|网点号|分行号|法人机构编号"), None, _code),
    (re.compile(r"流水号|交易号|序号|凭证号|批次号|协议号"), None, _num_id(16)),
    (re.compile(r"代码|编码|类型$"),                  None, _code),
    # Generic entity name (product/branch/scheme names) → company-like text.
    (re.compile(r"名称|简称"),                        None, lambda c: Rule(tag="cn_company")),
]


def infer_zh_rule(col: "ColumnDef") -> Optional[Rule]:
    """Infer a Rule from a column's Chinese comment. Returns None if no match."""
    text = col.comment or ""
    if not text:
        return None
    for pattern, type_filter, factory in _ZH_RULES:
        if pattern.search(text):
            if type_filter is not None and col.type_category != type_filter:
                continue
            return factory(col)
    return None
