"""GET /health."""

import sqlite3

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from paybridge.api.container import Container
from paybridge.api.deps import get_container

router = APIRouter()


@router.get("/health")
def health(container: Container = Depends(get_container)) -> JSONResponse:
    try:
        with container.db.read() as conn:
            conn.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        return JSONResponse({"status": "error", "database": "error"}, status_code=503)
    return JSONResponse({"status": "ok", "database": "ok"})
