from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.db import session_factory

router = APIRouter(tags=["meta"])


@router.get("/health")
def health():
    with session_factory()() as db:
        db.execute(text("select 1"))
    return {"status": "ok"}
