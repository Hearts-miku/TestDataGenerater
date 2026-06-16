"""In-memory schema registry — maps schema_id → RelationalSchemaModel."""

from __future__ import annotations

from typing import Optional

from app.core.schema_model import RelationalSchemaModel


class SchemaRegistry:
    def __init__(self) -> None:
        self._store: dict[str, RelationalSchemaModel] = {}

    def save(self, schema: RelationalSchemaModel) -> str:
        self._store[schema.id] = schema
        return schema.id

    def get(self, schema_id: str) -> Optional[RelationalSchemaModel]:
        return self._store.get(schema_id)

    def require(self, schema_id: str) -> RelationalSchemaModel:
        schema = self.get(schema_id)
        if schema is None:
            raise KeyError(f"Schema not found: {schema_id!r}")
        return schema

    def delete(self, schema_id: str) -> None:
        self._store.pop(schema_id, None)

    def list_ids(self) -> list[str]:
        return list(self._store.keys())


# Singleton used across the app (overridable in tests)
schema_registry = SchemaRegistry()
