"""FastAPI dependency injectors — single shared instances per process."""

from __future__ import annotations

from functools import lru_cache

from app.core.registry import SchemaRegistry
from app.db.duckdb_client import DuckDBClient
from app.services.export_service import ExportService
from app.services.generate_service import GenerateService
from app.services.parse_service import ParseService
from app.services.query_service import QueryService


@lru_cache(maxsize=1)
def _get_db() -> DuckDBClient:
    from app.config import settings
    return DuckDBClient(path=settings.duckdb_path)


@lru_cache(maxsize=1)
def _get_registry() -> SchemaRegistry:
    return SchemaRegistry()


def get_parse_service() -> ParseService:
    return ParseService(registry=_get_registry(), db=_get_db())


def get_generate_service() -> GenerateService:
    return GenerateService(registry=_get_registry(), db=_get_db())


def get_query_service() -> QueryService:
    return QueryService(db=_get_db())


def get_export_service() -> ExportService:
    return ExportService(registry=_get_registry(), db=_get_db())


def get_db() -> DuckDBClient:
    return _get_db()


def get_registry() -> SchemaRegistry:
    return _get_registry()
