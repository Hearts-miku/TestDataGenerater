"""Internal schema representation — output of all parsers."""

from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ColumnDef(BaseModel):
    name: str
    type_category: Literal[
        "integer", "float", "decimal", "string", "text",
        "boolean", "date", "datetime", "json", "enum", "unknown"
    ] = "unknown"
    raw_type: str = ""
    nullable: bool = True
    primary_key: bool = False
    auto_increment: bool = False
    unique: bool = False
    default: Any = None
    length: Optional[int] = None       # VARCHAR(n) → n
    precision: Optional[int] = None    # DECIMAL(p,s) → p
    scale: Optional[int] = None        # DECIMAL(p,s) → s
    enum_values: Optional[list[str]] = None


# Alias for backward-compat
ColumnModel = ColumnDef


class ForeignKeyDef(BaseModel):
    column: str
    ref_table: str
    ref_column: str


# Alias
ForeignKeyModel = ForeignKeyDef


class TableDef(BaseModel):
    name: str
    columns: list[ColumnDef] = Field(default_factory=list)
    primary_key: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKeyDef] = Field(default_factory=list)
    unique_constraints: list[list[str]] = Field(default_factory=list)

    def column(self, name: str) -> Optional[ColumnDef]:
        return next((c for c in self.columns if c.name == name), None)


# Alias
TableModel = TableDef


class GenerationStep(BaseModel):
    step: int
    name: str            # table / node / relationship name
    kind: Literal["table", "node", "relationship"] = "table"


class RelationalSchemaModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dialect: str = "mysql"
    tables: list[TableDef] = Field(default_factory=list)
    generation_order: list[GenerationStep] = Field(default_factory=list)
    schema_type: Literal["relational", "graph"] = "relational"

    # graph-specific (Phase 3)
    nodes: list["NodeDef"] = Field(default_factory=list)
    relationships: list["RelationshipDef"] = Field(default_factory=list)

    @property
    def tables_by_name(self) -> dict[str, TableDef]:
        return {t.name: t for t in self.tables}


# ── Graph schema (Phase 3 stubs) ──────────────────────────────────────────────

class NodeDef(BaseModel):
    label: str
    properties: list[ColumnDef] = Field(default_factory=list)
    unique_constraints: list[str] = Field(default_factory=list)

    @property
    def columns(self) -> list[ColumnDef]:
        return self.properties


class RelationshipDef(BaseModel):
    type: str
    from_label: str
    to_label: str
    properties: list[ColumnDef] = Field(default_factory=list)
