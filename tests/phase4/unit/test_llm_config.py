"""
Phase 4 · 单元测试 — LLM 配置层
覆盖任务：P4-B2（ChatOpenAI 实例化）+ P4-B3（降级逻辑）
"""

import pytest
from unittest.mock import patch, MagicMock
from app.ai.llm_config import LLMConfig, build_llm, is_llm_reachable


class TestLLMConfig:
    def test_valid_config_creates_object(self):
        cfg = LLMConfig(
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
            model="gpt-4o",
        )
        assert cfg.base_url == "https://api.openai.com/v1"
        assert cfg.model == "gpt-4o"

    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="api_key"):
            LLMConfig(base_url="https://api.openai.com/v1", api_key="", model="gpt-4o")

    def test_empty_model_raises(self):
        with pytest.raises(ValueError, match="model"):
            LLMConfig(base_url="https://api.openai.com/v1", api_key="sk-x", model="")

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="url"):
            LLMConfig(base_url="not-a-url", api_key="sk-x", model="gpt-4o")

    def test_from_dict(self):
        cfg = LLMConfig.from_dict({
            "base_url": "http://localhost:11434/v1",
            "api_key":  "ollama",
            "model":    "llama3",
        })
        assert cfg.model == "llama3"

    @pytest.mark.parametrize("url", [
        "https://api.openai.com/v1",
        "https://api.deepseek.com/v1",
        "https://openrouter.ai/api/v1",
        "http://localhost:11434/v1",
        "http://localhost:1234/v1",
    ])
    def test_known_base_urls_accepted(self, url):
        cfg = LLMConfig(base_url=url, api_key="sk-test", model="test-model")
        assert cfg.base_url == url


class TestBuildLLM:
    def test_builds_chat_openai_instance(self):
        from langchain_openai import ChatOpenAI
        cfg = LLMConfig(
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
            model="gpt-4o",
        )
        llm = build_llm(cfg)
        assert isinstance(llm, ChatOpenAI)

    def test_base_url_set_on_instance(self):
        cfg = LLMConfig(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
            model="llama3",
        )
        llm = build_llm(cfg)
        assert "11434" in str(llm.openai_api_base or "")

    def test_temperature_set(self):
        cfg = LLMConfig(
            base_url="https://api.openai.com/v1",
            api_key="sk-x",
            model="gpt-4o",
            temperature=0.2,
        )
        llm = build_llm(cfg)
        assert llm.temperature == 0.2


class TestIsLLMReachable:
    def test_reachable_returns_true(self):
        with patch("app.ai.llm_config.httpx.get") as mock_get:
            mock_get.return_value.status_code = 200
            assert is_llm_reachable("http://localhost:11434/v1") is True

    def test_unreachable_returns_false(self):
        import httpx
        with patch("app.ai.llm_config.httpx.get", side_effect=httpx.ConnectError("refused")):
            assert is_llm_reachable("http://127.0.0.1:19999/v1") is False

    def test_timeout_returns_false(self):
        import httpx
        with patch("app.ai.llm_config.httpx.get", side_effect=httpx.TimeoutException("timeout")):
            assert is_llm_reachable("http://127.0.0.1:19999/v1") is False
