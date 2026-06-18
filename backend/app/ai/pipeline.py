"""LangGraph state definition for the AI generation pipeline."""

from __future__ import annotations

from typing import Any, TypedDict

from app.core.schema_model import RelationalSchemaModel


class GraphState(TypedDict):
    schema_model: RelationalSchemaModel
    domain_context: str
    field_rules: dict[str, Any]
    generated_batches: dict[str, list[dict]]
    validation_errors: list[str]
    retry_count: int
    row_counts: dict[str, int]
    ai_used: bool
