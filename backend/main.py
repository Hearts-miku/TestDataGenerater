"""DataForge — FastAPI entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import db_sql, export, generate, health, parse, reset

app = FastAPI(title="DataForge", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(health.router, prefix="/api")
app.include_router(parse.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(db_sql.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(reset.router, prefix="/api")

# Serve frontend (production mode — build first with `pnpm build`)
_frontend = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
