"""
Phase 1 · 单元测试 — Faker 规则引擎
覆盖任务：P1-B4（字段名语义推断 + 类型感知生成）

测试对象：backend/app/generator/rules.py :: FakerRuleEngine
"""

import re
import pytest
from app.generator.rules import FakerRuleEngine


@pytest.fixture
def engine():
    return FakerRuleEngine(locale="zh_CN")


# ── 语义推断 ──────────────────────────────────────────────────────────────────

class TestSemanticInference:
    @pytest.mark.parametrize("field_name,type_cat,expected_tag", [
        ("email",        "string",   "email"),
        ("user_email",   "string",   "email"),
        ("phone",        "string",   "phone"),
        ("mobile",       "string",   "phone"),
        ("username",     "string",   "username"),
        ("first_name",   "string",   "first_name"),
        ("last_name",    "string",   "last_name"),
        ("full_name",    "string",   "name"),
        ("address",      "string",   "address"),
        ("city",         "string",   "city"),
        ("country",      "string",   "country"),
        ("zip_code",     "string",   "postcode"),
        ("postal_code",  "string",   "postcode"),
        ("url",          "string",   "url"),
        ("website",      "string",   "url"),
        ("company",      "string",   "company"),
        ("description",  "text",     "text"),
        ("bio",          "text",     "text"),
        ("ip_address",   "string",   "ipv4"),
        ("created_at",   "datetime", "datetime"),
        ("updated_at",   "datetime", "datetime"),
        ("birth_date",   "date",     "date_of_birth"),
        ("price",        "decimal",  "price"),
        ("amount",       "decimal",  "decimal"),
        ("age",          "integer",  "random_int"),
        ("quantity",     "integer",  "random_int"),
        ("is_active",    "boolean",  "boolean"),
        ("sku",          "string",   "sku"),
        ("uuid",         "string",   "uuid4"),
    ])
    def test_infer_rule_tag(self, engine, field_name, type_cat, expected_tag):
        rule = engine.infer_rule(field_name, type_cat)
        assert rule.tag == expected_tag, (
            f"field={field_name!r} type={type_cat!r}: "
            f"expected tag={expected_tag!r}, got {rule.tag!r}"
        )

    def test_unknown_field_falls_back_to_type(self, engine):
        rule = engine.infer_rule("xyzzy_unknown_field", "string")
        assert rule.tag in ("word", "text", "pystr", "lexify")

    def test_case_insensitive_inference(self, engine):
        rule_lower = engine.infer_rule("email", "string")
        rule_upper = engine.infer_rule("EMAIL", "string")
        assert rule_lower.tag == rule_upper.tag


# ── 值生成 ────────────────────────────────────────────────────────────────────

class TestValueGeneration:
    def test_email_format(self, engine):
        rule = engine.infer_rule("email", "string")
        value = engine.generate(rule)
        assert "@" in str(value)

    def test_integer_within_bounds(self, engine):
        rule = engine.infer_rule("age", "integer")
        rule.min_val = 18
        rule.max_val = 99
        for _ in range(20):
            val = engine.generate(rule)
            assert 18 <= val <= 99

    def test_boolean_is_bool(self, engine):
        rule = engine.infer_rule("is_active", "boolean")
        for _ in range(10):
            val = engine.generate(rule)
            assert isinstance(val, bool)

    def test_date_format(self, engine):
        rule = engine.infer_rule("created_at", "date")
        val = engine.generate(rule)
        # 应为 date 对象或 ISO 格式字符串
        assert val is not None

    def test_enum_respects_allowed_values(self, engine):
        from app.core.schema_model import ColumnDef
        from app.generator.rules import Rule
        rule = Rule(tag="enum", enum_values=["A", "B", "C"])
        for _ in range(30):
            val = engine.generate(rule)
            assert val in {"A", "B", "C"}

    def test_varchar_length_respected(self, engine):
        from app.generator.rules import Rule
        rule = Rule(tag="pystr", max_chars=10)
        for _ in range(20):
            val = engine.generate(rule)
            assert len(str(val)) <= 10

    def test_decimal_precision(self, engine):
        from app.generator.rules import Rule
        rule = Rule(tag="decimal", precision=10, scale=2)
        val = engine.generate(rule)
        parts = str(val).split(".")
        if len(parts) == 2:
            assert len(parts[1]) <= 2

    def test_none_generated_for_nullable(self, engine):
        from app.generator.rules import Rule
        rule = Rule(tag="pystr", nullable=True, null_rate=1.0)
        val = engine.generate(rule)
        assert val is None


# ── 批量生成 ──────────────────────────────────────────────────────────────────

class TestBatchGeneration:
    def test_batch_size_matches_request(self, engine):
        from app.generator.rules import Rule
        rule = Rule(tag="pystr")
        values = engine.generate_batch(rule, n=100)
        assert len(values) == 100

    def test_unique_batch_no_duplicates(self, engine):
        rule = engine.infer_rule("email", "string")
        values = engine.generate_batch(rule, n=200, unique=True)
        assert len(set(values)) == 200

    def test_unique_batch_raises_on_exhaustion(self, engine):
        from app.generator.rules import Rule
        # ENUM 只有 2 个值但请求 3 个 unique
        rule = Rule(tag="enum", enum_values=["X", "Y"])
        with pytest.raises(ValueError, match="unique"):
            engine.generate_batch(rule, n=3, unique=True)
