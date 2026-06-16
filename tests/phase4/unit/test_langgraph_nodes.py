"""
Phase 4 · 单元测试 — LangGraph 节点（mock LLM）
覆盖任务：P4-B1（四节点工作流各节点独立行为）

所有 LLM 调用通过 unittest.mock 替换，不发送真实请求。
"""

import pytest
from unittest.mock import MagicMock, patch
from app.ai.nodes import (
    SchemaContextNode,
    RuleInferenceNode,
    BatchGenerationNode,
    ValidationNode,
)
from app.ai.pipeline import GraphState
from app.core.schema_model import RelationalSchemaModel, TableDef, ColumnDef


def simple_schema():
    return RelationalSchemaModel(tables=[
        TableDef(name="users", columns=[
            ColumnDef(name="id",       type_category="integer", primary_key=True, auto_increment=True),
            ColumnDef(name="email",    type_category="string",  nullable=False, unique=True, length=120),
            ColumnDef(name="username", type_category="string",  nullable=False, unique=True, length=50),
        ])
    ])


def base_state(**kwargs) -> GraphState:
    defaults = dict(
        schema_model=simple_schema(),
        domain_context="",
        field_rules={},
        generated_batches={},
        validation_errors=[],
        retry_count=0,
        row_counts={"users": 5},
        ai_used=False,
    )
    defaults.update(kwargs)
    return GraphState(**defaults)


# ── SchemaContextNode ─────────────────────────────────────────────────────────

class TestSchemaContextNode:
    def test_sets_domain_context(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "用户管理系统"
        node = SchemaContextNode(llm=mock_llm)

        state = base_state()
        result = node.run(state)

        assert result["domain_context"] == "用户管理系统"
        mock_llm.invoke.assert_called_once()

    def test_prompt_contains_schema_info(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "some domain"
        node = SchemaContextNode(llm=mock_llm)

        node.run(base_state())

        call_args = mock_llm.invoke.call_args
        prompt_str = str(call_args)
        assert "users" in prompt_str or "email" in prompt_str

    def test_llm_error_propagates(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError("LLM unavailable")
        node = SchemaContextNode(llm=mock_llm)

        with pytest.raises(RuntimeError, match="LLM unavailable"):
            node.run(base_state())


# ── RuleInferenceNode ─────────────────────────────────────────────────────────

class TestRuleInferenceNode:
    def _make_llm_response(self) -> MagicMock:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = """{
            "users.email":    {"tag": "email"},
            "users.username": {"tag": "user_name"}
        }"""
        return mock_llm

    def test_returns_field_rules_dict(self):
        node = RuleInferenceNode(llm=self._make_llm_response())
        state = base_state(domain_context="用户系统")
        result = node.run(state)
        assert isinstance(result["field_rules"], dict)
        assert len(result["field_rules"]) > 0

    def test_rule_keys_include_table_prefix(self):
        node = RuleInferenceNode(llm=self._make_llm_response())
        result = node.run(base_state(domain_context="用户系统"))
        rule_keys = list(result["field_rules"].keys())
        assert all("." in k for k in rule_keys)

    def test_invalid_json_falls_back_to_empty_rules(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "NOT JSON"
        node = RuleInferenceNode(llm=mock_llm)
        result = node.run(base_state(domain_context="ctx"))
        assert isinstance(result["field_rules"], dict)


# ── BatchGenerationNode ───────────────────────────────────────────────────────

class TestBatchGenerationNode:
    def test_generates_correct_row_count(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = """[
            {"id": 1, "email": "a@a.com", "username": "alice"},
            {"id": 2, "email": "b@b.com", "username": "bob"},
            {"id": 3, "email": "c@c.com", "username": "carol"},
            {"id": 4, "email": "d@d.com", "username": "dave"},
            {"id": 5, "email": "e@e.com", "username": "eve"}
        ]"""
        node = BatchGenerationNode(llm=mock_llm)
        state = base_state(
            domain_context="用户系统",
            field_rules={"users.email": {"tag": "email"}, "users.username": {"tag": "user_name"}},
        )
        result = node.run(state)
        assert len(result["generated_batches"].get("users", [])) == 5

    def test_falls_back_to_faker_on_llm_error(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError("timeout")
        node = BatchGenerationNode(llm=mock_llm)
        # 降级应使用 Faker，不抛出
        result = node.run(base_state(domain_context="ctx", field_rules={}))
        assert "users" in result["generated_batches"]

    def test_generated_rows_have_required_fields(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = """[
            {"id": 1, "email": "a@a.com", "username": "alice"}
        ]"""
        node = BatchGenerationNode(llm=mock_llm)
        result = node.run(base_state(
            row_counts={"users": 1},
            field_rules={},
            domain_context="ctx",
        ))
        row = result["generated_batches"]["users"][0]
        assert "id" in row and "email" in row and "username" in row


# ── ValidationNode ────────────────────────────────────────────────────────────

class TestValidationNode:
    def test_passes_valid_batch(self):
        node = ValidationNode()
        state = base_state(generated_batches={
            "users": [
                {"id": 1, "email": "a@a.com", "username": "alice"},
                {"id": 2, "email": "b@b.com", "username": "bob"},
            ]
        })
        result = node.run(state)
        assert result["validation_errors"] == []

    def test_catches_unique_violation(self):
        node = ValidationNode()
        state = base_state(generated_batches={
            "users": [
                {"id": 1, "email": "dup@a.com", "username": "alice"},
                {"id": 2, "email": "dup@a.com", "username": "bob"},  # 重复 email
            ]
        })
        result = node.run(state)
        assert len(result["validation_errors"]) > 0

    def test_catches_not_null_violation(self):
        node = ValidationNode()
        state = base_state(generated_batches={
            "users": [{"id": 1, "email": None, "username": "alice"}]  # email NOT NULL
        })
        result = node.run(state)
        assert any("email" in str(e).lower() for e in result["validation_errors"])

    def test_increments_retry_on_failure(self):
        node = ValidationNode()
        state = base_state(
            retry_count=0,
            generated_batches={"users": [{"id": 1, "email": None, "username": "x"}]},
        )
        result = node.run(state)
        assert result["retry_count"] == 1
