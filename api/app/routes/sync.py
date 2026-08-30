"""POST /sync - drain the client's offline mutation queue. Sec 12."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.domain.models import User
from app.domain.schemas import SessionOut
from app.repo.sessions import SessionRepo
from app.routes.sessions import _session_out
from app.services.sync import SyncService

router = APIRouter(tags=["sync"])


class Mutation(BaseModel):
    id: uuid.UUID
    type: str
    at: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class SyncRequest(BaseModel):
    mutations: list[Mutation] = Field(default_factory=list, max_length=500)


class Rejection(BaseModel):
    id: str | None
    code: str
    message: str


class SyncResponse(BaseModel):
    applied: list[uuid.UUID]
    duplicates: list[uuid.UUID]
    rejected: list[Rejection]
    # The server's view afterwards, so the client can replace its provisional
    # state rather than trying to reconcile it field by field (Sec 12.4).
    active_session: SessionOut | None


@router.post("/sync", response_model=SyncResponse)
def sync(
    payload: SyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    outcome = SyncService(db, user).apply(
        [m.model_dump(mode="json") for m in payload.mutations]
    )
    active = SessionRepo(db, user.id).active()
    return SyncResponse(
        applied=outcome.applied,
        duplicates=outcome.duplicates,
        rejected=[Rejection(**r) for r in outcome.rejected],
        active_session=_session_out(db, user, active) if active else None,
    )
