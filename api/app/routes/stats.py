"""Headline numbers, streak and power level."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.clock import local_date, utcnow
from app.core.ranks import HEATMAP_RAMP, RANKS, next_rank, progress_to_next, rank_for
from app.db import get_db
from app.deps import current_user
from app.domain.models import User
from app.repo.stats import StatsRepo
from app.repo.users import SettingsRepo

router = APIRouter(tags=["stats"])


class RankOut(BaseModel):
    level: int
    name: str
    threshold: int
    band: int
    color: str
    blurb: str


class StatsOut(BaseModel):
    current_streak: int
    longest_streak: int
    total_sessions: int
    sessions_this_week: int
    sets_this_week: int
    volume_this_week_kg: Decimal
    total_volume_kg: Decimal
    last_session_date: str | None
    trained_today: bool
    active_days: list[str]

    rank: RankOut
    next_rank: RankOut | None
    progress_to_next: float
    ladder: list[RankOut]
    heatmap_ramp: list[str]


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db), user: User = Depends(current_user)):
    settings = SettingsRepo(db, user.id).get()
    timezone = settings.timezone if settings else "UTC"
    week_start = settings.week_start if settings else "monday"
    today = local_date(utcnow(), timezone)

    computed = StatsRepo(db, user.id).compute(today=today, week_start=week_start)
    upcoming = next_rank(computed.current_streak)

    return StatsOut(
        **{
            **computed.__dict__,
            "last_session_date": (
                computed.last_session_date.isoformat()
                if computed.last_session_date
                else None
            ),
        },
        rank=RankOut(**rank_for(computed.current_streak).__dict__),
        next_rank=RankOut(**upcoming.__dict__) if upcoming else None,
        progress_to_next=progress_to_next(computed.current_streak),
        ladder=[RankOut(**r.__dict__) for r in RANKS],
        heatmap_ramp=list(HEATMAP_RAMP),
    )
