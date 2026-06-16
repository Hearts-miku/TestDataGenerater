from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    duckdb_path: str = str(Path(__file__).parent.parent / "data" / "dataforge.duckdb")
    kuzu_path: str = str(Path(__file__).parent.parent / "data" / "dataforge_graph")
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"

    # LLM (Phase 4)
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"

    model_config = {"env_prefix": "DATAFORGE_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
