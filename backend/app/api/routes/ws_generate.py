"""WebSocket endpoint — streaming generation progress at /ws/generate."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.dependencies import get_db, get_registry

logger = logging.getLogger(__name__)

router = APIRouter()

_PREVIEW_THRESHOLD = 50  # send preview rows when table count >= this


@router.websocket("/ws/generate")
async def ws_generate(websocket: WebSocket) -> None:
    # Accept FIRST — prevents HTTP 500 if dependencies have transient errors during reload
    await websocket.accept()

    try:
        registry = get_registry()
        db = get_db()
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": f"Server init error: {exc}"})
        return

    try:
        raw = await websocket.receive_text()
    except WebSocketDisconnect:
        return

    try:
        req = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "message": "Invalid JSON"})
        return

    schema_id: str = req.get("schema_id", "")
    row_counts: dict[str, int] = req.get("row_counts", {})
    ai_enabled: bool = bool(req.get("ai_enabled", False))

    # Validate schema exists
    try:
        schema = registry.require(schema_id)
    except KeyError:
        await websocket.send_json({"type": "error", "message": f"Schema not found: {schema_id}"})
        return

    # Determine generation order
    if schema.generation_order:
        ordered_tables = [s.name for s in schema.generation_order if s.name in row_counts]
    else:
        ordered_tables = [t.name for t in schema.tables if t.name in row_counts]
    for t in row_counts:
        if t not in ordered_tables:
            ordered_tables.append(t)

    n_tables = max(len(ordered_tables), 1)

    try:
        await websocket.send_json({"type": "progress", "stage": "start", "percent": 5})

        from app.generator.constraint import ConstraintSolver
        from app.generator.strategies.rule_based import RuleBasedStrategy

        strategy = RuleBasedStrategy()

        db.create_tables(schema)  # CREATE OR REPLACE — ensures schema always matches

        solver = ConstraintSolver(schema)
        tables_meta: dict[str, dict] = {}

        for idx, table_name in enumerate(ordered_tables):
            count = row_counts.get(table_name, 0)
            if count <= 0:
                tables_meta[table_name] = {"generated": 0}
                continue

            progress_start = 5 + int(idx / n_tables * 70)
            progress_mid = 5 + int((idx + 0.5) / n_tables * 70)
            progress_end = 5 + int((idx + 1) / n_tables * 70)

            await websocket.send_json({
                "type": "progress",
                "stage": "generating",
                "table": table_name,
                "percent": progress_start,
            })

            # Run synchronous generation in a thread
            tbl = schema.tables_by_name.get(table_name)
            if tbl is None:
                tables_meta[table_name] = {"generated": 0}
                continue

            rows: list[dict] = await asyncio.to_thread(
                _generate_table, strategy, schema, table_name, count, solver
            )

            # Register PKs for FK consumers
            for pk_col in tbl.primary_key:
                pk_values = [r[pk_col] for r in rows if pk_col in r and r[pk_col] is not None]
                if pk_values:
                    solver.register_pk(table_name, pk_values)

            await websocket.send_json({
                "type": "progress",
                "stage": "generated",
                "table": table_name,
                "count": len(rows),
                "percent": progress_mid,
            })

            # Send preview for large batches
            if count >= _PREVIEW_THRESHOLD and rows:
                await websocket.send_json({
                    "type": "preview",
                    "table": table_name,
                    "rows": rows[:10],
                })

            # Write to DuckDB
            await asyncio.to_thread(_save_rows, db, table_name, rows)

            tables_meta[table_name] = {"generated": len(rows)}

            await websocket.send_json({
                "type": "progress",
                "stage": "saved",
                "table": table_name,
                "percent": progress_end,
            })

        await websocket.send_json({
            "type": "progress",
            "stage": "complete",
            "percent": 100,
        })

        await websocket.send_json({
            "type": "done",
            "tables": tables_meta,
            "ai_used": ai_enabled,
        })

    except WebSocketDisconnect:
        logger.debug("Client disconnected during generation")
    except Exception as exc:
        logger.exception("ws_generate error")
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


def _generate_table(
    strategy: Any,
    schema: Any,
    table_name: str,
    count: int,
    solver: Any,
) -> list[dict]:
    result = strategy.generate(schema, {table_name: count}, solver)
    return result.get(table_name, [])


def _save_rows(db: Any, table_name: str, rows: list[dict]) -> None:
    _CHUNK = 10_000
    for i in range(0, max(len(rows), 1), _CHUNK):
        chunk = rows[i: i + _CHUNK]
        if chunk:
            db.insert_rows(table_name, chunk)
