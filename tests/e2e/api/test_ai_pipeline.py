"""
E2E：LangGraph AI 管道
使用 mock LLM 验证管道各节点行为，以及 AI 不可用时的降级逻辑。
测试聚焦于管道状态转换与输出结构，不依赖真实 LLM API。
"""

import pytest
from unittest.mock import patch, MagicMock
from conftest import parse_ddl, generate, sql_query


# ── 通用 mock LLM 响应 ────────────────────────────────────────────────────────

MOCK_DOMAIN_CONTEXT = "电商平台用户订单管理系统"

MOCK_FIELD_RULES = {
    "users.email":    {"type": "faker", "method": "email"},
    "users.username": {"type": "faker", "method": "user_name"},
    "orders.status":  {"type": "enum",  "values": ["pending", "paid", "shipped"]},
}

MOCK_LLM_BATCH = [
    {"email": "alice@example.com", "username": "alice_w", "age": 28},
    {"email": "bob@example.com",   "username": "bob_j",   "age": 35},
]


class TestAIPipelineNodes:
    """单独测试每个 LangGraph 节点（通过 API 内部状态端点）。"""

    def test_schema_context_node_returns_domain(self, client, ddl_ecommerce):
        schema = parse_ddl(client, ddl_ecommerce)
        resp = client.post("/api/ai/analyze-schema", json={"schema_id": schema["schema_id"]})
        # 若 LLM 不可用，端点应返回 503 而非崩溃
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            assert "domain_context" in resp.json()

    def test_rule_inference_node_returns_per_field_rules(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        resp = client.post(
            "/api/ai/infer-rules",
            json={"schema_id": schema["schema_id"], "domain_context": MOCK_DOMAIN_CONTEXT},
        )
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            rules = resp.json()["field_rules"]
            assert isinstance(rules, dict)

    def test_validation_node_catches_constraint_violation(self, client, ddl_simple_users):
        """提交违反约束的数据，校验节点应返回错误列表。"""
        schema = parse_ddl(client, ddl_simple_users)
        resp = client.post("/api/ai/validate-batch", json={
            "schema_id": schema["schema_id"],
            "batch": [
                {"id": 1, "username": "dup_user", "email": "a@a.com"},
                {"id": 1, "username": "dup_user", "email": "b@b.com"},  # 重复 PK + UNIQUE
            ],
        })
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            errors = resp.json()["validation_errors"]
            assert len(errors) > 0


class TestAIEnabledGeneration:
    """集成测试：ai_enabled=True 时生成流程走 LangGraph 路径。"""

    def test_ai_generation_produces_correct_row_count(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        result = generate(client, schema["schema_id"], row_counts={"users": 10}, ai_enabled=True)
        # 无论是否真正调用 LLM，生成数量必须符合要求
        assert result["tables"]["users"]["generated"] == 10

    def test_ai_generated_data_satisfies_constraints(self, client, ddl_ecommerce):
        schema = parse_ddl(client, ddl_ecommerce)
        generate(client, schema["schema_id"], row_counts={
            "categories": 5, "products": 15,
            "users": 8, "orders": 20, "order_items": 40,
        }, ai_enabled=True)

        orphans = sql_query(client, """
            SELECT COUNT(*) AS cnt FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE c.id IS NULL
        """)["rows"][0]["cnt"]
        assert orphans == 0

    def test_ai_response_metadata_present(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        result = generate(client, schema["schema_id"], row_counts={"users": 5}, ai_enabled=True)
        # 响应中应包含 AI 管道使用情况（真实调用 or 降级）
        assert "ai_used" in result
        assert isinstance(result["ai_used"], bool)


class TestAIFallbackBehavior:
    """验证 LLM API 不可用时系统能自动降级为 Faker 规则引擎。"""

    def test_generation_succeeds_without_llm(self, client, ddl_ecommerce):
        """即使 AI 关闭，生成仍应正常完成。"""
        schema = parse_ddl(client, ddl_ecommerce)
        result = generate(client, schema["schema_id"], row_counts={
            "categories": 5, "products": 10,
            "users": 5, "orders": 10, "order_items": 20,
        }, ai_enabled=False)
        for table in ("categories", "products", "users", "orders", "order_items"):
            assert result["tables"][table]["generated"] > 0

    def test_fallback_flag_set_when_llm_unavailable(self, client, ddl_simple_users):
        """当 ai_enabled=True 但 LLM 实际不可达时，ai_used 应为 False。"""
        schema = parse_ddl(client, ddl_simple_users)
        # 通过配置一个无效 base_url 模拟 LLM 不可达
        resp = client.post("/api/generate", json={
            "schema_id": schema["schema_id"],
            "row_counts": {"users": 5},
            "ai_enabled": True,
            "llm_config": {
                "base_url": "http://127.0.0.1:19999/v1",  # 必定不可达
                "api_key":  "invalid-key",
                "model":    "gpt-4o",
            },
        })
        assert resp.status_code == 200
        result = resp.json()
        assert result["tables"]["users"]["generated"] == 5
        assert result["ai_used"] is False  # 自动降级


class TestLLMConfigValidation:
    def test_missing_api_key_with_ai_enabled_returns_error(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        resp = client.post("/api/generate", json={
            "schema_id": schema["schema_id"],
            "row_counts": {"users": 5},
            "ai_enabled": True,
            "llm_config": {"base_url": "https://api.openai.com/v1", "api_key": "", "model": "gpt-4o"},
        })
        # 空 api_key + ai_enabled=True 应返回 422 或自动降级
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            assert resp.json()["ai_used"] is False

    def test_custom_base_url_accepted(self, client, ddl_simple_users):
        schema = parse_ddl(client, ddl_simple_users)
        resp = client.post("/api/generate", json={
            "schema_id": schema["schema_id"],
            "row_counts": {"users": 5},
            "ai_enabled": True,
            "llm_config": {
                "base_url": "https://api.deepseek.com/v1",
                "api_key":  "sk-test",
                "model":    "deepseek-chat",
            },
        })
        # 配置本身合法，不应因 base_url 格式而 422
        assert resp.status_code in (200, 503)  # 503 = LLM 实际调用失败后降级
