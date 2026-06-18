"""LLM configuration — build ChatOpenAI-compatible instances for any provider."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.7

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("api_key must not be empty")
        if not self.model:
            raise ValueError("model must not be empty")
        if not re.match(r"^https?://", self.base_url):
            raise ValueError(f"Invalid url: {self.base_url!r} — must start with http:// or https://")

    @classmethod
    def from_dict(cls, d: dict) -> "LLMConfig":
        return cls(
            base_url=d["base_url"],
            api_key=d["api_key"],
            model=d["model"],
            temperature=float(d.get("temperature", 0.7)),
        )


def build_llm(cfg: LLMConfig):
    """Return a ChatOpenAI instance configured for any OpenAI-compatible provider."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        model=cfg.model,
        temperature=cfg.temperature,
    )


def is_llm_reachable(base_url: str, timeout: float = 5.0) -> bool:
    """Return True if the base_url responds with HTTP (any status), False on connection error."""
    try:
        resp = httpx.get(base_url, timeout=timeout)
        return resp.status_code < 600
    except Exception:
        return False
