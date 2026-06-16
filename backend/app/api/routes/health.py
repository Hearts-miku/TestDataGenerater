from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    try:
        import psutil
        mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except ImportError:
        mem = 0

    return {"status": "ok", "memory_mb": round(mem, 1)}
