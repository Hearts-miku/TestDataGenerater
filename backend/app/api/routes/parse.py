from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.schema_model import GenerationStep
from app.services.parse_service import ParseService
from app.dependencies import get_parse_service

router = APIRouter()


class ParseRequest(BaseModel):
    source: str
    type: str           # required — "ddl" | "cypher"
    dialect: str = "mysql"


class ColumnOut(BaseModel):
    name: str
    type_category: str
    nullable: bool
    primary_key: bool
    auto_increment: bool
    unique: bool
    length: int | None = None
    enum_values: list[str] | None = None


class ForeignKeyOut(BaseModel):
    column: str
    ref_table: str
    ref_column: str


class TableOut(BaseModel):
    name: str
    columns: list[ColumnOut]
    primary_key: list[str]
    foreign_keys: list[ForeignKeyOut]


class ParseResponse(BaseModel):
    schema_id: str
    schema_type: str
    dialect: str
    tables: list[TableOut]
    nodes: list[dict] = []
    relationships: list[dict] = []
    generation_order: list[GenerationStep]


@router.post("/parse", response_model=ParseResponse)
async def parse_schema(
    req: ParseRequest,
    svc: ParseService = Depends(get_parse_service),
):
    try:
        if req.type == "ddl":
            schema = svc.parse_ddl(req.source, dialect=req.dialect)
        elif req.type == "cypher":
            schema = svc.parse_cypher(req.source)
        else:
            raise HTTPException(400, f"Unknown schema type: {req.type!r}")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Parse error: {exc}")

    tables_out = [
        TableOut(
            name=t.name,
            columns=[
                ColumnOut(
                    name=c.name,
                    type_category=c.type_category,
                    nullable=c.nullable,
                    primary_key=c.primary_key,
                    auto_increment=c.auto_increment,
                    unique=c.unique,
                    length=c.length,
                    enum_values=c.enum_values,
                )
                for c in t.columns
            ],
            primary_key=t.primary_key,
            foreign_keys=[
                ForeignKeyOut(column=fk.column, ref_table=fk.ref_table, ref_column=fk.ref_column)
                for fk in t.foreign_keys
            ],
        )
        for t in schema.tables  # schema.tables is a list
    ]

    return ParseResponse(
        schema_id=schema.id,
        schema_type=schema.schema_type,
        dialect=schema.dialect,
        tables=tables_out,
        generation_order=schema.generation_order,
    )
